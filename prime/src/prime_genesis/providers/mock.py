from __future__ import annotations

import re

from prime_genesis.models import AgentVersion, BenchmarkCase
from prime_genesis.providers.base import AgentProvider


class DeterministicProvider(AgentProvider):
    """Stable provider used for local development and CI without paid APIs."""

    def run(self, version: AgentVersion, case: BenchmarkCase) -> str:
        source = case.input_text.lower()
        findings = [term for term in case.expected_terms if term.lower() in source]
        prompt = version.prompt.lower()

        if "evidence-linked" in prompt:
            return (
                f"finding={'; '.join(findings)} | "
                f"confidence={min(0.99, 0.55 + 0.12 * len(findings)):.2f} | "
                f"evidence={re.sub(r'\s+', ' ', case.input_text).strip()}"
            )
        if "structured" in prompt:
            return f"finding={'; '.join(findings)} | evidence=available"
        return f"Finding: {', '.join(findings)}"
