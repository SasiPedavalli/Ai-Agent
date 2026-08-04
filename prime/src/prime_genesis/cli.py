from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from prime_genesis.audit import TenantAuditExporter
from prime_genesis.auth import issue_token, verify_token
from prime_genesis.backup import backup_sqlite
from prime_genesis.canary import CanaryPolicy
from prime_genesis.engine import evolve
from prime_genesis.improvement import FeedbackProposalBuilder
from prime_genesis.maintenance import RuntimeMaintenance
from prime_genesis.providers.mock import DeterministicProvider
from prime_genesis.readiness import evaluate_readiness
from prime_genesis.runtime import PrimeRuntime
from prime_genesis.security import TenantContext
from prime_genesis.state import read_status
from prime_products.base import ProductRequest

PRODUCTS = ("guardian-x", "genome", "company-brain", "digital-twin")


def _context(args: argparse.Namespace) -> TenantContext:
    return TenantContext(
        args.tenant,
        args.actor,
        frozenset(role.strip() for role in args.roles.split(",") if role.strip()),
    )


def _context_args(parser: argparse.ArgumentParser, default_roles: str = "reader") -> None:
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--roles", default=default_roles)
    parser.add_argument("--runtime-db", default="artifacts/runtime.db")


def _provider(name: str, model: str | None):
    if name == "mock":
        return DeterministicProvider()
    from prime_genesis.providers.openai_responses import OpenAIResponsesProvider

    return OpenAIResponsesProvider(model=model)


def _print(payload) -> None:
    print(json.dumps(payload, indent=2, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prime", description="PRIME 1.0 control plane")
    commands = parser.add_subparsers(dest="command", required=True)

    evolve_parser = commands.add_parser("evolve")
    evolve_parser.add_argument("--provider", choices=("mock", "openai"), default="mock")
    evolve_parser.add_argument("--model")
    evolve_parser.add_argument("--benchmark", default="data/benchmarks.jsonl")
    evolve_parser.add_argument("--holdout", default="data/holdout.calibration.jsonl")
    evolve_parser.add_argument("--db", default="artifacts/prime.db")
    evolve_parser.add_argument("--state", default="state/champion.json")
    evolve_parser.add_argument("--history", default="state/evolution-history.jsonl")
    evolve_parser.add_argument("--json-report", default="artifacts/latest-report.json")
    evolve_parser.add_argument("--max-rounds", type=int, default=2)
    evolve_parser.add_argument("--canary-traffic", type=float, default=0.1)

    status_parser = commands.add_parser("status")
    status_parser.add_argument("--state", default="state/champion.json")
    status_parser.add_argument("--history", default="state/evolution-history.jsonl")
    status_parser.add_argument(
        "--json",
        action="store_true",
        help="Compatibility flag; status output is JSON",
    )

    ready_parser = commands.add_parser("ready")
    ready_parser.add_argument("--state", default="state/champion.json")
    ready_parser.add_argument("--runtime-db", default="artifacts/runtime.db")

    for name in ("products", "models"):
        command = commands.add_parser(name)
        command.add_argument("--runtime-db", default="artifacts/runtime.db")

    command = commands.add_parser("run-product")
    command.add_argument("product", choices=PRODUCTS)
    command.add_argument("--text", required=True)
    command.add_argument("--namespace", default="default")
    command.add_argument("--sensitivity", default="standard")
    command.add_argument("--max-cost-usd", type=float)
    command.add_argument("--latency-target-ms", type=int)
    _context_args(command)

    for name, write in (("memory-add", True), ("memory-search", False)):
        command = commands.add_parser(name)
        command.add_argument("--namespace", default="default" if write else None)
        command.add_argument("--content" if write else "--query", required=True)
        if not write:
            command.add_argument("--limit", type=int, default=10)
        _context_args(command, "writer" if write else "reader")

    command = commands.add_parser("document-add")
    command.add_argument("--namespace", default="default")
    command.add_argument("--title", required=True)
    command.add_argument("--content", required=True)
    _context_args(command, "writer")

    command = commands.add_parser("document-search")
    command.add_argument("--query", required=True)
    command.add_argument("--namespace")
    command.add_argument("--limit", type=int, default=5)
    _context_args(command)

    command = commands.add_parser("budget-set")
    command.add_argument("--limit-usd", type=float, required=True)
    _context_args(command, "admin")
    _context_args(commands.add_parser("budget-status"))

    command = commands.add_parser("audit-export")
    command.add_argument("--destination", required=True)
    _context_args(command, "auditor")

    command = commands.add_parser("evaluation-proposals")
    command.add_argument("--maximum-rating", type=int, default=2)
    command.add_argument("--destination")
    _context_args(command, "evaluator")

    command = commands.add_parser("maintenance")
    command.add_argument("--runtime-event-days", type=int, default=30)
    command.add_argument("--feedback-days", type=int, default=365)
    _context_args(command, "admin")

    command = commands.add_parser("token-issue")
    command.add_argument("--tenant", required=True)
    command.add_argument("--actor", required=True)
    command.add_argument("--roles", default="reader")
    command.add_argument("--ttl", type=int, default=3600)

    command = commands.add_parser("token-verify")
    command.add_argument("--token", required=True)

    command = commands.add_parser("backup")
    command.add_argument("--source", default="artifacts/runtime.db")
    command.add_argument("--destination", required=True)

    command = commands.add_parser("serve")
    command.add_argument("--host", default="127.0.0.1")
    command.add_argument("--port", type=int, default=8080)
    return parser


def _run_evolution(args: argparse.Namespace) -> int:
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
    output = Path(args.json_report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    _print(report.to_dict())
    return 0


def _run_operator_command(args: argparse.Namespace) -> int | None:
    if args.command == "status":
        _print(read_status(args.state, args.history))
        return 0
    if args.command == "ready":
        report = evaluate_readiness(
            state_path=args.state,
            runtime_db_path=args.runtime_db,
        )
        _print(report.to_dict())
        return 0 if report.ready else 1
    if args.command == "token-issue":
        print(
            issue_token(
                os.getenv("PRIME_AUTH_SECRET", ""),
                _context(args),
                ttl_seconds=args.ttl,
            )
        )
        return 0
    if args.command == "token-verify":
        _print(asdict(verify_token(os.getenv("PRIME_AUTH_SECRET", ""), args.token)))
        return 0
    if args.command == "backup":
        _print(asdict(backup_sqlite(args.source, args.destination)))
        return 0
    if args.command == "audit-export":
        exporter = TenantAuditExporter(args.runtime_db)
        try:
            _print(asdict(exporter.export(_context(args), destination=args.destination)))
        finally:
            exporter.close()
        return 0
    if args.command == "evaluation-proposals":
        builder = FeedbackProposalBuilder(args.runtime_db)
        try:
            _print(
                [
                    asdict(item)
                    for item in builder.build(
                        _context(args),
                        maximum_rating=args.maximum_rating,
                        destination=args.destination,
                    )
                ]
            )
        finally:
            builder.close()
        return 0
    if args.command == "maintenance":
        manager = RuntimeMaintenance(args.runtime_db)
        try:
            _print(
                asdict(
                    manager.purge(
                        runtime_event_days=args.runtime_event_days,
                        feedback_days=args.feedback_days,
                    )
                )
            )
        finally:
            manager.close()
        return 0
    if args.command == "serve":
        import uvicorn

        uvicorn.run("prime_genesis.control_api:app", host=args.host, port=args.port)
        return 0
    return None


def _run_runtime_command(args: argparse.Namespace) -> int:
    runtime = PrimeRuntime(args.runtime_db)
    try:
        if args.command == "products":
            _print(runtime.list_products())
        elif args.command == "models":
            _print(runtime.list_models())
        elif args.command == "run-product":
            _print(
                runtime.run_product(
                    args.product,
                    _context(args),
                    ProductRequest(
                        args.text,
                        args.sensitivity,
                        args.namespace,
                        args.max_cost_usd,
                        args.latency_target_ms,
                    ),
                ).to_dict()
            )
        elif args.command == "memory-add":
            _print(
                asdict(
                    runtime.ingest_memory(
                        _context(args),
                        namespace=args.namespace,
                        content=args.content,
                    )
                )
            )
        elif args.command == "memory-search":
            _print(
                [
                    asdict(item)
                    for item in runtime.search_memory(
                        _context(args),
                        query=args.query,
                        namespace=args.namespace,
                        limit=args.limit,
                    )
                ]
            )
        elif args.command == "document-add":
            _print(
                asdict(
                    runtime.ingest_document(
                        _context(args),
                        namespace=args.namespace,
                        title=args.title,
                        content=args.content,
                    )
                )
            )
        elif args.command == "document-search":
            _print(
                [
                    {
                        "document": asdict(hit.document),
                        "score": hit.score,
                        "matched_terms": hit.matched_terms,
                    }
                    for hit in runtime.search_documents(
                        _context(args),
                        query=args.query,
                        namespace=args.namespace,
                        limit=args.limit,
                    )
                ]
            )
        elif args.command == "budget-set":
            runtime.budgets.set_daily_limit(_context(args), args.limit_usd)
            _print(asdict(runtime.budgets.authorize(_context(args), 0)))
        elif args.command == "budget-status":
            _print(asdict(runtime.budgets.authorize(_context(args), 0)))
        return 0
    finally:
        runtime.close()


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "evolve":
        return _run_evolution(args)
    operator_result = _run_operator_command(args)
    if operator_result is not None:
        return operator_result
    return _run_runtime_command(args)


if __name__ == "__main__":
    raise SystemExit(main())
