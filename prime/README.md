# PRIME 1.0 — Deployable Governed AI MVP

**PRIME — Progressive Recursive Intelligence & Mutation Engine** is a deployable, model-agnostic AI platform that combines cumulative governed evolution with tenant-scoped products.

Products:
- **Guardian X** — reliability, security, data, AI, and cost intelligence
- **Genome** — longitudinal finance and healthcare risk-support signatures
- **Company Brain** — organizational memory, retrieval, and conflict detection
- **Digital Twin** — assumption-explicit counterfactual scenarios

## What 1.0 includes

- Daily champion evolution with public, protected-holdout, canary, promotion, and rollback gates
- Persistent version lineage and sanitized champion state
- Tenant/actor context and reader/writer/admin/auditor/evaluator authorization
- Tenant-isolated memory and document retrieval
- Private, fast, balanced, and reasoning model tiers with controlled failover
- Tenant budgets, usage accounting, signed tenant tokens, rate limits, and idempotency
- Runtime events, feedback, bounded tools, CLI, REST API, and dashboard
- Readiness diagnostics and `/ready`
- Tenant-scoped audit export with SHA-256 evidence digest
- Low-rating feedback converted into human-reviewed evaluation proposals
- Operational metadata retention maintenance
- Verifiable SQLite backups
- Non-root container, persistent volume, health check, Compose deployment, Python matrix CI, and container smoke CI

## Run

```bash
cd prime
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e '.[api]'
python -m unittest discover -s tests -v
prime ready
prime serve --host 127.0.0.1 --port 8080
```

Container deployment:

```bash
cp .env.example .env
# Replace PRIME_AUTH_SECRET with at least 32 random characters.
docker compose up --build
```

Operator examples:

```bash
prime audit-export --tenant acme --actor auditor --roles auditor \
  --runtime-db artifacts/runtime.db --destination artifacts/acme-audit.jsonl

prime evaluation-proposals --tenant acme --actor evaluator --roles evaluator \
  --runtime-db artifacts/runtime.db --destination artifacts/evaluation-proposals.jsonl

prime maintenance --tenant acme --actor admin --roles admin \
  --runtime-db artifacts/runtime.db --runtime-event-days 30 --feedback-days 365
```

## Definition of “complete” for this release

PRIME 1.0 is a **deployable MVP**, not a frontier foundation model and not yet an enterprise SaaS equivalent to ChatGPT, Claude, or Cursor. It provides the governed control plane, product runtime, security baseline, deployment path, evidence trail, and daily improvement loop required to build toward that scale honestly.

Public production should replace HMAC/SQLite with enterprise OIDC, TLS termination, centralized secrets, encrypted managed PostgreSQL/pgvector or equivalent storage, external monitoring, autoscaling, formal compliance controls, and customer-specific integrations.

## Safety

Genome does not diagnose or confirm fraud. Guardian X does not remediate automatically. Company Brain does not silently change policy. Digital Twin does not guarantee outcomes. Feedback proposals never enter benchmarks automatically. Arbitrary production source-code self-modification remains prohibited; code changes continue through reviewed pull requests.

See `docs/ARCHITECTURE.md`, `docs/EVOLUTION_POLICY.md`, `docs/PRODUCT_RUNTIME.md`, `docs/DEPLOYMENT.md`, and `docs/OPERATIONS.md`.
