from __future__ import annotations

from abc import ABC, abstractmethod

from prime_genesis.models import AgentVersion, BenchmarkCase, ProviderResult


class AgentProvider(ABC):
    name = "abstract"

    @abstractmethod
    def run(self, version: AgentVersion, case: BenchmarkCase) -> ProviderResult | str:
        """Run one version against one benchmark case."""
        raise NotImplementedError
