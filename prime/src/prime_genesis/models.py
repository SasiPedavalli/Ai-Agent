from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    input_text: str
    expected_terms: tuple[str, ...]
    forbidden_terms: tuple[str, ...] = ()
    domain: str = "general"


@dataclass(frozen=True)
class AgentVersion:
    version_id: str
    prompt: str
    parent_version_id: str | None
    mutation_type: str
    mutation_reason: str
    created_at: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    output: str
    quality: float
    safety: float
    reliability: float
    latency_ms: float
    estimated_cost_usd: float


@dataclass(frozen=True)
class Scorecard:
    version_id: str
    quality: float
    safety: float
    reliability: float
    latency_ms: float
    estimated_cost_usd: float
    composite: float
    results: tuple[CaseResult, ...]


@dataclass(frozen=True)
class PromotionDecision:
    champion_version_id: str
    challenger_version_id: str
    approved: bool
    reason: str
    deltas: dict[str, float]
    decided_at: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class EvolutionReport:
    run_id: str
    started_at: str
    completed_at: str
    previous_champion: str
    selected_champion: str
    scorecards: tuple[Scorecard, ...]
    decisions: tuple[PromotionDecision, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
