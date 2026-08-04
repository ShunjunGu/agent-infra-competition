"""Deterministic, auditable reference runtime for the CogniGuide demo.

The reference runtime deliberately avoids an LLM or external service so that the
competition demo is reproducible. The AgentTeams adapter in ``agentteams/`` maps
these agent contracts to a production AgentTeams deployment.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
from typing import Any
from uuid import uuid4


SCHEMA_VERSION = "0.1.0"
EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)")
MIN_ASSESSMENTS_FOR_PRIORITY = 3
BKT_PARAMETERS = {"prior": 0.2, "learn": 0.15, "guess": 0.2, "slip": 0.1}


FRAMEWORKS: dict[str, dict[str, Any]] = {
    "python_foundations": {
        "label": "Python 基础",
        "concepts": [
            {
                "id": "variables",
                "label": "变量与数据类型",
                "prerequisites": [],
                "practice": "写出变量赋值、类型判断和一次类型转换，并解释每步结果。",
            },
            {
                "id": "expressions",
                "label": "表达式与运算",
                "prerequisites": ["variables"],
                "practice": "完成 3 道表达式求值题，并在运行前写下预测结果。",
            },
            {
                "id": "conditionals",
                "label": "条件分支",
                "prerequisites": ["variables", "expressions"],
                "practice": "实现一个包含边界条件的折扣规则，并用 4 组输入验证。",
            },
            {
                "id": "loops",
                "label": "循环与迭代",
                "prerequisites": ["variables", "conditionals"],
                "practice": "用 for 和 while 分别完成一次列表过滤，并解释终止条件。",
            },
            {
                "id": "functions",
                "label": "函数与参数",
                "prerequisites": ["variables", "expressions"],
                "practice": "把重复逻辑抽成一个带默认参数的函数，并写 3 个断言。",
            },
            {
                "id": "collections",
                "label": "列表与字典",
                "prerequisites": ["variables"],
                "practice": "用列表和字典各完成一次统计任务，比较两种数据结构。",
            },
            {
                "id": "debugging",
                "label": "调试与验证",
                "prerequisites": ["functions", "collections"],
                "practice": "定位一个给定的失败断言，记录假设、证据和修复后的回归结果。",
            },
        ],
    }
}


class InputValidationError(ValueError):
    """Raised when a demo payload does not satisfy the input contract."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _hash(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _round(value: float | None, digits: int = 3) -> float | None:
    return None if value is None else round(value, digits)


def _as_probability(value: Any, field: str) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise InputValidationError(f"{field} 必须是 0 到 1 之间的数字") from error
    if not 0 <= parsed <= 1:
        raise InputValidationError(f"{field} 必须在 0 到 1 之间")
    return parsed


def _framework_index(domain: str) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    framework = FRAMEWORKS.get(domain)
    if framework is None:
        choices = ", ".join(FRAMEWORKS)
        raise InputValidationError(f"暂不支持的 domain: {domain!r}。可选值：{choices}")
    return framework, {concept["id"]: concept for concept in framework["concepts"]}


def _normalize_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise InputValidationError("输入必须是 JSON 对象")

    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id.strip():
        raise InputValidationError("session_id 为必填字符串")

    domain = payload.get("domain")
    if not isinstance(domain, str):
        raise InputValidationError("domain 为必填字符串")
    _, concepts = _framework_index(domain)

    consent = payload.get("consent")
    if not isinstance(consent, dict) or not isinstance(consent.get("analysis_authorized"), bool):
        raise InputValidationError("consent.analysis_authorized 必须明确为 true 或 false")

    learner = payload.get("learner", {})
    if not isinstance(learner, dict):
        raise InputValidationError("learner 必须是对象")

    raw_signals = payload.get("learning_signals", [])
    if not isinstance(raw_signals, list):
        raise InputValidationError("learning_signals 必须是数组")

    normalized_signals: list[dict[str, Any]] = []
    for index, signal in enumerate(raw_signals):
        if not isinstance(signal, dict):
            raise InputValidationError(f"learning_signals[{index}] 必须是对象")
        concept = signal.get("concept")
        if concept not in concepts:
            raise InputValidationError(f"learning_signals[{index}].concept 不属于 {domain} 知识框架")

        confidence = _as_probability(signal.get("confidence"), f"learning_signals[{index}].confidence")
        observed_correct = signal.get("observed_correct")
        if observed_correct is not None and not isinstance(observed_correct, bool):
            raise InputValidationError(f"learning_signals[{index}].observed_correct 必须是 true、false 或 null")

        explicit_correct = signal.get("correct_count")
        explicit_incorrect = signal.get("incorrect_count")
        if explicit_correct is not None or explicit_incorrect is not None:
            try:
                correct_count = int(explicit_correct or 0)
                incorrect_count = int(explicit_incorrect or 0)
            except (TypeError, ValueError) as error:
                raise InputValidationError(f"learning_signals[{index}] 的计数必须是整数") from error
            if correct_count < 0 or incorrect_count < 0:
                raise InputValidationError(f"learning_signals[{index}] 的计数不能为负数")
        elif observed_correct is None:
            correct_count = 0
            incorrect_count = 0
        else:
            correct_count = 1 if observed_correct else 0
            incorrect_count = 0 if observed_correct else 1

        normalized_signals.append(
            {
                "concept": concept,
                "confidence": confidence,
                "correct_count": correct_count,
                "incorrect_count": incorrect_count,
                "evidence_id": str(signal.get("evidence_id") or f"signal-{index + 1}"),
                "question_type": str(signal.get("question_type") or "unknown"),
            }
        )

    raw_interactions = payload.get("interactions", [])
    if not isinstance(raw_interactions, list):
        raise InputValidationError("interactions 必须是数组")

    interactions: list[dict[str, Any]] = []
    for index, interaction in enumerate(raw_interactions):
        if not isinstance(interaction, dict):
            raise InputValidationError(f"interactions[{index}] 必须是对象")
        topic = interaction.get("topic")
        if topic is not None and topic not in concepts:
            raise InputValidationError(f"interactions[{index}].topic 不属于 {domain} 知识框架")
        content = str(interaction.get("content") or "")
        interactions.append(
            {
                "topic": topic,
                "question_type": str(interaction.get("question_type") or "unknown"),
                "content": content,
                "evidence_id": str(interaction.get("evidence_id") or f"interaction-{index + 1}"),
            }
        )

    return {
        "session_id": session_id.strip(),
        "domain": domain,
        "learner": {"id": str(learner.get("id") or "anonymous"), "goal": str(learner.get("goal") or "未提供")},
        "consent": {
            "analysis_authorized": consent["analysis_authorized"],
            "retention": str(consent.get("retention") or "local-only"),
        },
        "learning_signals": normalized_signals,
        "interactions": interactions,
    }


class AuditTrail:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.events: list[dict[str, Any]] = []

    def record(self, agent: str, event: str, status: str, inputs: Any, outputs: Any, **details: Any) -> None:
        self.events.append(
            {
                "sequence": len(self.events) + 1,
                "timestamp": _utc_now(),
                "run_id": self.run_id,
                "agent": agent,
                "event": event,
                "status": status,
                "input_hash": _hash(inputs),
                "output_hash": _hash(outputs),
                "details": details,
            }
        )


def _privacy_findings(interactions: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter()
    for interaction in interactions:
        content = interaction["content"]
        if EMAIL_PATTERN.search(content):
            counts["email"] += 1
        if PHONE_PATTERN.search(content):
            counts["phone"] += 1
    return dict(counts)


def _consent_gate(payload: dict[str, Any]) -> dict[str, Any]:
    privacy_findings = _privacy_findings(payload["interactions"])
    authorized = payload["consent"]["analysis_authorized"]
    return {
        "decision": "allow" if authorized else "block",
        "analysis_authorized": authorized,
        "retention": payload["consent"]["retention"],
        "privacy_findings": privacy_findings,
        "human_review_required": bool(privacy_findings),
        "reason": "用户已授权本地分析" if authorized else "未获得分析授权；系统未处理学习内容",
    }


def _interaction_analyst(payload: dict[str, Any], concepts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    buckets: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "confidence_values": [],
            "correct_count": 0,
            "incorrect_count": 0,
            "assessment_events": [],
            "question_count": 0,
            "question_types": Counter(),
            "evidence_refs": [],
        }
    )

    for signal in payload["learning_signals"]:
        bucket = buckets[signal["concept"]]
        if signal["confidence"] is not None:
            bucket["confidence_values"].append(signal["confidence"])
        bucket["correct_count"] += signal["correct_count"]
        bucket["incorrect_count"] += signal["incorrect_count"]
        bucket["assessment_events"].extend(
            {"is_correct": True, "confidence": signal["confidence"], "evidence_id": signal["evidence_id"]}
            for _ in range(signal["correct_count"])
        )
        bucket["assessment_events"].extend(
            {"is_correct": False, "confidence": signal["confidence"], "evidence_id": signal["evidence_id"]}
            for _ in range(signal["incorrect_count"])
        )
        bucket["question_types"][signal["question_type"]] += 1
        bucket["evidence_refs"].append(signal["evidence_id"])

    for interaction in payload["interactions"]:
        if interaction["topic"] is None:
            continue
        bucket = buckets[interaction["topic"]]
        bucket["question_count"] += 1
        bucket["question_types"][interaction["question_type"]] += 1
        bucket["evidence_refs"].append(interaction["evidence_id"])

    topics: list[dict[str, Any]] = []
    for concept_id, bucket in buckets.items():
        assessed_count = bucket["correct_count"] + bucket["incorrect_count"]
        topics.append(
            {
                "concept": concept_id,
                "label": concepts[concept_id]["label"],
                "assessed_count": assessed_count,
                "correct_count": bucket["correct_count"],
                "incorrect_count": bucket["incorrect_count"],
                "question_count": bucket["question_count"],
                "mean_confidence": _round(
                    sum(bucket["confidence_values"]) / len(bucket["confidence_values"])
                    if bucket["confidence_values"]
                    else None
                ),
                "question_types": dict(bucket["question_types"]),
                "evidence_refs": sorted(set(bucket["evidence_refs"])),
                "assessment_events": bucket["assessment_events"],
            }
        )

    topics.sort(key=lambda item: item["concept"])
    all_question_types = Counter()
    for item in topics:
        all_question_types.update(item["question_types"])
    return {
        "agent": "interaction-analyst",
        "topic_profiles": topics,
        "question_type_distribution": dict(all_question_types),
        "evidence_count": sum(item["assessed_count"] + item["question_count"] for item in topics),
        "limitations": [
            "系统仅使用结构化学习信号；不会把对话文本作为心理诊断依据。",
            "低样本主题只输出待验证假设，不输出确定性结论。",
        ],
    }


def _topological_order(framework: dict[str, Any], requested: list[str]) -> list[str]:
    concepts = {concept["id"]: concept for concept in framework["concepts"]}
    required: set[str] = set()

    def collect(concept_id: str) -> None:
        if concept_id in required:
            return
        required.add(concept_id)
        for prerequisite in concepts[concept_id]["prerequisites"]:
            collect(prerequisite)

    for concept_id in requested:
        collect(concept_id)

    ordered: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(concept_id: str) -> None:
        if concept_id in visited:
            return
        if concept_id in visiting:
            raise RuntimeError("知识框架中存在循环依赖")
        visiting.add(concept_id)
        for prerequisite in concepts[concept_id]["prerequisites"]:
            if prerequisite in required:
                visit(prerequisite)
        visiting.remove(concept_id)
        visited.add(concept_id)
        ordered.append(concept_id)

    for concept_id in requested:
        visit(concept_id)
    return ordered


def _knowledge_state_estimator(
    profile: dict[str, Any], framework: dict[str, Any], concepts: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    profile_by_concept = {item["concept"]: item for item in profile["topic_profiles"]}
    states: list[dict[str, Any]] = []
    calibration_weight = 0
    calibration_error_total = 0.0
    calibration_bias_total = 0.0
    brier_total = 0.0

    for concept in framework["concepts"]:
        concept_id = concept["id"]
        profile_item = profile_by_concept.get(concept_id)
        if profile_item is None:
            continue
        correct_count = profile_item["correct_count"]
        incorrect_count = profile_item["incorrect_count"]
        assessed_count = profile_item["assessed_count"]
        mastery = BKT_PARAMETERS["prior"]
        for event in profile_item["assessment_events"]:
            if event["is_correct"]:
                likelihood = mastery * (1 - BKT_PARAMETERS["slip"]) + (1 - mastery) * BKT_PARAMETERS["guess"]
                observed_mastery = mastery * (1 - BKT_PARAMETERS["slip"]) / likelihood
            else:
                likelihood = mastery * BKT_PARAMETERS["slip"] + (1 - mastery) * (1 - BKT_PARAMETERS["guess"])
                observed_mastery = mastery * BKT_PARAMETERS["slip"] / likelihood
            mastery = observed_mastery + (1 - observed_mastery) * BKT_PARAMETERS["learn"]
        observed_accuracy = correct_count / assessed_count if assessed_count else None
        mean_confidence = profile_item["mean_confidence"]
        calibration_gap = mean_confidence - observed_accuracy if mean_confidence is not None and observed_accuracy is not None else None
        for event in profile_item["assessment_events"]:
            if event["confidence"] is None:
                continue
            outcome = 1.0 if event["is_correct"] else 0.0
            calibration_error_total += abs(event["confidence"] - outcome)
            calibration_bias_total += event["confidence"] - outcome
            brier_total += (event["confidence"] - outcome) ** 2
            calibration_weight += 1

        states.append(
            {
                "concept": concept_id,
                "label": concept["label"],
                "assessed_count": assessed_count,
                "knowledge_tracing": {
                    "model": "BKT",
                    "parameters": BKT_PARAMETERS,
                    "mastery": _round(mastery),
                },
                "observed_accuracy": _round(observed_accuracy),
                "mean_confidence": mean_confidence,
                "calibration_gap": _round(calibration_gap),
                "evidence_refs": profile_item["evidence_refs"],
            }
        )

    state_by_concept = {item["concept"]: item for item in states}
    blind_spots: list[dict[str, Any]] = []
    for state in states:
        concept = concepts[state["concept"]]
        assessed_count = state["assessed_count"]
        mastery = state["knowledge_tracing"]["mastery"]
        calibration_gap = state["calibration_gap"]
        reason_codes: list[str] = []
        risk = 0.0
        if assessed_count == 0:
            reason_codes.append("no_assessment_evidence")
            risk += 0.22
        elif mastery < 0.6:
            reason_codes.append("low_posterior_mastery")
            risk += (0.6 - mastery) * 1.2
        if assessed_count < 2:
            reason_codes.append("insufficient_evidence")
            risk += 0.15
        if calibration_gap is not None and calibration_gap >= 0.2:
            reason_codes.append("overconfidence_signal")
            risk += calibration_gap * 0.9
        if calibration_gap is not None and calibration_gap <= -0.3:
            reason_codes.append("underconfidence_signal")
            risk += abs(calibration_gap) * 0.35

        weak_prerequisites = []
        for prerequisite in concept["prerequisites"]:
            prerequisite_state = state_by_concept.get(prerequisite)
            if prerequisite_state is None or prerequisite_state["knowledge_tracing"]["mastery"] < 0.6:
                weak_prerequisites.append(prerequisite)
        if weak_prerequisites:
            reason_codes.append("prerequisite_risk")
            risk += 0.22

        if reason_codes and risk >= 0.2:
            if assessed_count < MIN_ASSESSMENTS_FOR_PRIORITY:
                priority = "needs_more_data"
            elif risk >= 0.6:
                priority = "high"
            elif risk >= 0.38:
                priority = "medium"
            else:
                priority = "low"
            blind_spots.append(
                {
                    "concept": state["concept"],
                    "label": state["label"],
                    "priority": priority,
                    "risk_score": _round(min(risk, 1.0)),
                    "reason_codes": reason_codes,
                    "weak_prerequisites": weak_prerequisites,
                    "evidence_refs": state["evidence_refs"],
                    "claim_type": "待验证学习假设",
                }
            )

    blind_spots.sort(key=lambda item: (-item["risk_score"], item["concept"]))
    expected_calibration_error = calibration_error_total / calibration_weight if calibration_weight else None
    calibration_bias = calibration_bias_total / calibration_weight if calibration_weight else None
    brier_score = brier_total / calibration_weight if calibration_weight else None
    calibration_status = (
        "insufficient_evidence"
        if expected_calibration_error is None
        else "needs_calibration"
        if expected_calibration_error >= 0.2
        else "acceptable"
    )
    human_review_reasons: list[str] = []
    if expected_calibration_error is None:
        human_review_reasons.append("缺少可判分结果，无法估计校准度")
    if expected_calibration_error is not None and expected_calibration_error >= 0.2:
        human_review_reasons.append("置信度与可观察结果偏差较大，需要使用者确认")
    if any("insufficient_evidence" in item["reason_codes"] for item in blind_spots):
        human_review_reasons.append("至少一个结论的证据量不足 2 条")

    return {
        "agent": "knowledge-state-estimator",
        "method": {
            "name": "Bayesian Knowledge Tracing with confidence calibration",
            "description": "使用固定的 BKT 演示参数跟踪知识点掌握度；参数需在真实部署中用历史数据校准。",
        },
        "concept_states": states,
        "blind_spots": blind_spots,
        "calibration": {
            "expected_calibration_error": _round(expected_calibration_error),
            "bias": _round(calibration_bias),
            "brier_score": _round(brier_score),
            "status": calibration_status,
            "sampled_assessments": calibration_weight,
        },
        "human_review": {"required": bool(human_review_reasons), "reasons": human_review_reasons},
    }


def _learning_path_planner(
    knowledge_state: dict[str, Any], framework: dict[str, Any], concepts: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    blind_spots = knowledge_state["blind_spots"]
    targets = [item["concept"] for item in blind_spots[:3]]
    if not targets:
        targets = [framework["concepts"][0]["id"]]
    ordered = _topological_order(framework, targets)
    blind_by_concept = {item["concept"]: item for item in blind_spots}

    concept_steps: list[dict[str, Any]] = []
    for concept_id in ordered:
        gap = blind_by_concept.get(concept_id)
        concept = concepts[concept_id]
        reason = (
            "；".join(gap["reason_codes"]) if gap else "作为后续目标的前置知识，先建立可验证证据"
        )
        concept_steps.append(
            {
                "concept": concept_id,
                "label": concept["label"],
                "reason": reason,
                "activity": concept["practice"],
                "exit_criterion": "连续 3 个独立小任务达到正确，并在作答前记录 0-1 的信心分数。",
                "evidence_to_store": ["题目版本", "预测信心", "结果", "错误归因"],
            }
        )

    first_target = concepts[ordered[0]]["label"]
    return {
        "agent": "learning-path-planner",
        "policy": "先补前置依赖，再处理高风险目标；所有路径步骤均要求可判分证据与事后反思。",
        "phases": [
            {
                "phase": 1,
                "name": "校准与诊断",
                "objective": f"围绕 {first_target} 获取至少 3 条可判分证据，校准主观信心。",
                "steps": concept_steps[:1],
            },
            {
                "phase": 2,
                "name": "前置知识修复",
                "objective": "按知识依赖顺序完成针对性练习，避免跳过基础概念。",
                "steps": concept_steps[1:] or concept_steps[:1],
            },
            {
                "phase": 3,
                "name": "迁移与反思",
                "objective": "用新题检验迁移能力，并复核‘预测信心—实际结果’是否收敛。",
                "steps": [
                    {
                        "concept": "transfer-check",
                        "label": "迁移检验",
                        "reason": "避免只在原题型上记忆答案。",
                        "activity": "完成一个未见过的小项目任务，先写方案和信心分数，再运行测试并复盘。",
                        "exit_criterion": "保存任务、预测、测试结果和一次可解释的修正记录。",
                        "evidence_to_store": ["新任务", "信心分数", "测试结果", "复盘"],
                    }
                ],
            },
        ],
        "target_concepts": targets,
    }


def _report_verifier(
    payload: dict[str, Any], policy: dict[str, Any], knowledge_state: dict[str, Any], plan: dict[str, Any]
) -> dict[str, Any]:
    caveats = [
        "该结果是基于导入学习证据的辅助性学习建议，不构成心理、医疗或能力诊断。",
        "掌握度由固定参数的 BKT 演示模型估计；样本较少时应优先收集更多可判分证据。",
    ]
    if policy["privacy_findings"]:
        caveats.append("检测到潜在个人信息；报告未复述原文，建议在后续导入前脱敏。")
    if knowledge_state["human_review"]["required"]:
        caveats.append("系统已标记需人工复核项，不能把对应结论直接用于高风险决策。")

    high_priority = [item for item in knowledge_state["blind_spots"] if item["priority"] == "high"]
    summary = (
        f"已分析 {len(knowledge_state['concept_states'])} 个有证据的概念，"
        f"生成 {len(knowledge_state['blind_spots'])} 条待验证学习假设。"
    )
    return {
        "agent": "report-verifier",
        "title": "CogniGuide 元认知洞察报告",
        "headline": "优先补齐高风险前置知识，并通过可判分练习校准学习信心。"
        if high_priority
        else "先补充可判分学习证据，再形成更可靠的个性化路径。",
        "summary": summary,
        "high_priority_count": len(high_priority),
        "human_review": knowledge_state["human_review"],
        "caveats": caveats,
        "next_action": plan["phases"][0]["objective"],
        "data_boundary": {
            "retention": payload["consent"]["retention"],
            "raw_interaction_text_in_report": False,
            "analysis_authorized": policy["analysis_authorized"],
        },
    }


def _blocked_result(payload: dict[str, Any], policy: dict[str, Any], run_id: str, audit: AuditTrail) -> dict[str, Any]:
    report = {
        "title": "CogniGuide 安全边界响应",
        "headline": "分析未执行：尚未获得学习数据分析授权。",
        "summary": "系统没有处理或推断导入的学习内容。请先由数据主体明确授权本地分析。",
        "next_action": "将 consent.analysis_authorized 设为 true 后重新运行。",
        "caveats": ["未授权时不输出个体学习结论。"],
        "data_boundary": {"analysis_authorized": False, "raw_interaction_text_in_report": False},
    }
    audit.record("team-leader", "pipeline_blocked", "blocked", payload, report, reason="consent_missing")
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "status": "blocked",
        "session_id": payload["session_id"],
        "input_summary": {
            "domain": payload["domain"],
            "assessment_event_count": len(payload["learning_signals"]),
            "interaction_count": len(payload["interactions"]),
            "raw_text_persisted": False,
        },
        "policy": policy,
        "report": report,
        "trace": audit.events,
    }


def run_pipeline(raw_payload: Any) -> dict[str, Any]:
    """Run a full, deterministic multi-agent learning-analysis workflow."""

    payload = _normalize_payload(raw_payload)
    framework, concepts = _framework_index(payload["domain"])
    run_id = f"cg-{uuid4().hex[:12]}"
    audit = AuditTrail(run_id)
    audit.record("team-leader", "task_received", "ok", {"session_id": payload["session_id"], "domain": payload["domain"]}, {}, workflow="serial")

    policy = _consent_gate(payload)
    audit.record("consent-boundary-agent", "policy_check", policy["decision"], payload["consent"], policy)
    if policy["decision"] == "block":
        return _blocked_result(payload, policy, run_id, audit)

    profile = _interaction_analyst(payload, concepts)
    audit.record("interaction-analyst", "extract_evidence_profile", "ok", payload["learning_signals"], profile)

    knowledge_state = _knowledge_state_estimator(profile, framework, concepts)
    audit.record("knowledge-state-estimator", "estimate_mastery_and_calibration", "ok", profile, knowledge_state)

    plan = _learning_path_planner(knowledge_state, framework, concepts)
    audit.record("learning-path-planner", "build_prerequisite_aware_path", "ok", knowledge_state, plan)

    report = _report_verifier(payload, policy, knowledge_state, plan)
    audit.record("report-verifier", "verify_claims_and_emit_report", "ok", {"knowledge_state": knowledge_state, "plan": plan}, report)

    result = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "status": "complete",
        "session_id": payload["session_id"],
        "input_summary": {
            "domain": payload["domain"],
            "assessment_event_count": len(payload["learning_signals"]),
            "interaction_count": len(payload["interactions"]),
            "raw_text_persisted": False,
        },
        "framework": {"id": payload["domain"], "label": framework["label"]},
        "team": {
            "name": "cogniguide-reference-team",
            "coordination": "team-leader serially dispatches four specialized agents through structured state contracts",
        },
        "policy": policy,
        "interaction_profile": profile,
        "knowledge_state": knowledge_state,
        "learning_plan": plan,
        "report": report,
        "trace": audit.events,
    }
    audit.record("team-leader", "task_completed", "ok", {"run_id": run_id}, {"status": result["status"]})
    result["trace"] = audit.events
    return result


def render_markdown(result: dict[str, Any]) -> str:
    report = result["report"]
    lines = [f"# {report['title']}", "", f"> {report['headline']}", "", report["summary"], ""]
    if result["status"] == "blocked":
        lines.extend(["## 下一步", "", report["next_action"], ""])
        return "\n".join(lines)

    calibration = result["knowledge_state"]["calibration"]
    lines.extend(
        [
            "## 校准与证据",
            "",
            f"- 校准状态：`{calibration['status']}`",
            f"- 期望校准误差：`{calibration['expected_calibration_error']}`",
            f"- 可判分样本数：`{calibration['sampled_assessments']}`",
            f"- 校准偏差：`{calibration['bias']}`；Brier 分数：`{calibration['brier_score']}`",
            "",
            "## 待验证学习假设",
            "",
            "| 优先级 | 概念 | 风险分 | 依据 |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for gap in result["knowledge_state"]["blind_spots"]:
        lines.append(f"| {gap['priority']} | {gap['label']} | {gap['risk_score']} | {', '.join(gap['reason_codes'])} |")

    lines.extend(["", "## 学习路径", ""])
    for phase in result["learning_plan"]["phases"]:
        lines.extend([f"### 阶段 {phase['phase']}：{phase['name']}", "", phase["objective"], ""])
        for step in phase["steps"]:
            lines.append(f"- **{step['label']}**：{step['activity']}  验收：{step['exit_criterion']}")

    lines.extend(["", "## 安全与限制", ""])
    lines.extend(f"- {item}" for item in report["caveats"])
    return "\n".join(lines) + "\n"


def render_html(result: dict[str, Any]) -> str:
    report = result["report"]
    if result["status"] == "blocked":
        body = f"<h1>{escape(report['title'])}</h1><p class=\"headline\">{escape(report['headline'])}</p><p>{escape(report['summary'])}</p><h2>下一步</h2><p>{escape(report['next_action'])}</p>"
    else:
        calibration = result["knowledge_state"]["calibration"]
        gaps = "".join(
            "<tr>"
            f"<td>{escape(gap['priority'])}</td><td>{escape(gap['label'])}</td>"
            f"<td>{escape(str(gap['risk_score']))}</td><td>{escape(', '.join(gap['reason_codes']))}</td>"
            "</tr>"
            for gap in result["knowledge_state"]["blind_spots"]
        ) or "<tr><td colspan=\"4\">未检测到足够证据支持的高风险假设。</td></tr>"
        phases = "".join(
            f"<section><h3>阶段 {phase['phase']}：{escape(phase['name'])}</h3><p>{escape(phase['objective'])}</p><ul>"
            + "".join(
                f"<li><strong>{escape(step['label'])}</strong>：{escape(step['activity'])}<br><small>验收：{escape(step['exit_criterion'])}</small></li>"
                for step in phase["steps"]
            )
            + "</ul></section>"
            for phase in result["learning_plan"]["phases"]
        )
        caveats = "".join(f"<li>{escape(item)}</li>" for item in report["caveats"])
        body = f"""
<h1>{escape(report['title'])}</h1>
<p class=\"headline\">{escape(report['headline'])}</p>
<p>{escape(report['summary'])}</p>
<div class=\"metrics\"><div><span>校准状态</span><b>{escape(calibration['status'])}</b></div><div><span>期望校准误差</span><b>{escape(str(calibration['expected_calibration_error']))}</b></div><div><span>审计事件</span><b>{len(result['trace'])}</b></div></div>
<h2>待验证学习假设</h2><table><thead><tr><th>优先级</th><th>概念</th><th>风险分</th><th>依据</th></tr></thead><tbody>{gaps}</tbody></table>
<h2>学习路径</h2>{phases}
<h2>安全与限制</h2><ul>{caveats}</ul>
"""
    return f"""<!doctype html>
<html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>{escape(report['title'])}</title>
<style>body{{max-width:960px;margin:40px auto;padding:0 20px;font-family:system-ui,-apple-system,'Microsoft YaHei',sans-serif;color:#152033;line-height:1.6;background:#f7f9fc}}main{{background:#fff;border:1px solid #dfe7f2;border-radius:16px;padding:32px;box-shadow:0 10px 30px #10244a10}}h1{{margin-top:0}}.headline{{color:#174ea6;font-size:1.15rem;font-weight:700}}.metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}.metrics div{{background:#eef5ff;padding:14px;border-radius:10px}}.metrics span{{display:block;font-size:.8rem;color:#526276}}.metrics b{{font-size:1.2rem}}table{{width:100%;border-collapse:collapse}}th,td{{padding:10px;border-bottom:1px solid #e4eaf2;text-align:left;vertical-align:top}}small{{color:#526276}}section{{border-left:3px solid #3578e5;padding-left:16px;margin:20px 0}}@media(max-width:600px){{.metrics{{grid-template-columns:1fr}}}}</style></head>
<body><main>{body}</main></body></html>"""


def write_artifacts(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    """Persist privacy-minimized output artifacts and return their paths."""

    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    result_path = target / "result.json"
    trace_path = target / "trace.jsonl"
    input_summary_path = target / "input_sanitized.json"
    profile_path = target / "01_interaction_profile.json"
    learner_state_path = target / "02_learner_state.json"
    path_plan_path = target / "03_learning_path.json"
    verification_path = target / "04_report_verification.json"
    markdown_path = target / "report.md"
    html_path = target / "report.html"
    manifest_path = target / "manifest.json"

    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    trace_path.write_text(
        "".join(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n" for event in result["trace"]), encoding="utf-8"
    )
    markdown_path.write_text(render_markdown(result), encoding="utf-8")
    html_path.write_text(render_html(result), encoding="utf-8")
    input_summary_path.write_text(json.dumps(result["input_summary"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if result["status"] == "complete":
        profile_path.write_text(json.dumps(result["interaction_profile"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        learner_state_path.write_text(json.dumps(result["knowledge_state"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        path_plan_path.write_text(json.dumps(result["learning_plan"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        verification_path.write_text(json.dumps(result["report"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": result["run_id"],
        "status": result["status"],
        "artifacts": {
            path.name: sha256(path.read_bytes()).hexdigest()
            for path in (
                result_path,
                trace_path,
                input_summary_path,
                profile_path,
                learner_state_path,
                path_plan_path,
                verification_path,
                markdown_path,
                html_path,
            )
            if path.exists()
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "result": str(result_path),
        "input_summary": str(input_summary_path),
        "profile": str(profile_path) if profile_path.exists() else "",
        "learner_state": str(learner_state_path) if learner_state_path.exists() else "",
        "learning_path": str(path_plan_path) if path_plan_path.exists() else "",
        "verification": str(verification_path) if verification_path.exists() else "",
        "trace": str(trace_path),
        "markdown": str(markdown_path),
        "html": str(html_path),
        "manifest": str(manifest_path),
    }


def verify_artifacts(output_dir: str | Path) -> dict[str, Any]:
    """Verify the SHA-256 manifest emitted by :func:`write_artifacts`."""

    target = Path(output_dir)
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    failures: list[dict[str, str]] = []
    for name, expected_hash in manifest["artifacts"].items():
        path = target / name
        actual_hash = sha256(path.read_bytes()).hexdigest() if path.exists() else None
        if actual_hash != expected_hash:
            failures.append({"artifact": name, "expected": expected_hash, "actual": actual_hash or "missing"})
    return {"ok": not failures, "run_id": manifest["run_id"], "failures": failures}
