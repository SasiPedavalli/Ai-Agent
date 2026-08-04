# PRIME State

This directory contains versioned, non-secret evolution state produced by the governed daily workflow:

- `champion.json` — active champion configuration and aggregate scorecard
- `evolution-history.jsonl` — one non-sensitive summary per run

Full reports, case outputs, the SQLite evidence database, and private holdouts remain workflow artifacts and are never committed. Do not store customer prompts, credentials, raw production telemetry, or protected holdout data here.
