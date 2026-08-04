from __future__ import annotations

import uuid
from pathlib import Path

from prime_genesis.benchmarks import load_cases
from prime_genesis.evaluation import evaluate
from prime_genesis.governance import decide
from prime_genesis.models import AgentVersion, EvolutionReport, utc_now
from prime_genesis.mutations import propose_mutations
from prime_genesis.providers.base import AgentProvider
from prime_genesis.store import ExperimentStore


DEFAULT_CHAMPION = AgentVersion(
    version_id="prime-genesis-v0",
    prompt=(
        "Analyze the supplied operational case. Identify only findings supported by the input. "
        "Never invent systems, people, events, or evidence."
    ),
    parent_version_id=None,
    mutation_type="genesis",
    mutation_reason="Initial governed champion.",
)


def evolve(
    provider: AgentProvider,
    benchmark_path: str | Path,
    db_path: str | Path,
    champion: AgentVersion = DEFAULT_CHAMPION,
) -> EvolutionReport:
    started_at = utc_now()
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    cases = load_cases(benchmark_path)
    store = ExperimentStore(db_path)

    try:
        store.save_version(champion)
        active_version = champion
        active_score = evaluate(provider, active_version, cases)
        store.save_scorecard(run_id, active_score)

        scorecards = [active_score]
        decisions = []

        for candidate in propose_mutations(champion):
            store.save_version(candidate)
            candidate_score = evaluate(provider, candidate, cases)
            store.save_scorecard(run_id, candidate_score)
            decision = decide(active_score, candidate_score)
            store.save_decision(run_id, decision)

            scorecards.append(candidate_score)
            decisions.append(decision)
            if decision.approved:
                active_version = candidate
                active_score = candidate_score

        report = EvolutionReport(
            run_id=run_id,
            started_at=started_at,
            completed_at=utc_now(),
            previous_champion=champion.version_id,
            selected_champion=active_version.version_id,
            scorecards=tuple(scorecards),
            decisions=tuple(decisions),
        )
        store.save_report(report)
        return report
    finally:
        store.close()
