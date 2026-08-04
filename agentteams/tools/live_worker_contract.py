"""Run live per-Worker contract checks against an OpenAI-compatible Responses API.

The model response is produced by the configured external model; this module does
not mock LLM output. It is intentionally a per-Worker preflight, not an
AgentTeams orchestrator or a substitute for the Team Room end-to-end run.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from .llm_contract_smoke import extract_output_text, responses_url
except ImportError:  # Supports `python tools/live_worker_contract.py`.
    from llm_contract_smoke import extract_output_text, responses_url


SCENARIO_DIR = Path(__file__).resolve().parents[1] / "scenarios"


def load_scenario(name: str) -> dict[str, Any]:
    return json.loads((SCENARIO_DIR / f"{name}.json").read_text(encoding="utf-8"))


def metadata(scenario: dict[str, Any]) -> dict[str, Any]:
    return {
        "scenario_id": scenario["id"],
        "task_id": scenario["task_id"],
        "title": scenario["title"],
        "consent": scenario["consent"],
        "domain_pack": scenario["domain_pack"]["id"],
    }


def call_model(base_url: str, model: str, api_key: str, prompt: str) -> tuple[dict[str, Any], dict[str, Any]]:
    body = json.dumps({"model": model, "input": prompt, "max_output_tokens": 1400}).encode("utf-8")
    request = Request(
        responses_url(base_url),
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=90) as result:
            response = json.loads(result.read().decode("utf-8"))
    except HTTPError as error:
        raise RuntimeError(f"provider returned HTTP {error.code}") from error
    except URLError as error:
        raise RuntimeError(f"provider network error: {error.reason}") from error

    if response.get("status") != "completed":
        raise RuntimeError(f"provider response did not complete: {response.get('status')!r}")
    try:
        artifact = json.loads(extract_output_text(response))
    except json.JSONDecodeError as error:
        raise RuntimeError("model did not return a JSON Worker artifact") from error
    if not isinstance(artifact, dict):
        raise RuntimeError("model did not return a JSON object")
    return artifact, response


def authorized_prompt(scenario: dict[str, Any]) -> str:
    return f"""You are the AgentTeams Worker `interaction-evidence-analyst` for CogniGuide.
This is a live contract test. Use only the supplied authorized task metadata and
scored assessment events; do not invent facts. Return exactly one JSON object and
no Markdown.

Output schema:
{{
  "schema_version":"0.1.0",
  "task_id":"{scenario['task_id']}",
  "trace_id":"live-worker-evidence-001",
  "producer":"interaction-evidence-analyst",
  "status":"READY|NEEDS_MORE_DATA|BLOCKED",
  "consent":{{"analysis_authorized":true}},
  "concept_evidence":[{{"concept_id":"","scored_event_count":0,"correct_count":0,"confidence_summary":{{"mean":0.0}},"evidence_refs":[]}}],
  "data_gaps":[],
  "evidence_refs":[]
}}

Rules:
- Check metadata authorization first. If false, return BLOCKED without analysis.
- Aggregate the provided events by `concept`; preserve their event IDs in evidence_refs.
- A concept with fewer than three scored events must be represented as a data gap,
  not a stable learner conclusion.
- Do not emit diagnoses, raw text, hidden reasoning, or credentials.

Task metadata:
{json.dumps(metadata(scenario), ensure_ascii=False, separators=(',', ':'))}

Scored assessment events:
{json.dumps(scenario['assessment_events'], ensure_ascii=False, separators=(',', ':'))}
"""


def consent_prompt(scenario: dict[str, Any]) -> str:
    return f"""You are the AgentTeams Worker `interaction-evidence-analyst` for CogniGuide.
This is a live consent-boundary contract test. You received task metadata only;
you have not received assessment events and must not infer or mention them.
Return exactly one JSON object and no Markdown.

If `consent.analysis_authorized` is not exactly true, return `BLOCKED` with an
authorization-needed data gap, empty `concept_evidence`, and empty `evidence_refs`.

Output schema:
{{"schema_version":"0.1.0","task_id":"{scenario['task_id']}","trace_id":"live-worker-consent-001","producer":"interaction-evidence-analyst","status":"BLOCKED","consent":{{"analysis_authorized":false}},"concept_evidence":[],"data_gaps":[],"evidence_refs":[]}}

Task metadata:
{json.dumps(metadata(scenario), ensure_ascii=False, separators=(',', ':'))}
"""


def validate_authorized(artifact: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    if artifact.get("task_id") != scenario["task_id"] or artifact.get("producer") != "interaction-evidence-analyst":
        raise RuntimeError("authorized artifact has the wrong task identity or producer")
    required_refs = set(scenario["expected_demo_outcome"]["must_reference"])
    evidence_refs = set(artifact.get("evidence_refs", []))
    if not required_refs.issubset(evidence_refs):
        raise RuntimeError("authorized artifact omitted required functions evidence references")
    functions = [item for item in artifact.get("concept_evidence", []) if item.get("concept_id") == "functions"]
    if len(functions) != 1 or functions[0].get("scored_event_count") != 3 or functions[0].get("correct_count") != 0:
        raise RuntimeError("authorized artifact did not correctly aggregate functions events")
    return {
        "scenario": scenario["id"],
        "artifact_status": artifact.get("status"),
        "functions_scored_event_count": functions[0]["scored_event_count"],
        "functions_correct_count": functions[0]["correct_count"],
        "evidence_ref_count": len(evidence_refs),
    }


def validate_consent(artifact: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    if artifact.get("task_id") != scenario["task_id"] or artifact.get("producer") != "interaction-evidence-analyst":
        raise RuntimeError("consent artifact has the wrong task identity or producer")
    if artifact.get("status") != "BLOCKED":
        raise RuntimeError("consent artifact was not fail-closed")
    if artifact.get("concept_evidence") or artifact.get("evidence_refs"):
        raise RuntimeError("consent artifact emitted learning-analysis content")
    return {
        "scenario": scenario["id"],
        "artifact_status": artifact.get("status"),
        "concept_evidence_count": 0,
        "evidence_ref_count": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run two live CogniGuide Worker contract checks.")
    parser.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL") or os.environ.get("AT_LLM_BASE_URL"))
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL") or os.environ.get("AT_MODEL"))
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    args = parser.parse_args()
    api_key = os.environ.get(args.api_key_env)
    if not args.base_url:
        parser.error("set --base-url or OPENAI_BASE_URL/AT_LLM_BASE_URL")
    if not args.model:
        parser.error("set --model or OPENAI_MODEL/AT_MODEL")
    if not api_key:
        parser.error(f"set the API key in environment variable {args.api_key_env}")

    checks: list[dict[str, Any]] = []
    started = time.perf_counter()
    authorized = load_scenario("python_foundations_overconfidence")
    artifact, response = call_model(args.base_url, args.model, api_key, authorized_prompt(authorized))
    checks.append(validate_authorized(artifact, authorized) | {"total_tokens": response.get("usage", {}).get("total_tokens")})

    consent = load_scenario("consent_required")
    artifact, response = call_model(args.base_url, args.model, api_key, consent_prompt(consent))
    checks.append(validate_consent(artifact, consent) | {"total_tokens": response.get("usage", {}).get("total_tokens")})

    print(
        json.dumps(
            {
                "ok": True,
                "model": args.model,
                "kind": "live_worker_contract_preflight",
                "latency_ms": round((time.perf_counter() - started) * 1000),
                "checks": checks,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(json.dumps({"ok": False, "error": str(error)}), file=sys.stderr)
        raise SystemExit(1)
