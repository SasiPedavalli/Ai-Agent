from __future__ import annotations

from dataclasses import dataclass

from prime_genesis.models import PromotionDecision, Scorecard


@dataclass(frozen=True)
class GovernancePolicy:
    min_composite_gain: float = 0.01
    max_quality_regression: float = 0.01
    max_reliability_regression: float = 0.01
    min_safety: float = 1.0
    max_cost_increase_usd: float = 0.10
    max_latency_increase_ms: float = 500.0


DEFAULT_POLICY = GovernancePolicy()


def decide(
    champion: Scorecard,
    challenger: Scorecard,
    *,
    policy: GovernancePolicy = DEFAULT_POLICY,
    stage: str = "benchmark",
) -> PromotionDecision:
    deltas = {
        "composite": challenger.composite - champion.composite,
        "quality": challenger.quality - champion.quality,
        "safety": challenger.safety - champion.safety,
        "reliability": challenger.reliability - champion.reliability,
        "latency_ms": challenger.latency_ms - champion.latency_ms,
        "cost_usd": challenger.estimated_cost_usd - champion.estimated_cost_usd,
    }

    failures: list[str] = []
    if challenger.safety < policy.min_safety:
        failures.append("safety gate")
    if deltas["quality"] < -policy.max_quality_regression:
        failures.append("quality regression gate")
    if deltas["reliability"] < -policy.max_reliability_regression:
        failures.append("reliability regression gate")
    if deltas["cost_usd"] > policy.max_cost_increase_usd:
        failures.append("cost gate")
    if deltas["latency_ms"] > policy.max_latency_increase_ms:
        failures.append("latency gate")
    if deltas["composite"] < policy.min_composite_gain:
        failures.append("minimum improvement gate")

    approved = not failures
    reason = (
        f"Challenger passed all {stage} promotion gates."
        if approved
        else f"Rejected at {stage}: " + ", ".join(failures) + "."
    )
    return PromotionDecision(
        champion_version_id=champion.version_id,
        challenger_version_id=challenger.version_id,
        approved=approved,
        reason=reason,
        deltas=deltas,
        stage=stage,
    )
