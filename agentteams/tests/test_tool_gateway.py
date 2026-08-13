"""Regression tests for the AgentTeams HTTP tool gateway."""

from __future__ import annotations

import json
from http.client import HTTPResponse
from http.server import ThreadingHTTPServer
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from agentteams.tools.mock_tool_server import MockToolHandler, call_tool
from agentteams.tools.mock_tools import REQUEST_SCHEMA_VERSION, get_state, reset_state


def request_body(actor: str, *, task_id: str = "CG-1001", trace_id: str = "cg1001-test-001", **extra: object) -> dict[str, object]:
    return {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "task_id": task_id,
        "trace_id": trace_id,
        "actor": actor,
        **extra,
    }


class ToolGatewayPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_state("python_foundations_overconfidence")
        reset_state("consent_required")

    def test_metadata_requires_complete_request_envelope(self) -> None:
        with self.assertRaisesRegex(ValueError, "schema_version"):
            call_tool("python_foundations_overconfidence", "learning_data.get_task_metadata", {})

        with self.assertRaisesRegex(PermissionError, "task_id"):
            call_tool(
                "python_foundations_overconfidence",
                "learning_data.get_task_metadata",
                request_body("interaction-evidence-analyst", task_id="CG-9999"),
            )

    def test_role_policy_and_consent_fail_closed(self) -> None:
        events = call_tool(
            "python_foundations_overconfidence",
            "learning_data.get_assessment_events",
            request_body("interaction-evidence-analyst"),
        )
        self.assertEqual(len(events), 6)

        with self.assertRaisesRegex(PermissionError, "not allowed"):
            call_tool(
                "python_foundations_overconfidence",
                "learning_data.get_assessment_events",
                request_body("learning-path-planner"),
            )

        with self.assertRaisesRegex(PermissionError, "not authorized"):
            call_tool(
                "consent_required",
                "learning_data.get_assessment_events",
                request_body("interaction-evidence-analyst", task_id="CG-1002"),
            )

        with self.assertRaisesRegex(PermissionError, "not authorized"):
            call_tool(
                "consent_required",
                "evidence.verify_refs",
                request_body("report-verifier", task_id="CG-1002", evidence_refs=["evt-hidden-01"]),
            )

    def test_trace_records_context_but_not_request_content(self) -> None:
        payload = request_body(
            "learning-path-planner",
            plan={"ordered_concepts": ["variables", "expressions"], "freeform_note": "must not be retained"},
        )
        result = call_tool("python_foundations_overconfidence", "plan.validate_prerequisites", payload)
        self.assertTrue(result["valid"])

        trace = get_state("python_foundations_overconfidence").trace_snapshot()
        self.assertEqual(len(trace), 1)
        self.assertEqual(trace[0]["request_context"]["actor"], "learning-path-planner")
        self.assertIn("args_hash", trace[0])
        self.assertNotIn("args", trace[0])
        self.assertNotIn("must not be retained", json.dumps(trace))
        self.assertTrue(trace[0]["time"].endswith("Z"))

    def test_path_validation_detects_duplicates_and_external_actions(self) -> None:
        duplicate = call_tool(
            "python_foundations_overconfidence",
            "plan.validate_prerequisites",
            request_body(
                "learning-path-planner",
                plan={"ordered_concepts": ["variables", "variables", "expressions"]},
            ),
        )
        self.assertFalse(duplicate["valid"])
        self.assertEqual(duplicate["duplicate_concepts"], ["variables"])

        external_action = call_tool(
            "python_foundations_overconfidence",
            "plan.validate_prerequisites",
            request_body(
                "learning-path-planner",
                plan={"ordered_concepts": ["variables", "expressions"], "external_actions": ["send_email"]},
            ),
        )
        self.assertFalse(external_action["valid"])
        self.assertTrue(external_action["requires_external_action"])

    def test_audit_event_is_bound_to_request_context_and_scrubbed(self) -> None:
        payload = request_body(
            "interaction-evidence-analyst",
            event={
                "task_id": "CG-1001",
                "trace_id": "cg1001-test-001",
                "actor": "interaction-evidence-analyst",
                "event": "consent_checked",
                "status": "AUTHORIZED",
                "evidence_refs": ["evt-functions-01"],
                "raw_text": "do not retain this learner text",
                "chain_of_thought": "do not retain reasoning",
                "api_key": "do-not-retain",
            },
        )
        result = call_tool("python_foundations_overconfidence", "audit.append", payload)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["dropped_fields"], ["api_key", "chain_of_thought", "raw_text"])

        audit = get_state("python_foundations_overconfidence").audit_snapshot()
        self.assertEqual(len(audit), 1)
        serialized = json.dumps(audit)
        self.assertNotIn("do not retain", serialized)
        self.assertNotIn("raw_text", serialized)


class ToolGatewayHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), MockToolHandler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address[:2]
        cls.base_url = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self) -> None:
        reset_state("python_foundations_overconfidence")
        reset_state("consent_required")

    def _post(self, path: str, payload: dict[str, object]) -> tuple[int, dict[str, object]]:
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            response: HTTPResponse = urlopen(request, timeout=2)
        except HTTPError as error:
            return error.code, json.loads(error.read().decode("utf-8"))
        with response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_http_metadata_and_policy_statuses(self) -> None:
        with urlopen(f"{self.base_url}/health", timeout=2) as response:
            self.assertEqual(response.status, 200)
            self.assertTrue(json.loads(response.read().decode("utf-8"))["ok"])

        status, body = self._post(
            "/tools/python_foundations_overconfidence/learning_data.get_task_metadata",
            request_body("interaction-evidence-analyst"),
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])

        status, body = self._post(
            "/tools/python_foundations_overconfidence/learning_data.get_assessment_events",
            request_body("learning-path-planner"),
        )
        self.assertEqual(status, 403)
        self.assertFalse(body["ok"])

        status, body = self._post(
            "/tools/consent_required/learning_data.get_assessment_events",
            request_body("interaction-evidence-analyst", task_id="CG-1002"),
        )
        self.assertEqual(status, 403)
        self.assertIn("not authorized", str(body["error"]))


if __name__ == "__main__":
    unittest.main()
