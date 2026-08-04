from __future__ import annotations

import unittest

from agentteams.tools.llm_contract_smoke import extract_output_text, responses_url


class LlmContractSmokeHelpersTests(unittest.TestCase):
    def test_normalizes_responses_urls(self) -> None:
        self.assertEqual(responses_url("https://provider.example"), "https://provider.example/v1/responses")
        self.assertEqual(responses_url("https://provider.example/v1/"), "https://provider.example/v1/responses")
        self.assertEqual(responses_url("https://provider.example/v1/responses"), "https://provider.example/v1/responses")

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


if __name__ == "__main__":
    unittest.main()
