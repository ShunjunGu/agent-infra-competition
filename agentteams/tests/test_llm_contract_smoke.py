from __future__ import annotations

import unittest

from agentteams.tools.llm_contract_smoke import (
    CHAT_COMPLETIONS,
    RESPONSES,
    chat_completions_url,
    completion_payload,
    extract_output_text,
    normalize_wire_api,
    normalized_completion_status,
    responses_url,
)


class LlmContractSmokeHelpersTests(unittest.TestCase):
    def test_normalizes_responses_urls(self) -> None:
        self.assertEqual(responses_url("https://provider.example"), "https://provider.example/v1/responses")
        self.assertEqual(responses_url("https://provider.example/v1/"), "https://provider.example/v1/responses")
        self.assertEqual(responses_url("https://provider.example/v1/responses"), "https://provider.example/v1/responses")

    def test_normalizes_deepseek_chat_completions_urls_and_aliases(self) -> None:
        self.assertEqual(chat_completions_url("https://api.deepseek.com"), "https://api.deepseek.com/chat/completions")
        self.assertEqual(
            chat_completions_url("https://api.deepseek.com/chat/completions"),
            "https://api.deepseek.com/chat/completions",
        )
        self.assertEqual(normalize_wire_api("chat_completions"), CHAT_COMPLETIONS)
        self.assertEqual(normalize_wire_api("responses"), RESPONSES)

    def test_builds_a_json_mode_chat_completion_request(self) -> None:
        payload = completion_payload("deepseek-v4-flash", "return JSON", 64, CHAT_COMPLETIONS)
        self.assertEqual(payload["model"], "deepseek-v4-flash")
        self.assertEqual(payload["messages"], [{"role": "user", "content": "return JSON"}])
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["max_tokens"], 64)

    def test_extracts_standard_responses_content_when_output_text_is_absent(self) -> None:
        response = {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": '{"status":"ok"}'}],
                }
            ]
        }
        self.assertEqual(extract_output_text(response), '{"status":"ok"}')

    def test_extracts_deepseek_chat_content_and_normalizes_status(self) -> None:
        response = {
            "model": "deepseek-v4-flash",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": '{"status":"ok"}'},
                }
            ],
        }
        self.assertEqual(extract_output_text(response, CHAT_COMPLETIONS), '{"status":"ok"}')
        self.assertEqual(normalized_completion_status(response, CHAT_COMPLETIONS), "completed")


if __name__ == "__main__":
    unittest.main()
