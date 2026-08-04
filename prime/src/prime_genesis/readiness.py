from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from prime_genesis.model_registry import ModelRegistry, default_model_registry


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    passed: bool
    required: bool
    detail: str


@dataclass(frozen=True)
class ReadinessReport:
    ready: bool
    checks: tuple[ReadinessCheck, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _check_state(path: Path) -> ReadinessCheck:
    if not path.exists():
        return ReadinessCheck("champion_state", False, True, f"Missing state file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        champion = payload["champion"]
        version_id = champion["version_id"]
        generation = int(champion["generation"])
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return ReadinessCheck("champion_state", False, True, f"Invalid state: {exc}")
    return ReadinessCheck(
        "champion_state",
        True,
        True,
        f"Active champion {version_id} at generation {generation}.",
    )


def _check_database(path: Path) -> ReadinessCheck:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path)
        try:
            connection.execute("SELECT 1").fetchone()
            connection.execute(
                "CREATE TABLE IF NOT EXISTS readiness_probe (id INTEGER PRIMARY KEY)"
            )
            connection.commit()
        finally:
            connection.close()
    except (OSError, sqlite3.Error) as exc:
        return ReadinessCheck("runtime_database", False, True, str(exc))
    return ReadinessCheck("runtime_database", True, True, f"Writable SQLite database: {path}")


def _check_auth() -> ReadinessCheck:
    mode = os.getenv("PRIME_AUTH_MODE", "local").lower()
    if mode == "local":
        return ReadinessCheck(
            "authentication",
            True,
            True,
            "Local trusted-header mode is enabled; do not expose it publicly.",
        )
    if mode == "hmac":
        secret = os.getenv("PRIME_AUTH_SECRET", "")
        passed = len(secret) >= 32
        return ReadinessCheck(
            "authentication",
            passed,
            True,
            "HMAC authentication is configured."
            if passed
            else "PRIME_AUTH_SECRET must contain at least 32 characters.",
        )
    return ReadinessCheck("authentication", False, True, f"Unsupported auth mode: {mode}")


def _check_models(registry: ModelRegistry) -> ReadinessCheck:
    enabled = registry.list(enabled_only=True)
    tiers = {model.tier for model in enabled}
    required = {"local-private", "fast", "balanced", "reasoning"}
    missing = sorted(required - tiers)
    return ReadinessCheck(
        "model_registry",
        not missing,
        True,
        f"Enabled model tiers: {sorted(tiers)}."
        if not missing
        else f"Missing enabled model tiers: {missing}.",
    )


def evaluate_readiness(
    *,
    state_path: str | Path = "state/champion.json",
    runtime_db_path: str | Path = "artifacts/runtime.db",
    registry: ModelRegistry | None = None,
) -> ReadinessReport:
    checks = (
        _check_state(Path(state_path)),
        _check_database(Path(runtime_db_path)),
        _check_auth(),
        _check_models(registry or default_model_registry()),
    )
    return ReadinessReport(
        ready=all(check.passed for check in checks if check.required),
        checks=checks,
    )
