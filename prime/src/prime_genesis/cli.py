from __future__ import annotations

import argparse
import json
from pathlib import Path

from prime_genesis.canary import CanaryPolicy
from prime_genesis.engine import evolve
from prime_genesis.providers.mock import DeterministicProvider
from prime_genesis.state import read_status


def _provider(name: str, model: str | None):
    if name == "mock":
        return DeterministicProvider()
    if name == "openai":
        from prime_genesis.providers.openai_responses import OpenAIResponsesProvider

        return OpenAIResponsesProvider(model=model)
    raise ValueError(f"Unsupported provider: {name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prime", description="PRIME evolution control plane")
    subparsers = parser.add_subparsers(dest="command", required=True)

    evolve_parser = subparsers.add_parser("evolve", help="Run one governed evolution cycle")
    evolve_parser.add_argument("--provider", choices=("mock", "openai"), default="mock")
    evolve_parser.add_argument("--model", default=None)
    evolve_parser.add_argument("--benchmark", default="data/benchmarks.jsonl")
    evolve_parser.add_argument("--holdout", default="data/holdout.calibration.jsonl")
    evolve_parser.add_argument("--db", default="artifacts/prime.db")
    evolve_parser.add_argument("--state", default="state/champion.json")
    evolve_parser.add_argument("--history", default="state/evolution-history.jsonl")
    evolve_parser.add_argument("--json-report", default="artifacts/latest-report.json")
    evolve_parser.add_argument("--max-rounds", type=int, default=2)
    evolve_parser.add_argument("--canary-traffic", type=float, default=0.10)

    status_parser = subparsers.add_parser("status", help="Show the active PRIME champion")
    status_parser.add_argument("--state", default="state/champion.json")
    status_parser.add_argument("--history", default="state/evolution-history.jsonl")
    status_parser.add_argument("--json", action="store_true")

    serve_parser = subparsers.add_parser("serve", help="Start the PRIME control API")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8080)
    return parser


def _write_report(path: str | Path, payload: dict) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output_path


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "evolve":
        report = evolve(
            provider=_provider(args.provider, args.model),
            benchmark_path=args.benchmark,
            holdout_path=args.holdout,
            db_path=args.db,
            state_path=args.state,
            history_path=args.history,
            max_mutation_rounds=args.max_rounds,
            canary_policy=CanaryPolicy(traffic_fraction=args.canary_traffic),
        )
        output_path = _write_report(args.json_report, report.to_dict())
        print(f"Run: {report.run_id}")
        print(f"Provider: {report.provider_name}")
        print(f"Previous champion: {report.previous_champion}")
        print(f"Selected champion: {report.selected_champion}")
        print(f"Promoted: {report.promoted}")
        print(f"Rollback performed: {report.rollback_performed}")
        print(f"Report: {output_path}")
        return 0

    if args.command == "status":
        status = read_status(args.state, args.history)
        if args.json:
            print(json.dumps(status, indent=2))
        elif not status["initialized"]:
            print("PRIME has not completed an evolution run yet.")
        else:
            champion = status["champion"]
            latest = status["latest_run"]
            print(f"Champion: {champion['version_id']}")
            print(f"Generation: {champion['generation']}")
            print(f"Latest run: {latest['run_id']}")
            print(f"History entries: {status['history_count']}")
        return 0

    if args.command == "serve":
        try:
            import uvicorn
        except ImportError as exc:
            raise RuntimeError("Install the API extra: pip install -e '.[api]'") from exc
        uvicorn.run("prime_genesis.control_api:app", host=args.host, port=args.port, reload=False)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
