from __future__ import annotations

import argparse
import json
from pathlib import Path

from prime_genesis.engine import evolve
from prime_genesis.providers.mock import DeterministicProvider


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prime", description="PRIME Genesis control plane")
    subparsers = parser.add_subparsers(dest="command", required=True)

    evolve_parser = subparsers.add_parser("evolve", help="Run one governed evolution cycle")
    evolve_parser.add_argument("--benchmark", default="data/benchmarks.jsonl")
    evolve_parser.add_argument("--db", default="artifacts/prime.db")
    evolve_parser.add_argument("--json-report", default="artifacts/latest-report.json")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "evolve":
        report = evolve(
            provider=DeterministicProvider(),
            benchmark_path=args.benchmark,
            db_path=args.db,
        )
        output_path = Path(args.json_report)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        print(f"Run: {report.run_id}")
        print(f"Previous champion: {report.previous_champion}")
        print(f"Selected champion: {report.selected_champion}")
        print(f"Report: {output_path}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
