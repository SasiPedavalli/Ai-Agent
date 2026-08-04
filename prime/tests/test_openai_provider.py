from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from prime_genesis.engine import DEFAULT_CHAMPION
from prime_genesis.models import BenchmarkCase
from prime_genesis.providers.openai_responses import OpenAIResponsesProvider


class FakeResponses:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            id="resp_test",
            output_text="finding=test | evidence=test input",
            usage=SimpleNamespace(input_tokens=100, output_tokens=50),
        )


class OpenAIProviderTests(unittest.TestCase):
    def test_adapter_uses_responses_api_without_storage(self) -> None:
        responses = FakeResponses()
        client = SimpleNamespace(responses=responses)
        case = BenchmarkCase(
            case_id="case-1",
            input_text="test input",
            expected_terms=("test",),
        )
        with patch.dict(
            os.environ,
            {
                "PRIME_INPUT_COST_PER_MILLION": "2",
                "PRIME_OUTPUT_COST_PER_MILLION": "8",
            },
            clear=False,
        ):
            result = OpenAIResponsesProvider(model="gpt-test", client=client).run(
                DEFAULT_CHAMPION, case
            )
        self.assertEqual(responses.kwargs["model"], "gpt-test")
        self.assertFalse(responses.kwargs["store"])
        self.assertEqual(responses.kwargs["metadata"]["prime_case"], "case-1")
        self.assertAlmostEqual(result.estimated_cost_usd, 0.0006)
        self.assertEqual(result.metadata["input_tokens"], 100)


if __name__ == "__main__":
    unittest.main()
