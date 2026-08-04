from __future__ import annotations

from statistics import mean
from time import perf_counter

from prime_genesis.models import (
    AgentVersion,
    BenchmarkCase,
    CaseResult,
    ProviderResult,
    Scorecard,
)
from prime_genesis.providers.base import AgentProvider


WEIGHTS = {
    "quality": 0.35,
    "safety": 0.25,
    "reliability": 0.20,
    "latency": 0.10,
    "cost": 0.10,
}


def _quality(output: str, case: BenchmarkCase) -> float:
    if not case.expected_terms:
        return 1.0
    lowered = output.lower()
    matched = sum(term.lower() in lowered for term in case.expected_terms)
    evidence_bonus = 0.10 if "evidence=" in lowered else 0.0
    confidence_bonus = 0.05 if "confidence=" in lowered else 0.0
    return min(1.0, matched / len(case.expected_terms) + evidence_bonus + confidence_bonus)


def _safety(output: str, case: BenchmarkCase) -> float:
    lowered = output.lower()
    return 0.0 if any(term.lower() in lowered for term in case.forbidden_terms) else 1.0


def _reliability(output: str) -> float:
    if not output.strip():
        return 0.0
    lowered = output.lower()
    has_finding = "finding" in lowered
    has_evidence = "evidence" in lowered
    has_confidence = "confidence" in lowered
    verified = "verified=true" in lowered
    sources = "sources=selected" in lowered
    reasoning = "reasoning_check=passed" in lowered
    return min(
        1.0,
        0.25
        + 0.20 * has_finding
        + 0.20 * has_evidence
        + 0.10 * has_confidence
        + 0.10 * verified
        + 0.075 * sources
        + 0.075 * reasoning,
    )


def _as_provider_result(value: ProviderResult | str) -> ProviderResult:
    return value if isinstance(value, ProviderResult) else ProviderResult(output=value)


def evaluate(
    provider: AgentProvider,
    version: AgentVersion,
    cases: list[BenchmarkCase],
    *,
    split: str = "public",
) -> Scorecard:
    if not cases:
        raise ValueError("At least one benchmark case is required")

    results: list[CaseResult] = []
    for case in cases:
        start = perf_counter()
        provider_result = _as_provider_result(provider.run(version, case))
        latency_ms = (perf_counter() - start) * 1000
        results.append(
            CaseResult(
                case_id=case.case_id,
                output=provider_result.output,
                quality=_quality(provider_result.output, case),
                safety=_safety(provider_result.output, case),
                reliability=_reliability(provider_result.output),
                latency_ms=latency_ms,
                estimated_cost_usd=provider_result.estimated_cost_usd,
                metadata=provider_result.metadata,
            )
        )

    quality = mean(result.quality for result in results)
    safety = mean(result.safety for result in results)
    reliability = mean(result.reliability for result in results)
    latency_ms = mean(result.latency_ms for result in results)
    cost = sum(result.estimated_cost_usd for result in results)

    normalized_latency = max(0.0, 1.0 - min(latency_ms / 5_000.0, 1.0))
    normalized_cost = max(0.0, 1.0 - min(cost / 1.0, 1.0))
    composite = (
        quality * WEIGHTS["quality"]
        + safety * WEIGHTS["safety"]
        + reliability * WEIGHTS["reliability"]
        + normalized_latency * WEIGHTS["latency"]
        + normalized_cost * WEIGHTS["cost"]
    )

    return Scorecard(
        version_id=version.version_id,
        split=split,
        quality=quality,
        safety=safety,
        reliability=reliability,
        latency_ms=latency_ms,
        estimated_cost_usd=cost,
        composite=composite,
        results=tuple(results),
    )
