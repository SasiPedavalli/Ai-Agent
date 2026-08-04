# PRIME Evolution Policy

## Non-negotiable rules

1. No uncontrolled production self-modification.
2. Every mutation has a parent, reason, version, and evaluation record.
3. Evaluation data is separated from mutation generation.
4. A candidate cannot pass by improving one metric while violating a safety gate.
5. Every promotion is reversible.
6. High-impact actions require human approval.
7. Customer-specific data remains isolated by tenant and deployment policy.
8. Cost budgets and resource ceilings are enforced.
9. Regressions trigger rollback or automatic demotion.
10. Daily evolution produces evidence, not guaranteed improvement.

## Daily cadence

- Collect observations and failures
- Refresh non-protected training examples
- Diagnose weak capability clusters
- Generate bounded candidates
- Execute sandbox evaluations
- Compare against champion
- Promote only passing challengers
- Persist lineage and scorecards
- Monitor promoted versions
