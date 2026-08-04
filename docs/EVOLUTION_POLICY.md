# PRIME Evolution Policy

## Non-negotiable controls

1. PRIME does not rewrite arbitrary production code.
2. Every version has a parent, generation, reason, and immutable identifier.
3. Mutation generation cannot read the protected holdout.
4. A challenger must pass public benchmarks, protected holdout gates, and canary checks.
5. Safety cannot be traded for quality, latency, or cost.
6. A failed canary requires rollback to the previous champion.
7. Only aggregate, non-sensitive state may be committed to Git.
8. Private cases, customer inputs, and raw outputs remain isolated artifacts.
9. Real-model calls use explicit credentials and `store=False` where supported.
10. High-impact customer actions require human approval.
11. Daily evolution attempts improvement; it never guarantees that a better candidate exists.
12. A no-promotion run is a valid safety outcome.

## Daily operating cycle

- Load the persisted champion.
- Generate bounded configuration challengers.
- Evaluate the active champion and challengers on public cases.
- Evaluate public-gate winners on a separately supplied holdout.
- Run canary checks for holdout-gate winners.
- Promote the strongest fully passing challenger.
- Preserve or roll back to the existing champion on failure.
- Persist aggregate state and upload full evidence privately.
