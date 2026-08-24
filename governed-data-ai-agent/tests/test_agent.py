import json
import tempfile
import unittest
from pathlib import Path

from app.agent import GovernedDataAIAgent
from app.audit import AuditStore
from app.models import DataSource
from app.purview import MockPurviewGateway


ROOT = Path(__file__).resolve().parents[1]


class AgentTests(unittest.TestCase):
    def test_approved_governed_asset_can_be_evaluated(self):
        policy = json.loads((ROOT / "config/governance_policy.json").read_text())
        rules = json.loads((ROOT / "config/data_quality_rules.json").read_text())
        with tempfile.TemporaryDirectory() as td:
            agent = GovernedDataAIAgent(
                policy=policy,
                audit_store=AuditStore(str(Path(td) / "audit.db")),
                purview_gateway=MockPurviewGateway(str(Path(td) / "purview.jsonl")),
            )
            source = DataSource(
                name="customer_events",
                path=str(ROOT / "data/sample_customer_events.csv"),
                owner="platform-owner@company.com",
                domain="customer-telemetry",
                environment="test",
                approved=True,
                lineage_registered=True,
            )
            result = agent.run(source, rules)
            self.assertEqual(result.policy["decision"], "ALLOW")
            self.assertIn("email", result.metadata["classifications"])
            self.assertEqual(result.metadata["sensitivity"], "confidential")
            self.assertTrue(result.input_hash)
            self.assertTrue(result.output_hash)

    def test_unapproved_source_is_blocked(self):
        policy = json.loads((ROOT / "config/governance_policy.json").read_text())
        rules = json.loads((ROOT / "config/data_quality_rules.json").read_text())
        with tempfile.TemporaryDirectory() as td:
            agent = GovernedDataAIAgent(
                policy=policy,
                audit_store=AuditStore(str(Path(td) / "audit.db")),
                purview_gateway=MockPurviewGateway(str(Path(td) / "purview.jsonl")),
            )
            source = DataSource(
                name="customer_events",
                path=str(ROOT / "data/sample_customer_events.csv"),
                owner="platform-owner@company.com",
                domain="customer-telemetry",
                environment="prod",
                approved=False,
                lineage_registered=True,
            )
            result = agent.run(source, rules)
            self.assertEqual(result.policy["decision"], "BLOCK")
            self.assertIn("approved_governed_source", result.policy["reasons"])


if __name__ == "__main__":
    unittest.main()
