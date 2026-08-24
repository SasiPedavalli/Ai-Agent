from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agent import GovernedDataAIAgent
from .audit import AuditStore
from .models import DataSource


def load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Governed Data & AI Operations Agent")
    parser.add_argument("--source", default="data/sample_customer_events.csv")
    parser.add_argument("--rules", default="config/data_quality_rules.json")
    parser.add_argument("--policy", default="config/governance_policy.json")
    parser.add_argument("--environment", default="dev", choices=["dev", "test", "prod"])
    parser.add_argument("--approved", action="store_true")
    parser.add_argument("--lineage-registered", action="store_true")
    parser.add_argument("--owner", default="data-platform@company.com")
    parser.add_argument("--domain", default="customer-telemetry")
    parser.add_argument("--asset-name", default="customer_events")
    parser.add_argument("--output", default="agent_result.json")
    parser.add_argument(
        "--promotion-gate",
        action="store_true",
        help="Return non-zero when governance policy blocks deployment; designed for CI/CD.",
    )
    args = parser.parse_args()

    source = DataSource(
        name=args.asset_name,
        path=args.source,
        owner=args.owner,
        domain=args.domain,
        environment=args.environment,
        approved=args.approved,
        lineage_registered=args.lineage_registered,
    )

    agent = GovernedDataAIAgent(
        policy=load_json(args.policy),
        audit_store=AuditStore("agent_audit.db"),
    )
    result = agent.run(source, load_json(args.rules))
    payload = result.to_dict()
    Path(args.output).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(json.dumps({
        "run_id": result.run_id,
        "quality_score": result.quality_score,
        "policy_decision": result.policy["decision"],
        "policy_failures": result.policy["reasons"],
        "classifications": result.metadata["classifications"],
        "anomalies": len(result.anomaly_findings),
        "output": args.output,
    }, indent=2))

    if args.promotion_gate and result.policy["decision"] != "ALLOW":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
