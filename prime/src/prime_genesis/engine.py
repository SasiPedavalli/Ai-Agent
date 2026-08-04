from __future__ import annotations

import uuid
from pathlib import Path

from prime_genesis.benchmarks import load_cases
from prime_genesis.canary import CanaryPolicy, simulate_canary
from prime_genesis.evaluation import evaluate
from prime_genesis.governance import GovernancePolicy, decide
from prime_genesis.models import AgentVersion, EvolutionReport, Scorecard, utc_now
from prime_genesis.mutations import propose_mutations
from prime_genesis.providers.base import AgentProvider
from prime_genesis.state import append_history, load_champion_state, save_champion_state
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


def _find_scorecard(scorecards: list[Scorecard], version_id: str, split: str) -> Scorecard:
    for scorecard in reversed(scorecards):
        if scorecard.version_id == version_id and scorecard.split == split:
            return scorecard
    raise LookupError(f"Missing {split} scorecard for {version_id}")


def evolve(
    provider: AgentProvider,
    benchmark_path: str | Path,
    db_path: str | Path,
    *,
    holdout_path: str | Path | None = None,
    state_path: str | Path | None = None,
    history_path: str | Path | None = None,
    champion: AgentVersion | None = None,
    governance_policy: GovernancePolicy = GovernancePolicy(),
    canary_policy: CanaryPolicy = CanaryPolicy(),
    max_mutation_rounds: int = 2,
) -> EvolutionReport:
    started_at = utc_now()
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    public_cases = load_cases(benchmark_path)
    holdout_cases = load_cases(holdout_path) if holdout_path else public_cases
    store = ExperimentStore(db_path)

    try:
        persisted = load_champion_state(state_path) or store.load_champion()
        initial_champion = champion or persisted or DEFAULT_CHAMPION
        active_version = initial_champion
        store.save_version(active_version)

        scorecards: list[Scorecard] = []
        decisions = []
        canaries = []
        rollback_performed = False

        active_public = evaluate(provider, active_version, public_cases, split="public")
        active_holdout = evaluate(provider, active_version, holdout_cases, split="holdout")
        for scorecard in (active_public, active_holdout):
            store.save_scorecard(run_id, scorecard)
            scorecards.append(scorecard)

        for _ in range(max(1, max_mutation_rounds)):
            approved_candidates: list[tuple[AgentVersion, Scorecard, Scorecard]] = []
            for candidate in propose_mutations(active_version):
                store.save_version(candidate)
                candidate_public = evaluate(provider, candidate, public_cases, split="public")
                store.save_scorecard(run_id, candidate_public)
                scorecards.append(candidate_public)

                public_decision = decide(
                    active_public,
                    candidate_public,
                    policy=governance_policy,
                    stage="public-benchmark",
                )
                store.save_decision(run_id, public_decision)
                decisions.append(public_decision)
                if not public_decision.approved:
                    continue

                candidate_holdout = evaluate(provider, candidate, holdout_cases, split="holdout")
                store.save_scorecard(run_id, candidate_holdout)
                scorecards.append(candidate_holdout)
                holdout_decision = decide(
                    active_holdout,
                    candidate_holdout,
                    policy=governance_policy,
                    stage="protected-holdout",
                )
                store.save_decision(run_id, holdout_decision)
                decisions.append(holdout_decision)
                if not holdout_decision.approved:
                    continue

                canary = simulate_canary(active_holdout, candidate_holdout, policy=canary_policy)
                store.save_canary(run_id, canary)
                canaries.append(canary)
                if not canary.passed:
                    rollback_performed = True
                    continue
                approved_candidates.append((candidate, candidate_public, candidate_holdout))

            if not approved_candidates:
                break

            candidate, public_score, holdout_score = max(
                approved_candidates,
                key=lambda item: (item[2].composite, item[1].composite),
            )
            active_version = candidate
            active_public = public_score
            active_holdout = holdout_score

        promoted = active_version.version_id != initial_champion.version_id
        report = EvolutionReport(
            run_id=run_id,
            started_at=started_at,
            completed_at=utc_now(),
            previous_champion=initial_champion.version_id,
            selected_champion=active_version.version_id,
            promoted=promoted,
            rollback_performed=rollback_performed,
            provider_name=getattr(provider, "name", provider.__class__.__name__),
            scorecards=tuple(scorecards),
            decisions=tuple(decisions),
            canaries=tuple(canaries),
        )
        store.save_report(report, active_version)

        if state_path is not None:
            save_champion_state(
                state_path,
                champion=active_version,
                report=report,
                scorecard=_find_scorecard(scorecards, active_version.version_id, "holdout"),
            )
        if history_path is not None:
            append_history(history_path, report)
        return report
    finally:
        store.close()
