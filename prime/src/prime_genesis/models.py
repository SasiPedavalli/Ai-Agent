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
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class AgentVersion:
    version_id: str
    prompt: str
    parent_version_id: str | None
    mutation_type: str
    mutation_reason: str
    generation: int = 0
    workflow_steps: tuple[str, ...] = ("analyze", "verify", "answer")
    model_route: str = "balanced"
    retrieval_policy: str = "input-only"
    response_contract: str = "plain"
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentVersion":
        data = dict(payload)
        if "workflow_steps" in data:
            data["workflow_steps"] = tuple(data["workflow_steps"])
        return cls(**data)


@dataclass(frozen=True)
class ProviderResult:
    output: str
    estimated_cost_usd: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    output: str
    quality: float
    safety: float
    reliability: float
    latency_ms: float
    estimated_cost_usd: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Scorecard:
    version_id: str
    split: str
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
    stage: str = "benchmark"
    decided_at: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class CanaryResult:
    champion_version_id: str
    challenger_version_id: str
    traffic_fraction: float
    sample_size: int
    passed: bool
    rollback_required: bool
    reason: str
    observed_deltas: dict[str, float]
    started_at: str
    completed_at: str


@dataclass(frozen=True)
class EvolutionReport:
    run_id: str
    started_at: str
    completed_at: str
    previous_champion: str
    selected_champion: str
    promoted: bool
    rollback_performed: bool
    provider_name: str
    scorecards: tuple[Scorecard, ...]
    decisions: tuple[PromotionDecision, ...]
    canaries: tuple[CanaryResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
