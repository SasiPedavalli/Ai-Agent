# PRIME v0.5 — Deployable Governed AI Platform

**PRIME — Progressive Recursive Intelligence & Mutation Engine** combines cumulative governed evolution with a tenant-scoped AI product platform.

Products:
- **Guardian X** — reliability, security, data, AI, and cost intelligence
- **Genome** — longitudinal finance and healthcare risk-support signatures
- **Company Brain** — organizational memory, retrieval, and conflict detection
- **Digital Twin** — assumption-explicit counterfactual scenarios

## Platform capabilities

- Daily champion evolution with public, holdout, canary, promotion, and rollback gates
- Tenant/actor context and reader/writer/admin authorization
- Tenant-isolated memory and document retrieval
- Private, fast, balanced, and reasoning model tiers with controlled failover
- Tenant model budgets and usage accounting
- Signed tenant tokens, actor/operation rate limits, and idempotent product runs
- Runtime events, feedback, bounded tools, CLI, REST API, and dashboard
- Verifiable SQLite backups
- Non-root container, persistent volume, health check, Compose deployment, and container CI

## Run from source

```bash
cd prime
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e '.[api]'
python -m unittest discover -s tests -v
prime evolve
prime products
prime models
prime serve --host 127.0.0.1 --port 8080
```

## Run with Docker

```bash
cd prime
cp .env.example .env
# Replace PRIME_AUTH_SECRET with at least 32 random characters.
docker compose up --build
```

The container enables HMAC Bearer authentication, runs as a non-root user, persists data in `prime_data`, and exposes `/health`.

Create a temporary tenant token:

```bash
export PRIME_AUTH_SECRET='replace-with-at-least-32-random-characters'
prime token-issue --tenant acme --actor admin --roles admin,reader,writer --ttl 3600
```

Product calls accept `Idempotency-Key`. Rate limits are scoped by tenant, actor, and operation. Tenant budgets are checked before model execution.

## Important production boundary

HMAC tokens and SQLite make PRIME runnable as a single-node deployment. They are not the final enterprise architecture. Internet-facing deployments should use an identity-aware gateway with OIDC, encrypted managed PostgreSQL/pgvector or equivalent tenant storage, centralized secrets, TLS, backup retention, audit export, and external monitoring.

No customer data, private holdouts, API keys, HMAC secrets, raw outputs, or runtime databases should be committed to Git.

## Safety

Genome does not diagnose or confirm fraud. Guardian X does not remediate automatically. Company Brain does not silently change policy. Digital Twin does not guarantee outcomes. Arbitrary production source-code self-modification remains prohibited; code changes continue through reviewed pull requests.

See `docs/ARCHITECTURE.md`, `docs/EVOLUTION_POLICY.md`, `docs/PRODUCT_RUNTIME.md`, and `docs/DEPLOYMENT.md`.
