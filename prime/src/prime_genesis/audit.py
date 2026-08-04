from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from prime_genesis.models import utc_now
from prime_genesis.security import TenantContext, require_role


@dataclass(frozen=True)
class AuditExport:
    tenant_id: str
    generated_at: str
    record_count: int
    sha256: str
    destination: str | None
    records: tuple[dict[str, Any], ...]


class TenantAuditExporter:
    """Exports tenant-scoped operational evidence without memory/document contents."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row

    def close(self) -> None:
        self.connection.close()

    def _table_exists(self, table: str) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        return row is not None

    def _events(self, tenant_id: str) -> list[dict[str, Any]]:
        if not self._table_exists("runtime_events"):
            return []
        rows = self.connection.execute(
            "SELECT event_id, product, event_type, payload_json, created_at "
            "FROM runtime_events WHERE tenant_id=? ORDER BY created_at",
            (tenant_id,),
        ).fetchall()
        return [
            {
                "record_type": "runtime_event",
                "record_id": row["event_id"],
                "product": row["product"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def _feedback(self, tenant_id: str) -> list[dict[str, Any]]:
        if not self._table_exists("feedback"):
            return []
        rows = self.connection.execute(
            "SELECT feedback_id, product, run_id, rating, comment, metadata_json, created_at "
            "FROM feedback WHERE tenant_id=? ORDER BY created_at",
            (tenant_id,),
        ).fetchall()
        return [
            {
                "record_type": "feedback",
                "record_id": row["feedback_id"],
                "product": row["product"],
                "run_id": row["run_id"],
                "rating": int(row["rating"]),
                "comment": row["comment"],
                "metadata": json.loads(row["metadata_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def _usage(self, tenant_id: str) -> list[dict[str, Any]]:
        if not self._table_exists("model_usage"):
            return []
        rows = self.connection.execute(
            "SELECT usage_id, product, model_name, estimated_cost_usd, actual_cost_usd, "
            "usage_date, created_at FROM model_usage WHERE tenant_id=? ORDER BY created_at",
            (tenant_id,),
        ).fetchall()
        return [
            {
                "record_type": "model_usage",
                "record_id": row["usage_id"],
                "product": row["product"],
                "model_name": row["model_name"],
                "estimated_cost_usd": float(row["estimated_cost_usd"]),
                "actual_cost_usd": row["actual_cost_usd"],
                "usage_date": row["usage_date"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def export(
        self,
        context: TenantContext,
        *,
        destination: str | Path | None = None,
    ) -> AuditExport:
        require_role(context, "admin", "auditor")
        records = tuple(self._events(context.tenant_id) + self._feedback(context.tenant_id) + self._usage(context.tenant_id))
        body = "".join(json.dumps(record, sort_keys=True) + "\n" for record in records)
        digest = hashlib.sha256(body.encode()).hexdigest()
        target: str | None = None
        if destination is not None:
            path = Path(destination)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
            target = str(path)
        return AuditExport(
            tenant_id=context.tenant_id,
            generated_at=utc_now(),
            record_count=len(records),
            sha256=digest,
            destination=target,
            records=records,
        )
