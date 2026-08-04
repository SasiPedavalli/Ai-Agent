# PRIME v0.2 — Governed Continuous Evolution

**PRIME — Progressive Recursive Intelligence & Mutation Engine** is the control plane for a family of intelligent products: Guardian X, Genome, Company Brain, and Digital Twin.

v0.2 turns the Genesis experiment into a cumulative daily evolution system. Each run resumes from the persisted champion, creates bounded configuration challengers, evaluates them on public benchmarks and a separate holdout, simulates a canary rollout, and either promotes the best safe candidate or preserves the current champion.

## Evolution path

```text
Persisted champion
    ↓
Bounded prompt / workflow / retrieval / routing mutations
    ↓
Public benchmark gate
    ↓
Protected holdout gate
    ↓
Canary simulation
    ↓
Promote or roll back
    ↓
Persist champion + report + Git history
```

## Capabilities

- Cumulative champion state across daily runs
- Immutable version lineage and generation numbers
- Prompt, workflow-policy, retrieval-policy, response-contract, and model-route mutations
- Public benchmark and separate holdout evaluation
- Multi-objective quality, safety, reliability, latency, and cost gates
- Canary promotion and rollback records
- SQLite experiment evidence plus Git-versioned non-sensitive state
- Optional OpenAI Responses API provider with `store=False`
- Optional FastAPI control plane and built-in dashboard
- CLI commands for evolution, status, and serving the control center
- Daily GitHub Actions evolution with optional secret-injected protected holdout

## Local use

```bash
cd prime
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
prime evolve
prime status
```

Real-model mode is optional:

```bash
pip install -e '.[openai]'
export OPENAI_API_KEY='...'
prime evolve --provider openai --model gpt-5
```

Control center:

```bash
pip install -e '.[api]'
prime serve --host 127.0.0.1 --port 8080
```

API-triggered evolution is disabled by default. Explicitly set `PRIME_API_EVOLUTION_ENABLED=true` only in a controlled environment.

## Protected evaluations

`data/holdout.calibration.jsonl` is public and is therefore only a calibration set. Production promotion should inject a private JSONL holdout through the `PRIME_HOLDOUT_JSONL_BASE64` GitHub secret. Mutation generation never receives that protected file.

## Safety boundary

PRIME evolves configuration and decision policy, not arbitrary production code. Every promoted version must pass benchmark, holdout, and canary gates. High-impact actions remain human-approved.
