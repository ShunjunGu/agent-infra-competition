"""Check a real OpenAI-compatible model endpoint without storing credentials.

DeepSeek's documented OpenAI-compatible interface uses Chat Completions. The
adapter retains OpenAI Responses support for portability, but defaults to the
DeepSeek profile so the competition demo has a concrete, runnable backend.
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


CHAT_COMPLETIONS = "chat-completions"
RESPONSES = "responses"
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-flash"
EXPECTED = {"status": "ok", "role": "report-verifier"}


def normalize_wire_api(value: str) -> str:
    normalized = value.strip().lower().replace("_", "-")
    aliases = {
        "chat": CHAT_COMPLETIONS,
        "chat-completion": CHAT_COMPLETIONS,
        "chat-completions": CHAT_COMPLETIONS,
        "response": RESPONSES,
        "responses": RESPONSES,
    }
    if normalized not in aliases:
        raise ValueError("wire API must be chat-completions or responses")
    return aliases[normalized]


def responses_url(base_url: str) -> str:
    """Return a Responses endpoint; retained for OpenAI-compatible fallback."""

    base_url = base_url.rstrip("/")
    if base_url.endswith("/responses"):
        return base_url
    if base_url.endswith("/v1"):
        return f"{base_url}/responses"
    return f"{base_url}/v1/responses"


def chat_completions_url(base_url: str) -> str:
    base_url = base_url.rstrip("/")
    if base_url.endswith("/chat/completions"):
        return base_url
    return f"{base_url}/chat/completions"


def completion_url(base_url: str, wire_api: str) -> str:
    wire_api = normalize_wire_api(wire_api)
    if wire_api == CHAT_COMPLETIONS:
        return chat_completions_url(base_url)
    return responses_url(base_url)


def completion_payload(model: str, prompt: str, max_output_tokens: int, wire_api: str) -> dict[str, Any]:
    wire_api = normalize_wire_api(wire_api)
    if wire_api == CHAT_COMPLETIONS:
        return {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": max_output_tokens,
            "response_format": {"type": "json_object"},
        }
    return {"model": model, "input": prompt, "max_output_tokens": max_output_tokens}


def extract_output_text(response: dict[str, Any], wire_api: str = RESPONSES) -> str:
    wire_api = normalize_wire_api(wire_api)
    if wire_api == CHAT_COMPLETIONS:
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return ""
        message = first_choice.get("message")
        if not isinstance(message, dict):
            return ""
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and isinstance(item.get("text"), str)
            )
        return ""

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


def normalized_completion_status(response: dict[str, Any], wire_api: str) -> str:
    wire_api = normalize_wire_api(wire_api)
    if wire_api == RESPONSES:
        return str(response.get("status", ""))
    choices = response.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(message, dict) and extract_output_text(response, wire_api):
            return "completed"
    return ""


def invoke_completion(
    base_url: str,
    model: str,
    api_key: str,
    prompt: str,
    *,
    wire_api: str,
    max_output_tokens: int,
    timeout_seconds: int = 90,
) -> dict[str, Any]:
    payload = completion_payload(model, prompt, max_output_tokens, wire_api)
    request = Request(
        completion_url(base_url, wire_api),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as result:
            return json.loads(result.read().decode("utf-8"))
    except HTTPError as error:
        raise RuntimeError(f"provider returned HTTP {error.code}") from error
    except URLError as error:
        raise RuntimeError(f"provider network error: {error.reason}") from error


def env_value(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test a real OpenAI-compatible model endpoint.")
    parser.add_argument(
        "--base-url",
        default=env_value("DEEPSEEK_BASE_URL", "OPENAI_BASE_URL", "AT_LLM_BASE_URL", default=DEFAULT_BASE_URL),
    )
    parser.add_argument(
        "--model",
        default=env_value("DEEPSEEK_MODEL", "OPENAI_MODEL", "AT_MODEL", default=DEFAULT_MODEL),
    )
    parser.add_argument(
        "--wire-api",
        default=env_value("DEEPSEEK_WIRE_API", "AT_LLM_WIRE_API", default=CHAT_COMPLETIONS),
        help="chat-completions (DeepSeek default) or responses",
    )
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    args = parser.parse_args()

    try:
        wire_api = normalize_wire_api(args.wire_api)
    except ValueError as error:
        parser.error(str(error))
    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        parser.error(f"set the API key in environment variable {args.api_key_env}")

    prompt = (
        "You are the CogniGuide Report Verifier health check. "
        'Return exactly this JSON object and nothing else: {"status":"ok","role":"report-verifier"}.'
    )
    started = time.perf_counter()
    try:
        response = invoke_completion(
            args.base_url,
            args.model,
            api_key,
            prompt,
            wire_api=wire_api,
            # DeepSeek V4 can spend part of completion budget on hidden
            # reasoning before emitting the JSON response.
            max_output_tokens=256,
        )
    except RuntimeError as error:
        print(json.dumps({"ok": False, "error": str(error)}), file=sys.stderr)
        return 1

    output = extract_output_text(response, wire_api)
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
                "wire_api": wire_api,
                "status": normalized_completion_status(response, wire_api),
                "latency_ms": round((time.perf_counter() - started) * 1000),
                "total_tokens": usage.get("total_tokens"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
