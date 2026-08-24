from __future__ import annotations

from typing import Dict

from .models import DataSource, MetadataEnrichment, PolicyDecision


def evaluate_policy(
    source: DataSource,
    quality_score: float,
    metadata: MetadataEnrichment,
    anomaly_count: int,
    policy: Dict,
) -> PolicyDecision:
    min_quality = float(policy.get("min_quality_score", 90))
    max_anomalies = int(policy.get("max_anomalies", 0))
    require_owner = bool(policy.get("require_owner", True))
    require_lineage = bool(policy.get("require_lineage", True))
    block_unapproved = bool(policy.get("block_unapproved_sources", True))

    checks = {
        "approved_governed_source": (source.approved or not block_unapproved),
        "owner_present": (bool(source.owner.strip()) or not require_owner),
        "lineage_registered": (source.lineage_registered or not require_lineage),
        "data_quality_threshold": quality_score >= min_quality,
        "anomaly_threshold": anomaly_count <= max_anomalies,
        "classification_present_for_sensitive_data": (
            metadata.sensitivity == "internal" or bool(metadata.classifications)
        ),
    }

    reasons = [name for name, ok in checks.items() if not ok]
    decision = "ALLOW" if all(checks.values()) else "BLOCK"
    return PolicyDecision(decision=decision, reasons=reasons, checks=checks)
