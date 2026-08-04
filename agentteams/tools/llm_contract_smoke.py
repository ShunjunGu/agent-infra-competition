"""Check an OpenAI-compatible Responses endpoint without storing credentials.

This is a provider and structured-output smoke test only. It does not pretend to
run an AgentTeams Team; use the AgentTeams runbook for that end-to-end check.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


EXPECTED = {"status": "ok", "role": "report-verifier"}


def responses_url(base_url: str) -> str:
    base_url = base_url.rstrip("/")
    if base_url.endswith("/responses"):
        return base_url
    if base_url.endswith("/v1"):
        return f"{base_url}/responses"
    return f"{base_url}/v1/responses"


def extract_output_text(response: dict[str, Any]) -> str:
    direct = response.get("output_text")
    if isinstance(direct, str) and direct:
        return direct

    parts: list[str] = []
    for item in response.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str):
                    parts.append(text)
    return "".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test an OpenAI-compatible Responses API.")
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

    payload = json.dumps(
        {
            "model": args.model,
            "input": (
                "You are the CogniGuide Report Verifier health check. "
                'Return exactly {"status":"ok","role":"report-verifier"} and nothing else.'
            ),
            "max_output_tokens": 64,
        }
    ).encode("utf-8")
    request = Request(
        responses_url(args.base_url),
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )

    started = time.perf_counter()
    try:
        with urlopen(request, timeout=60) as result:
            response = json.loads(result.read().decode("utf-8"))
    except HTTPError as error:
        print(json.dumps({"ok": False, "error": f"HTTP {error.code}"}), file=sys.stderr)
        return 1
    except URLError as error:
        print(json.dumps({"ok": False, "error": f"network error: {error.reason}"}), file=sys.stderr)
        return 1

    output = extract_output_text(response)
    try:
        contract = json.loads(output)
    except json.JSONDecodeError:
        print(json.dumps({"ok": False, "error": "response did not contain the required JSON contract"}), file=sys.stderr)
        return 1
    if contract != EXPECTED:
        print(json.dumps({"ok": False, "error": "response violated the required JSON contract"}), file=sys.stderr)
        return 1

    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    print(
        json.dumps(
            {
                "ok": True,
                "model": response.get("model", args.model),
                "status": response.get("status"),
                "latency_ms": round((time.perf_counter() - started) * 1000),
                "total_tokens": usage.get("total_tokens"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
