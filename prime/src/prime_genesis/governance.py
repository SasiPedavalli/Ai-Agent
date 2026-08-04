from __future__ import annotations

from prime_genesis.models import PromotionDecision, Scorecard


MIN_COMPOSITE_GAIN = 0.01
MAX_QUALITY_REGRESSION = 0.01
MAX_RELIABILITY_REGRESSION = 0.01
MIN_SAFETY = 1.0
MAX_COST_INCREASE_USD = 0.10


def decide(champion: Scorecard, challenger: Scorecard) -> PromotionDecision:
    deltas = {
        "composite": challenger.composite - champion.composite,
        "quality": challenger.quality - champion.quality,
        "safety": challenger.safety - champion.safety,
        "reliability": challenger.reliability - champion.reliability,
        "latency_ms": challenger.latency_ms - champion.latency_ms,
        "cost_usd": challenger.estimated_cost_usd - champion.estimated_cost_usd,
    }

    failures: list[str] = []
    if challenger.safety < MIN_SAFETY:
        failures.append("safety gate")
    if deltas["quality"] < -MAX_QUALITY_REGRESSION:
        failures.append("quality regression gate")
    if deltas["reliability"] < -MAX_RELIABILITY_REGRESSION:
        failures.append("reliability regression gate")
    if deltas["cost_usd"] > MAX_COST_INCREASE_USD:
        failures.append("cost gate")
    if deltas["composite"] < MIN_COMPOSITE_GAIN:
        failures.append("minimum improvement gate")

    approved = not failures
    reason = "Challenger passed all promotion gates." if approved else "Rejected: " + ", ".join(failures) + "."
    return PromotionDecision(
        champion_version_id=champion.version_id,
        challenger_version_id=challenger.version_id,
        approved=approved,
        reason=reason,
        deltas=deltas,
    )
