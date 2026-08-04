# PRIME Deployment

## Local container

```bash
cd prime
cp .env.example .env
# Replace PRIME_AUTH_SECRET with at least 32 random characters.
docker compose up --build
```

The container runs as a non-root user, stores SQLite state in the `prime_data` volume, and exposes `/health`.

## Authentication

- `PRIME_AUTH_MODE=local` accepts explicit tenant/actor headers and is for local development only.
- `PRIME_AUTH_MODE=hmac` requires a signed Bearer token created with `prime token-issue`; this is the container default.

HMAC tokens are a deployable baseline, not a substitute for enterprise OIDC. Internet-facing production should use an identity-aware gateway and external identity provider.

## Operations

- `PRIME_RATE_LIMIT_PER_MINUTE` applies per tenant, actor, and operation.
- Product runs accept `Idempotency-Key`, preventing repeat work and duplicate usage accounting.
- Tenant daily budgets are enforced before execution.
- `prime backup --source /data/runtime.db --destination /backup/runtime.db` creates a hashed backup.
- Encrypt and access-control `/data`. SQLite is single-node; use managed PostgreSQL for horizontal scale.

Never commit `.env`, HMAC secrets, API keys, private holdouts, runtime databases, or customer content. Secret rotation invalidates existing HMAC tokens.
