from __future__ import annotations

from abc import ABC, abstractmethod

from prime_genesis.models import AgentVersion, BenchmarkCase


class AgentProvider(ABC):
    """Execution boundary for an LLM or deterministic test provider."""

    @abstractmethod
    def run(self, version: AgentVersion, case: BenchmarkCase) -> str:
        raise NotImplementedError
