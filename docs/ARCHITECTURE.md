# PRIME v0.2 Architecture

```text
                      PRIME GOVERNED EVOLUTION CONTROL PLANE
┌───────────────────────────────────────────────────────────────────────────┐
│ Observe → Diagnose → Mutate → Public Eval → Protected Eval → Canary     │
│                    → Promote / Roll Back → Persist → Audit               │
└───────────────────────────────────────────────────────────────────────────┘
       │               │                 │                 │
 Version Registry  Evaluation Lab   Governance Gates  State + Lineage
       │               │                 │                 │
       └───────────────┴─────────────────┴─────────────────┘
                               │
       ┌───────────────────────┼───────────────────────────┐
       │                       │                           │
   Guardian X                Genome                  Company Brain
       │                       │                           │
       └───────────────────────┼───────────────────────────┘
                               │
                         Digital Twin
```

## Runtime components

- `models.py` — immutable versions, scorecards, decisions, canaries, and reports
- `state.py` — Git-versioned aggregate champion state and history
- `store.py` — SQLite evidence store with legacy-schema migration
- `mutations.py` — bounded prompt, workflow, retrieval, response, and routing mutations
- `evaluation.py` — multi-objective public and holdout evaluation
- `governance.py` — promotion gates
- `canary.py` — canary simulation and rollback decision
- `engine.py` — cumulative multi-round evolution orchestration
- `providers/mock.py` — deterministic offline provider
- `providers/openai_responses.py` — optional OpenAI Responses API adapter
- `control_api.py` — optional FastAPI control plane and dashboard
- `cli.py` — evolve, status, and serve commands

## Persistence model

- `state/champion.json` contains only active configuration and aggregate metrics.
- `state/evolution-history.jsonl` contains non-sensitive run summaries.
- Full outputs, private holdout results, and SQLite evidence are workflow artifacts and are not committed.

## Trust boundary

The mutation engine changes bounded configuration only. Source-code changes continue through human-reviewed pull requests. API-triggered evolution is disabled unless explicitly enabled by an operator.
