from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from prime_genesis.models import AgentVersion, EvolutionReport, PromotionDecision, Scorecard


SCHEMA = """
CREATE TABLE IF NOT EXISTS versions (
    version_id TEXT PRIMARY KEY,
    parent_version_id TEXT,
    mutation_type TEXT NOT NULL,
    mutation_reason TEXT NOT NULL,
    prompt TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scorecards (
    run_id TEXT NOT NULL,
    version_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (run_id, version_id)
);
CREATE TABLE IF NOT EXISTS decisions (
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
        self.connection.executescript(SCHEMA)

    def close(self) -> None:
        self.connection.close()

    def save_version(self, version: AgentVersion) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO versions VALUES (?, ?, ?, ?, ?, ?)",
            (
                version.version_id,
                version.parent_version_id,
                version.mutation_type,
                version.mutation_reason,
                version.prompt,
                version.created_at,
            ),
        )
        self.connection.commit()

    def save_scorecard(self, run_id: str, scorecard: Scorecard) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO scorecards VALUES (?, ?, ?)",
            (run_id, scorecard.version_id, json.dumps(asdict(scorecard))),
        )
        self.connection.commit()

    def save_decision(self, run_id: str, decision: PromotionDecision) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO decisions VALUES (?, ?, ?)",
            (run_id, decision.challenger_version_id, json.dumps(asdict(decision))),
        )
        self.connection.commit()

    def save_report(self, report: EvolutionReport) -> None:
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
        self.connection.commit()
