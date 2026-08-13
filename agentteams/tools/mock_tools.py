"""Stateful, local tool implementations used by CogniGuide AgentTeams Workers.

The code only exposes data and validation tools. It does not orchestrate agents:
AgentTeams owns Worker creation, TeamLeader routing, collaboration, and context.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from threading import RLock
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = PROJECT_ROOT / "scenarios"
REQUEST_SCHEMA_VERSION = "cogniguide.tool-request/v1"
AUDIT_EVENT_SCHEMA_VERSION = "cogniguide.audit-event/v1"
TRACE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

# This is a demo policy layer, not a substitute for authenticated transport. In a
# deployed setup, the gateway must only be reachable on a private network and the
# caller identity must be bound to a service credential.
ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "interaction-evidence-analyst": frozenset(
        {
            "learning_data.get_task_metadata",
            "learning_data.get_assessment_events",
            "learning_data.get_interaction_observations",
            "audit.append",
        }
    ),
    "knowledge-state-estimator": frozenset(
        {
            "learning_data.get_task_metadata",
            "framework.get_domain_pack",
            "framework.get_bkt_parameters",
            "audit.append",
        }
    ),
    "learning-path-planner": frozenset(
        {
            "learning_data.get_task_metadata",
            "framework.get_domain_pack",
            "plan.validate_prerequisites",
            "audit.append",
        }
    ),
    "report-verifier": frozenset(
        {
            "learning_data.get_task_metadata",
            "evidence.verify_refs",
            "plan.validate_prerequisites",
            "audit.append",
        }
    ),
    "cogniguide-demo-leader": frozenset(
        {
            "learning_data.get_task_metadata",
            "audit.append",
        }
    ),
    "demo-operator": frozenset({"system.reset"}),
}
RequestContext = dict[str, str]


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"scenario {path.name!r} must contain a JSON object")
    return payload


def list_scenarios() -> list[str]:
    return sorted(path.stem for path in SCENARIO_DIR.glob("*.json"))


def load_scenario(scenario_id: str) -> dict[str, Any]:
    if not isinstance(scenario_id, str) or scenario_id not in list_scenarios():
        raise ValueError(f"unknown scenario {scenario_id!r}; available: {', '.join(list_scenarios())}")
    scenario = _load_json(SCENARIO_DIR / f"{scenario_id}.json")
    _validate_scenario(scenario, scenario_id)
    return scenario


def _validate_scenario(scenario: dict[str, Any], scenario_id: str) -> None:
    required = {"id", "task_id", "title", "consent", "domain_pack", "assessment_events"}
    missing = sorted(required - set(scenario))
    if missing:
        raise ValueError(f"scenario {scenario_id!r} missing fields: {', '.join(missing)}")
    if scenario["id"] != scenario_id:
        raise ValueError(f"scenario {scenario_id!r} has a mismatched id")
    if not isinstance(scenario["task_id"], str) or not scenario["task_id"].strip():
        raise ValueError(f"scenario {scenario_id!r} has an invalid task_id")
    if not isinstance(scenario["consent"], dict) or not isinstance(
        scenario["consent"].get("analysis_authorized"), bool
    ):
        raise ValueError(f"scenario {scenario_id!r} must declare boolean consent.analysis_authorized")
    domain_pack = scenario["domain_pack"]
    if not isinstance(domain_pack, dict) or not isinstance(domain_pack.get("concepts"), list):
        raise ValueError(f"scenario {scenario_id!r} has an invalid domain_pack")
    concept_ids = [item.get("id") for item in domain_pack["concepts"] if isinstance(item, dict)]
    if len(concept_ids) != len(domain_pack["concepts"]) or any(not isinstance(item, str) for item in concept_ids):
        raise ValueError(f"scenario {scenario_id!r} has an invalid concept id")
    if len(set(concept_ids)) != len(concept_ids):
        raise ValueError(f"scenario {scenario_id!r} contains duplicate concept ids")
    event_ids = [item.get("event_id") for item in scenario["assessment_events"] if isinstance(item, dict)]
    if len(event_ids) != len(scenario["assessment_events"]) or any(not isinstance(item, str) for item in event_ids):
        raise ValueError(f"scenario {scenario_id!r} has an invalid assessment event id")
    if len(set(event_ids)) != len(event_ids):
        raise ValueError(f"scenario {scenario_id!r} contains duplicate assessment event ids")


def _hash(value: Any) -> str:
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class LocalCogniGuideTools:
    """Expose assessment, framework, validation, and audit tools for one scenario."""

    def __init__(self, scenario_id: str) -> None:
        self.scenario_id = scenario_id
        self.scenario = load_scenario(scenario_id)
        self.trace: list[dict[str, Any]] = []
        self.audit_events: list[dict[str, Any]] = []
        self._lock = RLock()

    def authorize(self, tool: str, payload: dict[str, Any]) -> RequestContext:
        """Validate the request envelope and enforce the demo role policy."""

        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        schema_version = payload.get("schema_version")
        if schema_version != REQUEST_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {REQUEST_SCHEMA_VERSION!r}")
        task_id = payload.get("task_id")
        if task_id != self.scenario["task_id"]:
            raise PermissionError("task_id does not match the requested scenario")
        trace_id = payload.get("trace_id")
        if not isinstance(trace_id, str) or not TRACE_ID_PATTERN.fullmatch(trace_id):
            raise ValueError("trace_id must match [A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
        actor = payload.get("actor")
        if not isinstance(actor, str) or actor not in ROLE_PERMISSIONS:
            raise PermissionError("actor is not an allowed CogniGuide role")
        if tool not in ROLE_PERMISSIONS[actor]:
            raise PermissionError(f"actor {actor!r} is not allowed to call {tool!r}")
        return {
            "schema_version": schema_version,
            "task_id": task_id,
            "trace_id": trace_id,
            "actor": actor,
        }

    def _record(self, tool: str, context: RequestContext, args: dict[str, Any], result: Any) -> Any:
        # Do not retain arbitrary request bodies: a plan or audit payload can
        # contain user-authored text. The hash still makes each call auditable.
        with self._lock:
            self.trace.append(
                {
                    "time": _timestamp(),
                    "tool": tool,
                    "request_context": copy.deepcopy(context),
                    "arg_keys": sorted(args),
                    "args_hash": _hash(args),
                    "result_hash": _hash(result),
                }
            )
        return copy.deepcopy(result)

    def task_metadata(self, context: RequestContext) -> dict[str, Any]:
        result = {
            "scenario_id": self.scenario_id,
            "task_id": self.scenario["task_id"],
            "title": self.scenario["title"],
            "consent": self.scenario["consent"],
            "domain_pack": self.scenario["domain_pack"]["id"],
        }
        return self._record("learning_data.get_task_metadata", context, {}, result)

    def _require_analysis_authorized(self) -> None:
        if not self.scenario["consent"].get("analysis_authorized", False):
            raise PermissionError("analysis is not authorized for this scenario")

    def assessment_events(self, context: RequestContext) -> list[dict[str, Any]]:
        self._require_analysis_authorized()
        return self._record("learning_data.get_assessment_events", context, {}, self.scenario["assessment_events"])

    def interaction_observations(self, context: RequestContext) -> list[dict[str, Any]]:
        self._require_analysis_authorized()
        result = self.scenario.get("interaction_observations", [])
        return self._record("learning_data.get_interaction_observations", context, {}, result)

    def domain_pack(self, context: RequestContext) -> dict[str, Any]:
        return self._record("framework.get_domain_pack", context, {}, self.scenario["domain_pack"])

    def bkt_parameters(self, context: RequestContext) -> dict[str, Any]:
        result = self.scenario["domain_pack"]["bkt_parameters"]
        return self._record("framework.get_bkt_parameters", context, {}, result)

    def verify_evidence_refs(self, context: RequestContext, evidence_refs: list[str]) -> dict[str, Any]:
        self._require_analysis_authorized()
        if not isinstance(evidence_refs, list) or not all(isinstance(ref, str) and ref.strip() for ref in evidence_refs):
            raise ValueError("evidence_refs must be a list of non-empty strings")
        known = {event["event_id"] for event in self.scenario["assessment_events"]}
        known.update(item["evidence_id"] for item in self.scenario.get("interaction_observations", []))
        requested = [ref.strip() for ref in evidence_refs]
        missing = sorted(set(requested) - known)
        result = {
            "valid": bool(requested) and not missing,
            "requested_count": len(requested),
            "resolved_count": len(requested) - len(missing),
            "missing_refs": missing,
        }
        if not requested:
            result["reason"] = "at least one evidence reference is required"
        return self._record("evidence.verify_refs", context, {"evidence_refs": requested}, result)

    def validate_path(self, context: RequestContext, plan: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(plan, dict):
            raise ValueError("plan must be a JSON object")
        raw_ordered = plan.get("ordered_concepts", [])
        if not isinstance(raw_ordered, list) or not all(isinstance(item, str) and item.strip() for item in raw_ordered):
            raise ValueError("plan.ordered_concepts must be a list of non-empty strings")
        external_actions = plan.get("external_actions", [])
        if not isinstance(external_actions, list):
            raise ValueError("plan.external_actions must be a list when provided")
        concepts = {item["id"]: item for item in self.scenario["domain_pack"]["concepts"]}
        ordered = [item.strip() for item in raw_ordered]
        missing_concepts = [item for item in ordered if item not in concepts]
        duplicate_concepts = sorted({item for item in ordered if ordered.count(item) > 1})
        seen: set[str] = set()
        violations: list[dict[str, Any]] = []
        for concept_id in ordered:
            if concept_id not in concepts:
                continue
            unmet = [parent for parent in concepts[concept_id]["prerequisites"] if parent not in seen]
            if unmet:
                violations.append({"concept": concept_id, "missing_prerequisites": unmet})
            seen.add(concept_id)
        result = {
            "valid": bool(ordered) and not missing_concepts and not duplicate_concepts and not violations,
            "unknown_concepts": missing_concepts,
            "duplicate_concepts": duplicate_concepts,
            "prerequisite_violations": violations,
            "requires_external_action": bool(external_actions),
        }
        if not ordered:
            result["reason"] = "ordered_concepts must contain at least one concept"
        if result["requires_external_action"]:
            result["valid"] = False
            result["reason"] = "learning path must not contain external automatic actions"
        return self._record("plan.validate_prerequisites", context, {"plan": plan}, result)

    def append_audit(self, context: RequestContext, event: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(event, dict):
            raise ValueError("event must be a JSON object")
        required = {"task_id", "trace_id", "actor", "event", "status"}
        missing = sorted(required - set(event))
        if missing:
            raise ValueError(f"audit event missing fields: {', '.join(missing)}")
        for field in ("task_id", "trace_id", "actor"):
            if event[field] != context[field]:
                raise PermissionError(f"audit event {field} must match request metadata")
        if not isinstance(event["event"], str) or not isinstance(event["status"], str):
            raise ValueError("audit event and status must be strings")
        if "schema_version" in event and not isinstance(event["schema_version"], str):
            raise ValueError("audit schema_version must be a string")
        if "evidence_refs" in event and (
            not isinstance(event["evidence_refs"], list)
            or not all(isinstance(ref, str) and ref.strip() for ref in event["evidence_refs"])
        ):
            raise ValueError("audit evidence_refs must be a list of non-empty strings")
        allowed_fields = {
            "schema_version",
            "task_id",
            "trace_id",
            "actor",
            "event",
            "status",
            "evidence_refs",
            "reason_code",
            "artifact_hash",
            "tool_call_ids",
        }
        safe_event = {
            key: copy.deepcopy(value)
            for key, value in event.items()
            if key in allowed_fields
        }
        safe_event.setdefault("schema_version", AUDIT_EVENT_SCHEMA_VERSION)
        safe_event["request_context"] = copy.deepcopy(context)
        safe_event["event_hash"] = _hash(safe_event)
        with self._lock:
            self.audit_events.append(safe_event)
        result = {
            "accepted": True,
            "event_hash": safe_event["event_hash"],
            "dropped_fields": sorted(set(event) - allowed_fields),
        }
        return self._record("audit.append", context, {"event": safe_event}, result)

    def trace_snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self.trace)

    def audit_snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self.audit_events)


TOOL_STATES: dict[str, LocalCogniGuideTools] = {}
_TOOL_STATES_LOCK = RLock()


def get_state(scenario_id: str) -> LocalCogniGuideTools:
    with _TOOL_STATES_LOCK:
        if scenario_id not in TOOL_STATES:
            TOOL_STATES[scenario_id] = LocalCogniGuideTools(scenario_id)
        return TOOL_STATES[scenario_id]


def reset_state(scenario_id: str) -> dict[str, Any]:
    with _TOOL_STATES_LOCK:
        TOOL_STATES[scenario_id] = LocalCogniGuideTools(scenario_id)
    return {"scenario_id": scenario_id, "status": "reset"}
