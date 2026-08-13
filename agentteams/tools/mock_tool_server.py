"""Run the HTTP tool gateway consumed by CogniGuide AgentTeams Workers."""

from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from typing import Any, Callable
from urllib.parse import unquote, urlparse

try:
    from .mock_tools import get_state, list_scenarios, reset_state
except ImportError:  # Supports `python tools/mock_tool_server.py`.
    from mock_tools import get_state, list_scenarios, reset_state


def call_tool(scenario_id: str, name: str, payload: dict[str, Any]) -> Any:
    tools = get_state(scenario_id)
    context = tools.authorize(name, payload)
    handlers: dict[str, Callable[[], Any]] = {
        "learning_data.get_task_metadata": lambda: tools.task_metadata(context),
        "learning_data.get_assessment_events": lambda: tools.assessment_events(context),
        "learning_data.get_interaction_observations": lambda: tools.interaction_observations(context),
        "framework.get_domain_pack": lambda: tools.domain_pack(context),
        "framework.get_bkt_parameters": lambda: tools.bkt_parameters(context),
        "evidence.verify_refs": lambda: tools.verify_evidence_refs(context, payload.get("evidence_refs", [])),
        "plan.validate_prerequisites": lambda: tools.validate_path(context, payload.get("plan", payload)),
        "audit.append": lambda: tools.append_audit(context, payload.get("event", payload)),
    }
    if name not in handlers:
        raise ValueError(f"unknown tool call {name!r}; available: {', '.join(sorted(handlers))}")
    return handlers[name]()


class MockToolHandler(BaseHTTPRequestHandler):
    server_version = "CogniGuideAgentTeamsToolGateway/0.1"
    max_request_bytes = 64 * 1024

    def _send(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("Content-Length must be an integer") from error
        if length < 0 or length > self.max_request_bytes:
            raise ValueError(f"request body must be between 0 and {self.max_request_bytes} bytes")
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        data = json.loads(raw) if raw.strip() else {}
        if not isinstance(data, dict):
            raise ValueError("request body must be a JSON object")
        return data

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parts = [unquote(part) for part in urlparse(self.path).path.strip("/").split("/") if part]
        try:
            if parts == ["health"]:
                self._send(HTTPStatus.OK, {"ok": True, "service": "cogniguide-agentteams-tool-gateway"})
                return
            if parts == ["scenarios"]:
                self._send(HTTPStatus.OK, {"ok": True, "result": list_scenarios()})
                return
            if len(parts) == 3 and parts[0] == "tools" and parts[2] == "trace":
                self._send(HTTPStatus.OK, {"ok": True, "result": get_state(parts[1]).trace_snapshot()})
                return
            if len(parts) == 3 and parts[0] == "tools" and parts[2] == "audit":
                self._send(HTTPStatus.OK, {"ok": True, "result": get_state(parts[1]).audit_snapshot()})
                return
            self._send(HTTPStatus.NOT_FOUND, {"ok": False, "error": "unknown endpoint"})
        except Exception as error:
            self._send(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})

    def do_POST(self) -> None:  # noqa: N802
        parts = [unquote(part) for part in urlparse(self.path).path.strip("/").split("/") if part]
        try:
            if len(parts) != 3 or parts[0] != "tools":
                self._send(HTTPStatus.NOT_FOUND, {"ok": False, "error": "expected /tools/{scenario_id}/{tool_call}"})
                return
            scenario_id, tool_call = parts[1], parts[2]
            payload = self._read_json()
            if tool_call == "reset":
                state = get_state(scenario_id)
                context = state.authorize("system.reset", payload)
                result = reset_state(scenario_id)
                result["request_context"] = context
            else:
                result = call_tool(scenario_id, tool_call, payload)
            self._send(HTTPStatus.OK, {"ok": True, "result": result})
        except PermissionError as error:
            self._send(HTTPStatus.FORBIDDEN, {"ok": False, "error": str(error)})
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            self._send(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
        except Exception as error:
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": "internal gateway error"})

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[cogniguide-tool-gateway] {self.address_string()} - {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the CogniGuide AgentTeams HTTP tool gateway.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=18089, type=int)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), MockToolHandler)
    print(f"CogniGuide AgentTeams tool gateway: http://{args.host}:{args.port}")
    print("Health: GET /health; tools: POST /tools/{scenario_id}/{tool_call}")
    server.serve_forever()


if __name__ == "__main__":
    main()
