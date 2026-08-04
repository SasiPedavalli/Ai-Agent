from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from prime_genesis.models import utc_now
from prime_genesis.security import TenantContext, require_role


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: str
    tenant_id: str
    namespace: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)


SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    memory_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    namespace TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memories_tenant_namespace
ON memories (tenant_id, namespace, created_at);
"""


class TenantMemoryStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)

    def close(self) -> None:
        self.connection.close()

    @staticmethod
    def _record(row: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            memory_id=row["memory_id"], tenant_id=row["tenant_id"], namespace=row["namespace"],
            content=row["content"], metadata=json.loads(row["metadata_json"]), created_at=row["created_at"],
        )

    def put(self, context: TenantContext, *, namespace: str, content: str, metadata: dict[str, Any] | None = None) -> MemoryRecord:
        require_role(context, "writer", "admin")
        if not namespace.strip() or not content.strip():
            raise ValueError("namespace and content are required")
        record = MemoryRecord(memory_id=f"mem-{uuid.uuid4().hex[:16]}", tenant_id=context.tenant_id,
                              namespace=namespace.strip(), content=content.strip(), metadata=metadata or {})
        self.connection.execute("INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?)",
            (record.memory_id, record.tenant_id, record.namespace, record.content,
             json.dumps(record.metadata, sort_keys=True), record.created_at))
        self.connection.commit()
        return record

    def get(self, context: TenantContext, memory_id: str) -> MemoryRecord | None:
        row = self.connection.execute("SELECT * FROM memories WHERE tenant_id=? AND memory_id=?",
                                      (context.tenant_id, memory_id)).fetchone()
        return self._record(row) if row else None

    def search(self, context: TenantContext, *, query: str, namespace: str | None = None, limit: int = 10) -> list[MemoryRecord]:
        limit = min(max(limit, 1), 100)
        pattern = f"%{query.strip()}%"
        if namespace is None:
            rows = self.connection.execute(
                "SELECT * FROM memories WHERE tenant_id=? AND content LIKE ? COLLATE NOCASE ORDER BY created_at DESC LIMIT ?",
                (context.tenant_id, pattern, limit)).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT * FROM memories WHERE tenant_id=? AND namespace=? AND content LIKE ? COLLATE NOCASE ORDER BY created_at DESC LIMIT ?",
                (context.tenant_id, namespace, pattern, limit)).fetchall()
        return [self._record(row) for row in rows]

    def recent(self, context: TenantContext, *, namespace: str | None = None, limit: int = 20) -> list[MemoryRecord]:
        limit = min(max(limit, 1), 100)
        if namespace is None:
            rows = self.connection.execute(
                "SELECT * FROM memories WHERE tenant_id=? ORDER BY created_at DESC LIMIT ?",
                (context.tenant_id, limit)).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT * FROM memories WHERE tenant_id=? AND namespace=? ORDER BY created_at DESC LIMIT ?",
                (context.tenant_id, namespace, limit)).fetchall()
        return [self._record(row) for row in rows]
