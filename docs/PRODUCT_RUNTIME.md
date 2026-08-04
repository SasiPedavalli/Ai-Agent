# PRIME Product Runtime

PRIME v0.3 adds a tenant-scoped execution plane for Guardian X, Genome, Company Brain, and Digital Twin.

## Security context

Every memory and product operation receives a validated `TenantContext` with tenant, actor, and roles. Memory queries always include the tenant identifier. Writes require `writer` or `admin`.

The HTTP API accepts `X-Prime-Tenant`, `X-Prime-Actor`, and `X-Prime-Roles`. These are trusted context headers, not authentication. A production identity-aware gateway must validate the user and overwrite them.

## Products

- **Guardian X** detects evidence-supported reliability, security, data-quality, AI-quality, and cost signals. It does not remediate automatically.
- **Genome** builds finance or healthcare behavioral signatures. It does not diagnose patients or confirm fraud.
- **Company Brain** compares tenant memory and supplied records for explicit conflicts. It does not silently change policy.
- **Digital Twin** creates assumption-explicit sensitivity scenarios. It does not guarantee outcomes.

## Routing

The router selects `local-private` for regulated content, `fast` for strict cost or latency, `reasoning` for complex or counterfactual requests, and `balanced` otherwise. v0.3 records the route but does not yet bind each tier to a production model registry.

## Data boundary

SQLite provides a runnable local foundation. Production should use encrypted tenant storage such as PostgreSQL/pgvector. Customer content, runtime databases, and raw feedback must not be committed to Git.
