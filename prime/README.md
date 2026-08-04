# PRIME v0.4 — Governed Evolution + Tenant AI Platform

**PRIME — Progressive Recursive Intelligence & Mutation Engine** now combines cumulative governed evolution with a tenant-scoped product platform.

Products:
- **Guardian X** — reliability, security, data, AI, and cost intelligence
- **Genome** — longitudinal finance and healthcare risk-support signatures
- **Company Brain** — organizational memory, retrieval, and conflict detection
- **Digital Twin** — assumption-explicit counterfactual scenarios

## v0.4 platform capabilities

- Persistent daily champion evolution with public, holdout, and canary gates
- Tenant/actor context and reader/writer/admin enforcement
- Tenant-isolated memory and document retrieval
- Model registry with private, fast, balanced, and reasoning tiers
- Tier failover and optional environment-configured model aliases
- Tenant daily model budgets and usage ledger
- Bounded tools, runtime events, feedback, CLI, REST API, and dashboard
- Customer content, private holdouts, raw outputs, and runtime databases excluded from Git

## Run

```bash
cd prime
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
python -m unittest discover -s tests -v

prime evolve
prime products
prime models
```

Product example:

```bash
prime run-product guardian-x --tenant acme --actor analyst --roles reader \
  --text "Kafka consumer lag caused pipeline latency to breach the SLA." --json
```

Retrieval and budget examples:

```bash
prime document-add --tenant acme --actor editor --roles writer \
  --namespace architecture --title Runbook \
  --content "The service listens on port 8080."

prime document-search --tenant acme --actor analyst --roles reader \
  --namespace architecture --query "service port"

prime budget-set --tenant acme --actor admin --roles admin --limit-usd 10
```

Optional real-model aliases are configured with `PRIME_FAST_MODEL`, `PRIME_BALANCED_MODEL`, and `PRIME_REASONING_MODEL`. The built-in deterministic models keep the platform runnable without paid APIs. Pricing is never assumed; optional per-million-token cost environment variables drive estimates.

The HTTP API expects `X-Prime-Tenant`, `X-Prime-Actor`, and `X-Prime-Roles` from a trusted identity-aware gateway. PRIME does not authenticate these headers itself. API-triggered evolution remains disabled unless explicitly enabled.

## Safety

Genome does not diagnose or confirm fraud. Guardian X does not remediate automatically. Company Brain does not silently change policy. Digital Twin does not guarantee outcomes. Arbitrary production source-code self-modification remains prohibited.

See `docs/ARCHITECTURE.md`, `docs/EVOLUTION_POLICY.md`, and `docs/PRODUCT_RUNTIME.md`.
