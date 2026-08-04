#!/usr/bin/env python3
"""Demonstrate the CogniGuide plan-monitor-reflect-replan closed loop."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from cogniguide.engine import InputValidationError, run_pipeline, write_artifacts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CogniGuide initial assessment and reassessment")
    parser.add_argument("--initial", type=Path, default=Path("examples/python_foundations.json"))
    parser.add_argument("--reassessment", type=Path, default=Path("examples/python_foundations_reassessment.json"))
    parser.add_argument("--output", type=Path, default=Path("runs/closed-loop"))
    return parser.parse_args()


def mastery_by_concept(result: dict) -> dict[str, float]:
    return {
        state["concept"]: state["knowledge_tracing"]["mastery"]
        for state in result["knowledge_state"]["concept_states"]
    }


def main() -> int:
    args = parse_args()
    try:
        initial = run_pipeline(json.loads(args.initial.read_text(encoding="utf-8")))
        reassessment = run_pipeline(json.loads(args.reassessment.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, InputValidationError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2

    initial_artifacts = write_artifacts(initial, args.output / "round-1")
    reassessment_artifacts = write_artifacts(reassessment, args.output / "round-2")
    before = mastery_by_concept(initial)
    after = mastery_by_concept(reassessment)
    deltas = [
        {
            "concept": concept,
            "round_1_mastery": before.get(concept),
            "round_2_mastery": after.get(concept),
            "delta": round(after.get(concept, 0) - before.get(concept, 0), 3),
        }
        for concept in sorted(set(before) | set(after))
    ]
    comparison = {
        "purpose": "演示新评估证据如何触发 BKT 状态更新和学习路径重规划，不主张证明真实学习效果。",
        "round_1": {"run_id": initial["run_id"], "status": initial["status"]},
        "round_2": {"run_id": reassessment["run_id"], "status": reassessment["status"]},
        "mastery_deltas": deltas,
        "artifacts": {"round_1_report": initial_artifacts["html"], "round_2_report": reassessment_artifacts["html"]},
    }
    comparison_path = args.output / "closed_loop_comparison.json"
    comparison_path.parent.mkdir(parents=True, exist_ok=True)
    comparison_path.write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("闭环演示完成。")
    print(f"比较结果: {comparison_path}")
    for delta in deltas:
        print(f"  {delta['concept']}: {delta['round_1_mastery']} -> {delta['round_2_mastery']} ({delta['delta']:+})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
