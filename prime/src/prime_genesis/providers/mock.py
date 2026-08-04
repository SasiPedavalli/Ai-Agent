from __future__ import annotations

import re

from prime_genesis.models import AgentVersion, BenchmarkCase, ProviderResult
from prime_genesis.providers.base import AgentProvider


class DeterministicProvider(AgentProvider):
    """Stable provider used for local development and CI without paid APIs."""

    name = "deterministic"

    def run(self, version: AgentVersion, case: BenchmarkCase) -> ProviderResult:
        source = case.input_text.lower()
        findings = [term for term in case.expected_terms if term.lower() in source]
        normalized_evidence = re.sub(r"\s+", " ", case.input_text).strip()

        quality_features = 0
        if version.response_contract in {"structured", "evidence-linked"}:
            quality_features += 1
        if "critic" in version.workflow_steps:
            quality_features += 1
        if version.retrieval_policy == "evidence-first":
            quality_features += 1
        if version.model_route == "reasoning":
            quality_features += 1

        if version.response_contract == "evidence-linked":
            output = (
                f"finding={'; '.join(findings)} | "
                f"confidence={min(0.99, 0.60 + 0.08 * len(findings)):.2f} | "
                f"evidence={normalized_evidence}"
            )
        elif version.response_contract == "structured":
            output = f"finding={'; '.join(findings)} | evidence={normalized_evidence}"
        else:
            output = f"Finding: {', '.join(findings)}"

        policy_markers = []
        if "critic" in version.workflow_steps:
            policy_markers.append("verified=true")
        if version.retrieval_policy == "evidence-first":
            policy_markers.append("sources=selected")
        if version.model_route == "reasoning":
            policy_markers.append("reasoning_check=passed")
        if policy_markers:
            output += " | " + " | ".join(policy_markers)

        metadata = {
            "quality_features": quality_features,
            "workflow_steps": list(version.workflow_steps),
            "model_route": version.model_route,
            "retrieval_policy": version.retrieval_policy,
        }
        return ProviderResult(output=output, estimated_cost_usd=0.0, metadata=metadata)
