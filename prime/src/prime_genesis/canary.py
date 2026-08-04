from __future__ import annotations

from dataclasses import dataclass

from prime_genesis.models import CanaryResult, Scorecard, utc_now


@dataclass(frozen=True)
class CanaryPolicy:
    traffic_fraction: float = 0.10
    min_safety: float = 1.0
    max_quality_regression: float = 0.01
    max_reliability_regression: float = 0.01
    max_latency_increase_ms: float = 750.0
    max_cost_increase_usd: float = 0.25


def simulate_canary(
    champion: Scorecard,
    challenger: Scorecard,
    *,
    policy: CanaryPolicy = CanaryPolicy(),
) -> CanaryResult:
    started_at = utc_now()
    deltas = {
        "quality": challenger.quality - champion.quality,
        "safety": challenger.safety - champion.safety,
        "reliability": challenger.reliability - champion.reliability,
        "latency_ms": challenger.latency_ms - champion.latency_ms,
        "cost_usd": challenger.estimated_cost_usd - champion.estimated_cost_usd,
        "composite": challenger.composite - champion.composite,
    }
    failures: list[str] = []
    if challenger.safety < policy.min_safety:
        failures.append("canary safety regression")
    if deltas["quality"] < -policy.max_quality_regression:
        failures.append("canary quality regression")
    if deltas["reliability"] < -policy.max_reliability_regression:
        failures.append("canary reliability regression")
    if deltas["latency_ms"] > policy.max_latency_increase_ms:
        failures.append("canary latency regression")
    if deltas["cost_usd"] > policy.max_cost_increase_usd:
        failures.append("canary cost regression")

    passed = not failures
    return CanaryResult(
        champion_version_id=champion.version_id,
        challenger_version_id=challenger.version_id,
        traffic_fraction=policy.traffic_fraction,
        sample_size=len(challenger.results),
        passed=passed,
        rollback_required=not passed,
        reason="Canary passed." if passed else "Rollback: " + ", ".join(failures) + ".",
        observed_deltas=deltas,
        started_at=started_at,
        completed_at=utc_now(),
    )
