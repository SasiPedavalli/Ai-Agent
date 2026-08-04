# PRIME 1.0 Operations

## Service checks

- `/health` confirms the process is running.
- `/ready` validates champion state, writable runtime storage, authentication configuration, and all required model tiers.
- A failed readiness response returns HTTP 503 and should remove the instance from traffic.

## Audit evidence

Tenant auditors and administrators can export runtime events, feedback, and model-usage records. Exports are tenant scoped and receive a SHA-256 digest. Memory and document contents are deliberately excluded from the operational audit export.

## Improvement proposals

Low-rating feedback can generate evaluation proposals containing an issue summary, expected behavior, and failure class. Proposals remain separate artifacts. A human evaluator must review, redact, label, and approve a case before it can enter a benchmark or protected holdout.

## Retention

The maintenance command purges old runtime events, old feedback, expired idempotency entries, and stale rate-limit windows. It never deletes tenant memory or documents. Customer-content retention requires a separate customer-approved policy.

## Backup and recovery

1. Stop writes or use a database-native consistent snapshot.
2. Run `prime backup` for the single-node SQLite baseline.
3. Store the backup and SHA-256 digest in encrypted, access-controlled storage.
4. Test restoration periodically.
5. Managed production storage should use automated point-in-time recovery.

## Incident response

- Revoke or rotate `PRIME_AUTH_SECRET` if token signing is compromised.
- Disable API-triggered evolution during an incident.
- Preserve audit and evolution artifacts.
- Roll back the active champion only through the governed lineage record.
- Do not place credentials, customer prompts, or protected evaluations in issue comments or Git commits.

## 1.0 limitations

PRIME 1.0 is a single-node deployable MVP. Horizontal scaling, enterprise OIDC, managed vector search, distributed queues, formal compliance certification, production SLO monitoring, billing, and customer connectors remain deployment-specific work.
