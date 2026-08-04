# PRIME Genesis Architecture

```text
                              PRIME CONTROL PLANE
┌────────────────────────────────────────────────────────────────────┐
│ Observe │ Diagnose │ Mutate │ Sandbox │ Evaluate │ Govern │ Learn │
└────────────────────────────────────────────────────────────────────┘
          │             │              │              │
   Version Registry  Benchmark Lab  Policy Gates  Lineage Store
          │             │              │              │
          └─────────────┴──────────────┴──────────────┘
                                │
       ┌────────────────────────┼─────────────────────────┐
       │                        │                         │
  Guardian X                 Genome                Company Brain
       │                        │                         │
       └────────────────────────┼─────────────────────────┘
                                │
                         AI Digital Twin
```

## Genesis components

- `models.py`: immutable evolution records
- `mutations.py`: bounded mutation candidates
- `evaluation.py`: quality, safety, reliability, latency, and cost scoring
- `governance.py`: promotion and regression gates
- `store.py`: SQLite experiment lineage and champion state
- `engine.py`: orchestrated evolution cycle
- `providers/`: model-provider abstraction
- `cli.py`: repeatable local and automated execution

## Next architecture increments

- OpenAI provider adapter with structured outputs
- Protected holdout benchmark service
- Workflow graph mutations
- Model router with quality/cost optimization
- Canary traffic simulator
- Rollback controller
- Event bus and observability pipeline
- Web control center
