from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from .audit import AuditStore
from .metadata import enrich_metadata
from .models import AgentRunResult, DataSource
from .policy import evaluate_policy
from .purview import MockPurviewGateway, PurviewGateway
from .quality import detect_numeric_anomalies, load_csv, run_quality_checks


AGENT_VERSION = "1.0.0"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class GovernedDataAIAgent:
    """Agentic governance workflow with deterministic safety gates outside the LLM."""

    def __init__(
        self,
        policy: Dict,
        audit_store: AuditStore,
        purview_gateway: PurviewGateway | None = None,
    ) -> None:
        self.policy = policy
        self.audit_store = audit_store
        self.purview = purview_gateway or MockPurviewGateway()

    def run(self, source: DataSource, rules: Dict) -> AgentRunResult:
        created_at = datetime.now(timezone.utc).isoformat()
        run_id = str(uuid.uuid4())
        raw = Path(source.path).read_bytes()
        input_hash = sha256_bytes(raw)

        columns, rows = load_csv(source.path)
        quality_score, quality_findings = run_quality_checks(columns, rows, rules)
        anomalies = detect_numeric_anomalies(
            rows,
            rules.get("numeric_columns", []),
            float(rules.get("z_threshold", 3.0)),
        )
        metadata = enrich_metadata(columns, source.domain)
        decision = evaluate_policy(
            source=source,
            quality_score=quality_score,
            metadata=metadata,
            anomaly_count=len(anomalies),
            policy=self.policy,
        )

        recommendations = []
        if decision.decision == "BLOCK":
            recommendations.append(
                "Keep the asset out of the production promotion path until failed governance and policy checks are remediated."
            )
        if quality_score < float(self.policy.get("min_quality_score", 90)):
            recommendations.append("Remediate failed data quality checks and rerun the agent.")
        if anomalies:
            recommendations.append("Review anomaly findings before approving downstream BI or AI use.")
        if metadata.classifications:
            recommendations.append(
                "Apply Microsoft Purview classifications and validate RBAC/access control for sensitive columns."
            )
        if not recommendations:
            recommendations.append(
                "Asset satisfies the current governed-data policy and is eligible for environment promotion."
            )

        prehash_payload = {
            "run_id": run_id,
            "agent_version": AGENT_VERSION,
            "source": asdict(source),
            "input_hash": input_hash,
            "quality_score": quality_score,
            "quality_findings": [asdict(x) for x in quality_findings],
            "anomaly_findings": [asdict(x) for x in anomalies],
            "metadata": asdict(metadata),
            "policy": asdict(decision),
            "recommendations": recommendations,
        }
        output_hash = sha256_bytes(json.dumps(prehash_payload, sort_keys=True).encode())

        trace = {
            "created_at": created_at,
            "agent_stage_sequence": [
                "approved-governed-source check",
                "metadata enrichment",
                "data quality checks",
                "anomaly detection",
                "governance policy checks",
                "audit logging",
                "Purview publication boundary",
            ],
            "input_output_traceability": {
                "input_hash": input_hash,
                "output_hash": output_hash,
                "source_path": source.path,
                "agent_version": AGENT_VERSION,
            },
        }

        result = AgentRunResult(
            run_id=run_id,
            agent_version=AGENT_VERSION,
            source=asdict(source),
            input_hash=input_hash,
            output_hash=output_hash,
            quality_score=quality_score,
            quality_findings=[asdict(x) for x in quality_findings],
            anomaly_findings=[asdict(x) for x in anomalies],
            metadata=asdict(metadata),
            policy=asdict(decision),
            recommendations=recommendations,
            trace=trace,
        )
        payload = result.to_dict()
        self.audit_store.write(payload)
        self.purview.publish_governance_result(source.name, payload)
        return result
