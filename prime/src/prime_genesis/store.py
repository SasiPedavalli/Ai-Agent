from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from prime_genesis.models import (
    AgentVersion,
    CanaryResult,
    EvolutionReport,
    PromotionDecision,
    Scorecard,
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS versions (
    version_id TEXT PRIMARY KEY,
    parent_version_id TEXT,
    mutation_type TEXT NOT NULL,
    mutation_reason TEXT NOT NULL,
    prompt TEXT NOT NULL,
    created_at TEXT NOT NULL,
    payload_json TEXT
);
CREATE TABLE IF NOT EXISTS scorecards (
    run_id TEXT NOT NULL,
    version_id TEXT NOT NULL,
    split TEXT NOT NULL DEFAULT 'public',
    payload_json TEXT NOT NULL,
    PRIMARY KEY (run_id, version_id, split)
);
CREATE TABLE IF NOT EXISTS decisions (
    run_id TEXT NOT NULL,
    challenger_version_id TEXT NOT NULL,
    stage TEXT NOT NULL DEFAULT 'benchmark',
    payload_json TEXT NOT NULL,
    PRIMARY KEY (run_id, challenger_version_id, stage)
);
CREATE TABLE IF NOT EXISTS canaries (
    run_id TEXT NOT NULL,
    challenger_version_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (run_id, challenger_version_id)
);
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    previous_champion TEXT NOT NULL,
    selected_champion TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class ExperimentStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)
        self._migrate_legacy_schema()

    def _columns(self, table: str) -> set[str]:
        return {row["name"] for row in self.connection.execute(f"PRAGMA table_info({table})")}

    def _migrate_legacy_schema(self) -> None:
        migrations = {
            "versions": [("payload_json", "TEXT")],
            "scorecards": [("split", "TEXT NOT NULL DEFAULT 'public'")],
            "decisions": [("stage", "TEXT NOT NULL DEFAULT 'benchmark'")],
        }
        for table, columns in migrations.items():
            existing = self._columns(table)
            for name, definition in columns:
                if name not in existing:
                    self.connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS canaries (
                run_id TEXT NOT NULL,
                challenger_version_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                PRIMARY KEY (run_id, challenger_version_id)
            )"""
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def save_version(self, version: AgentVersion) -> None:
        self.connection.execute(
            """INSERT OR REPLACE INTO versions
            (version_id, parent_version_id, mutation_type, mutation_reason, prompt, created_at, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                version.version_id,
                version.parent_version_id,
                version.mutation_type,
                version.mutation_reason,
                version.prompt,
                version.created_at,
                json.dumps(version.to_dict()),
            ),
        )
        self.connection.commit()

    def load_champion(self) -> AgentVersion | None:
        row = self.connection.execute("SELECT value FROM state WHERE key='champion_payload_json'").fetchone()
        if row is None:
            return None
        return AgentVersion.from_dict(json.loads(row["value"]))

    def save_scorecard(self, run_id: str, scorecard: Scorecard) -> None:
        self.connection.execute(
            """INSERT OR REPLACE INTO scorecards (run_id, version_id, split, payload_json)
            VALUES (?, ?, ?, ?)""",
            (run_id, scorecard.version_id, scorecard.split, json.dumps(asdict(scorecard))),
        )
        self.connection.commit()

    def save_decision(self, run_id: str, decision: PromotionDecision) -> None:
        self.connection.execute(
            """INSERT OR REPLACE INTO decisions
            (run_id, challenger_version_id, stage, payload_json) VALUES (?, ?, ?, ?)""",
            (run_id, decision.challenger_version_id, decision.stage, json.dumps(asdict(decision))),
        )
        self.connection.commit()

    def save_canary(self, run_id: str, canary: CanaryResult) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO canaries VALUES (?, ?, ?)",
            (run_id, canary.challenger_version_id, json.dumps(asdict(canary))),
        )
        self.connection.commit()

    def save_report(self, report: EvolutionReport, champion: AgentVersion) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO runs VALUES (?, ?, ?, ?, ?, ?)",
            (
                report.run_id,
                report.started_at,
                report.completed_at,
                report.previous_champion,
                report.selected_champion,
                json.dumps(report.to_dict()),
            ),
        )
        self.connection.execute(
            "INSERT OR REPLACE INTO state VALUES ('champion_version_id', ?)",
            (report.selected_champion,),
        )
        self.connection.execute(
            "INSERT OR REPLACE INTO state VALUES ('champion_payload_json', ?)",
            (json.dumps(champion.to_dict()),),
        )
        self.connection.commit()

    def recent_runs(self, limit: int = 20) -> list[dict]:
        rows = self.connection.execute(
            "SELECT payload_json FROM runs ORDER BY completed_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]
