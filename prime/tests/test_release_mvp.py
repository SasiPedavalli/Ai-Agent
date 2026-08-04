from __future__ import annotations

import json
import os
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from prime_genesis.audit import TenantAuditExporter
from prime_genesis.improvement import FeedbackProposalBuilder
from prime_genesis.maintenance import RuntimeMaintenance
from prime_genesis.readiness import evaluate_readiness
from prime_genesis.runtime import PrimeRuntime
from prime_genesis.security import TenantContext
from prime_products.base import ProductRequest


class ReleaseMvpTests(unittest.TestCase):
    def test_readiness_reports_valid_state_database_auth_and_models(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = root / "champion.json"
            state.write_text(
                json.dumps(
                    {
                        "champion": {
                            "version_id": "prime-test",
                            "generation": 3,
                        }
                    }
                ),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {"PRIME_AUTH_MODE": "hmac", "PRIME_AUTH_SECRET": "x" * 32},
                clear=False,
            ):
                report = evaluate_readiness(
                    state_path=state,
                    runtime_db_path=root / "runtime.db",
                )
            self.assertTrue(report.ready)
            self.assertTrue(all(check.passed for check in report.checks))

    def test_audit_export_is_tenant_scoped_and_hashed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Path(temp_dir) / "runtime.db"
            runtime = PrimeRuntime(db)
            alpha = TenantContext("alpha", "admin", frozenset({"admin", "reader"}))
            beta = TenantContext("beta", "admin", frozenset({"admin", "reader"}))
            try:
                alpha_result = runtime.run_product(
                    "guardian-x", alpha, ProductRequest(text="pipeline latency breached the SLA")
                )
                runtime.record_feedback(
                    alpha,
                    product="guardian-x",
                    run_id=alpha_result.run_id,
                    rating=2,
                    comment="Dependency evidence was missing.",
                )
                runtime.run_product(
                    "guardian-x", beta, ProductRequest(text="warehouse cost increased")
                )
            finally:
                runtime.close()

            exporter = TenantAuditExporter(db)
            try:
                exported = exporter.export(alpha, destination=Path(temp_dir) / "alpha.jsonl")
            finally:
                exporter.close()
            self.assertGreater(exported.record_count, 0)
            self.assertEqual(len(exported.sha256), 64)
            self.assertTrue(all(record.get("tenant_id") is None for record in exported.records))
            body = Path(exported.destination).read_text(encoding="utf-8")
            self.assertNotIn("beta", body)

    def test_low_feedback_creates_review_proposal_only_for_tenant(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Path(temp_dir) / "runtime.db"
            runtime = PrimeRuntime(db)
            alpha = TenantContext("alpha", "admin", frozenset({"admin"}))
            beta = TenantContext("beta", "admin", frozenset({"admin"}))
            try:
                runtime.record_feedback(
                    alpha,
                    product="company-brain",
                    run_id="run-a",
                    rating=1,
                    comment="Conflict source dates were not explained.",
                    metadata={
                        "failure_class": "evidence-ordering",
                        "expected_behavior": "Explain the authority and date of each source.",
                    },
                )
                runtime.record_feedback(
                    beta,
                    product="company-brain",
                    run_id="run-b",
                    rating=1,
                    comment="Beta-only feedback.",
                )
            finally:
                runtime.close()
            builder = FeedbackProposalBuilder(db)
            try:
                proposals = builder.build(alpha)
            finally:
                builder.close()
            self.assertEqual(len(proposals), 1)
            self.assertEqual(proposals[0].failure_class, "evidence-ordering")
            self.assertNotIn("Beta", proposals[0].issue_summary)

    def test_maintenance_purges_expired_operational_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Path(temp_dir) / "runtime.db"
            runtime = PrimeRuntime(db)
            context = TenantContext("acme", "operator")
            try:
                runtime.idempotency.put(
                    context,
                    operation="product",
                    key="expired",
                    response={"ok": True},
                    ttl_seconds=1,
                    now=100,
                )
                runtime.rate_limits.consume(
                    context,
                    operation="product",
                    limit=2,
                    window_seconds=60,
                    now=60,
                )
            finally:
                runtime.close()
            maintenance = RuntimeMaintenance(db)
            try:
                result = maintenance.purge(now_epoch=200000)
            finally:
                maintenance.close()
            payload = asdict(result)
            self.assertEqual(payload["idempotency_deleted"], 1)
            self.assertEqual(payload["rate_limit_windows_deleted"], 1)


if __name__ == "__main__":
    unittest.main()
