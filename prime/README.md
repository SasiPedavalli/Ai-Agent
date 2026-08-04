# PRIME Genesis

**PRIME — Progressive Recursive Intelligence & Mutation Engine** is the self-evolving control plane for the PRIME product family.

PRIME improves bounded parts of an AI system—prompts, workflow policies, model routing, retrieval settings, thresholds, memory policies, and evaluation suites—through controlled experiments. It never promotes a candidate merely because it is new. A candidate must beat the active champion on measurable quality, reliability, safety, latency, and cost gates.

## Product family

- **Guardian X** — predictive reliability, security, cloud, data, AI, and cost intelligence.
- **Genome** — evolving behavioral and longitudinal risk signatures for finance and healthcare.
- **Company Brain** — evidence-linked organizational memory and reasoning.
- **Digital Twin** — simulation and counterfactual decision intelligence.

## Daily evolution cycle

```text
Observe → Diagnose → Mutate → Sandbox → Evaluate → Govern
       → Canary → Promote or Roll Back → Record Lineage → Learn
```

## Genesis capabilities

- Deterministic daily evolution engine
- Versioned agent specifications and mutation lineage
- SQLite experiment registry
- Multi-objective evaluation scorecard
- Safety and regression gates
- Automatic champion selection
- Rollback-ready promotion records
- Provider interface plus deterministic mock provider
- JSONL benchmark loader
- CLI, unit tests, CI, and a scheduled daily evolution workflow

## Run locally

```bash
cd prime
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
prime evolve --benchmark data/benchmarks.jsonl --db artifacts/prime.db
```

Run tests:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Safety boundary

Genesis evolves configuration and decision policies—not arbitrary production code. Every mutation is versioned, evaluated in isolation, and reversible. High-impact actions remain human-approved until later governance levels explicitly permit automation.
