from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class DataSource:
    name: str
    path: str
    owner: str
    domain: str
    environment: str = "dev"
    approved: bool = False
    lineage_registered: bool = False


@dataclass
class QualityFinding:
    check: str
    status: str
    details: str
    severity: str = "medium"


@dataclass
class AnomalyFinding:
    column: str
    value: Any
    row_number: int
    z_score: float
    severity: str = "medium"


@dataclass
class MetadataEnrichment:
    classifications: Dict[str, List[str]] = field(default_factory=dict)
    suggested_description: str = ""
    sensitivity: str = "internal"
    rationale: List[str] = field(default_factory=list)


@dataclass
class PolicyDecision:
    decision: str
    reasons: List[str]
    checks: Dict[str, bool]


@dataclass
class AgentRunResult:
    run_id: str
    agent_version: str
    source: Dict[str, Any]
    input_hash: str
    output_hash: str
    quality_score: float
    quality_findings: List[Dict[str, Any]]
    anomaly_findings: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    policy: Dict[str, Any]
    recommendations: List[str]
    trace: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
