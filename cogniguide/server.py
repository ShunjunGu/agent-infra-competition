"""Dependency-free local web server for the CogniGuide demo."""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from typing import Any

from .engine import InputValidationError, run_pipeline


REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_FILE = REPO_ROOT / "web" / "index.html"
SAMPLE_FILE = REPO_ROOT / "examples" / "python_foundations.json"
MAX_BODY_BYTES = 512 * 1024


class CogniGuideHandler(BaseHTTPRequestHandler):
    server_version = "CogniGuideDemo/0.1"

    def _send(self, status: HTTPStatus, body: str | bytes, content_type: str) -> None:
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/index.html"}:
            self._send(HTTPStatus.OK, WEB_FILE.read_bytes(), "text/html; charset=utf-8")
            return
        if self.path == "/examples/python_foundations.json":
            self._send(HTTPStatus.OK, SAMPLE_FILE.read_bytes(), "application/json; charset=utf-8")
            return
        if self.path == "/healthz":
            self._send(HTTPStatus.OK, '{"ok":true,"service":"cogniguide-demo"}\n', "application/json; charset=utf-8")
            return
        self._send(HTTPStatus.NOT_FOUND, '{"error":"not found"}\n', "application/json; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/analyze":
            self._send(HTTPStatus.NOT_FOUND, '{"error":"not found"}\n', "application/json; charset=utf-8")
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if not 0 < content_length <= MAX_BODY_BYTES:
                raise InputValidationError(f"请求体必须在 1 到 {MAX_BODY_BYTES} 字节之间")
            payload: Any = json.loads(self.rfile.read(content_length).decode("utf-8"))
            result = run_pipeline(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, InputValidationError) as error:
            body = json.dumps({"error": str(error)}, ensure_ascii=False) + "\n"
            self._send(HTTPStatus.BAD_REQUEST, body, "application/json; charset=utf-8")
            return
        self._send(HTTPStatus.OK, json.dumps(result, ensure_ascii=False) + "\n", "application/json; charset=utf-8")

    def log_message(self, format: str, *args: object) -> None:
        print(f"[cogniguide] {self.address_string()} - {format % args}")


def serve(host: str = "127.0.0.1", port: int = 8080) -> None:
    httpd = ThreadingHTTPServer((host, port), CogniGuideHandler)
    print(f"CogniGuide Demo: http://{host}:{port}")
    print("仅监听本机。按 Ctrl+C 停止。")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nCogniGuide Demo stopped.")
    finally:
        httpd.server_close()
