from __future__ import annotations

import json
from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen

from cogniguide.engine import run_pipeline, verify_artifacts, write_artifacts
from cogniguide.server import CogniGuideHandler


ROOT = Path(__file__).resolve().parents[1]


class CogniGuideEngineTests(unittest.TestCase):
    def load_example(self, name: str) -> dict:
        return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))

    def test_complete_pipeline_generates_auditable_multi_agent_result(self) -> None:
        result = run_pipeline(self.load_example("python_foundations.json"))

        self.assertEqual(result["status"], "complete")
        self.assertGreaterEqual(len(result["trace"]), 7)
        self.assertEqual(
            [event["agent"] for event in result["trace"][:6]],
            [
                "team-leader",
                "consent-boundary-agent",
                "interaction-analyst",
                "knowledge-state-estimator",
                "learning-path-planner",
                "report-verifier",
            ],
        )
        gap_concepts = {gap["concept"] for gap in result["knowledge_state"]["blind_spots"]}
        self.assertIn("functions", gap_concepts)
        self.assertTrue(result["report"]["human_review"]["required"])

    def test_consent_gate_blocks_content_analysis(self) -> None:
        result = run_pipeline(self.load_example("consent_required.json"))

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(len(result["trace"]), 3)
        self.assertEqual(result["policy"]["decision"], "block")

    def test_cold_start_never_emits_a_high_priority_diagnosis(self) -> None:
        result = run_pipeline(self.load_example("insufficient_evidence.json"))

        priorities = {gap["priority"] for gap in result["knowledge_state"]["blind_spots"]}
        self.assertIn("needs_more_data", priorities)
        self.assertNotIn("high", priorities)

    def test_reassessment_increases_function_mastery(self) -> None:
        before = run_pipeline(self.load_example("python_foundations.json"))
        after = run_pipeline(self.load_example("python_foundations_reassessment.json"))
        before_functions = next(
            state for state in before["knowledge_state"]["concept_states"] if state["concept"] == "functions"
        )
        after_functions = next(
            state for state in after["knowledge_state"]["concept_states"] if state["concept"] == "functions"
        )
        self.assertGreater(
            after_functions["knowledge_tracing"]["mastery"],
            before_functions["knowledge_tracing"]["mastery"],
        )

    def test_local_web_api_serves_ui_and_runs_analysis(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), CogniGuideHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(f"{base_url}/", timeout=3) as response:
                page = response.read().decode("utf-8")
            self.assertIn("CogniGuide", page)
            request = Request(
                f"{base_url}/api/analyze",
                data=json.dumps(self.load_example("python_foundations.json")).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=3) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(payload["status"], "complete")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_result_does_not_echo_raw_interaction_text(self) -> None:
        payload = self.load_example("python_foundations.json")
        secret_like_text = "联系我：learner@example.com，电话 13800138000"
        payload["interactions"].append(
            {
                "topic": "functions",
                "question_type": "reflection",
                "evidence_id": "privacy-test-01",
                "content": secret_like_text,
            }
        )

        result = run_pipeline(payload)

        self.assertNotIn(secret_like_text, json.dumps(result, ensure_ascii=False))
        self.assertEqual(result["policy"]["privacy_findings"], {"email": 1, "phone": 1})

    def test_artifacts_include_tamper_evident_manifest(self) -> None:
        result = run_pipeline(self.load_example("python_foundations.json"))
        with tempfile.TemporaryDirectory() as directory:
            artifacts = write_artifacts(result, directory)
            manifest = json.loads(Path(artifacts["manifest"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "complete")
            self.assertIn("01_interaction_profile.json", manifest["artifacts"])
            self.assertTrue(verify_artifacts(directory)["ok"])
            Path(artifacts["markdown"]).write_text("tampered\n", encoding="utf-8")
            self.assertFalse(verify_artifacts(directory)["ok"])


if __name__ == "__main__":
    unittest.main()
