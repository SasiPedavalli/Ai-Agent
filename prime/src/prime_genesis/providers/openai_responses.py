from __future__ import annotations

import os
from typing import Any

from prime_genesis.models import AgentVersion, BenchmarkCase, ProviderResult
from prime_genesis.providers.base import AgentProvider


class OpenAIResponsesProvider(AgentProvider):
    """Optional real-model adapter built on OpenAI's Responses API.

    The adapter deliberately sets ``store=False`` and does not hard-code model
    pricing. Cost is estimated only when per-million-token rates are supplied
    through environment variables.
    """

    name = "openai-responses"

    def __init__(self, model: str | None = None, client: Any | None = None) -> None:
        self.model = model or os.getenv("PRIME_OPENAI_MODEL", "gpt-5")
        if client is not None:
            self.client = client
            return
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI support is optional. Install with: pip install -e '.[openai]'"
            ) from exc
        self.client = OpenAI()

    @staticmethod
    def _instructions(version: AgentVersion) -> str:
        workflow = " -> ".join(version.workflow_steps)
        return (
            f"{version.prompt}\n\n"
            f"Workflow: {workflow}. "
            f"Retrieval policy: {version.retrieval_policy}. "
            f"Response contract: {version.response_contract}. "
            "Use only evidence supplied in the case."
        )

    @staticmethod
    def _token_count(usage: Any, name: str) -> int:
        value = getattr(usage, name, 0) if usage is not None else 0
        return int(value or 0)

    @staticmethod
    def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
        input_rate = float(os.getenv("PRIME_INPUT_COST_PER_MILLION", "0"))
        output_rate = float(os.getenv("PRIME_OUTPUT_COST_PER_MILLION", "0"))
        return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000

    def run(self, version: AgentVersion, case: BenchmarkCase) -> ProviderResult:
        response = self.client.responses.create(
            model=self.model,
            instructions=self._instructions(version),
            input=case.input_text,
            store=False,
            metadata={
                "prime_version": version.version_id,
                "prime_case": case.case_id,
                "prime_generation": str(version.generation),
            },
        )
        usage = getattr(response, "usage", None)
        input_tokens = self._token_count(usage, "input_tokens")
        output_tokens = self._token_count(usage, "output_tokens")
        return ProviderResult(
            output=str(getattr(response, "output_text", "")),
            estimated_cost_usd=self._estimate_cost(input_tokens, output_tokens),
            metadata={
                "model": self.model,
                "response_id": getattr(response, "id", None),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "pricing_configured": bool(
                    os.getenv("PRIME_INPUT_COST_PER_MILLION")
                    or os.getenv("PRIME_OUTPUT_COST_PER_MILLION")
                ),
            },
        )
