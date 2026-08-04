from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MaintenanceResult:
    runtime_events_deleted: int
    feedback_deleted: int
    idempotency_deleted: int
    rate_limit_windows_deleted: int


class RuntimeMaintenance:
    """Purges operational metadata; customer memory and documents are untouched."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.connection = sqlite3.connect(self.path)

    def close(self) -> None:
        self.connection.close()

    def _exists(self, table: str) -> bool:
        return (
            self.connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            is not None
        )

    def purge(
        self,
        *,
        runtime_event_days: int = 30,
        feedback_days: int = 365,
        now_epoch: int | None = None,
    ) -> MaintenanceResult:
        if runtime_event_days < 1 or feedback_days < 1:
            raise ValueError("retention periods must be positive")
        current = int(time.time() if now_epoch is None else now_epoch)
        event_cutoff = current - runtime_event_days * 86400
        feedback_cutoff = current - feedback_days * 86400
        deleted = {
            "runtime_events": 0,
            "feedback": 0,
            "idempotency": 0,
            "rate_limits": 0,
        }
        if self._exists("runtime_events"):
            cursor = self.connection.execute(
                "DELETE FROM runtime_events WHERE CAST(strftime('%s', created_at) AS INTEGER) < ?",
                (event_cutoff,),
            )
            deleted["runtime_events"] = cursor.rowcount
        if self._exists("feedback"):
            cursor = self.connection.execute(
                "DELETE FROM feedback WHERE CAST(strftime('%s', created_at) AS INTEGER) < ?",
                (feedback_cutoff,),
            )
            deleted["feedback"] = cursor.rowcount
        if self._exists("idempotency_keys"):
            cursor = self.connection.execute(
                "DELETE FROM idempotency_keys WHERE expires_at <= ?", (current,)
            )
            deleted["idempotency"] = cursor.rowcount
        if self._exists("rate_limits"):
            cursor = self.connection.execute(
                "DELETE FROM rate_limits WHERE window_start < ?", (current - 86400,)
            )
            deleted["rate_limits"] = cursor.rowcount
        self.connection.commit()
        return MaintenanceResult(
            runtime_events_deleted=deleted["runtime_events"],
            feedback_deleted=deleted["feedback"],
            idempotency_deleted=deleted["idempotency"],
            rate_limit_windows_deleted=deleted["rate_limits"],
        )
