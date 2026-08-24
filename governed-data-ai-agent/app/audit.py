from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict


class AuditStore:
    def __init__(self, path: str = "agent_audit.db") -> None:
        self.path = Path(path)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_runs (
                    run_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    agent_version TEXT NOT NULL,
                    environment TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    input_hash TEXT NOT NULL,
                    output_hash TEXT NOT NULL,
                    policy_decision TEXT NOT NULL,
                    quality_score REAL NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )

    def write(self, result: Dict) -> None:
        trace = result["trace"]
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO agent_runs
                (run_id, created_at, agent_version, environment, source_name,
                 input_hash, output_hash, policy_decision, quality_score, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result["run_id"],
                    trace["created_at"],
                    result["agent_version"],
                    result["source"]["environment"],
                    result["source"]["name"],
                    result["input_hash"],
                    result["output_hash"],
                    result["policy"]["decision"],
                    result["quality_score"],
                    json.dumps(result, sort_keys=True),
                ),
            )
