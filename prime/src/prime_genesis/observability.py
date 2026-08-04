from __future__ import annotations

import json, sqlite3, uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from prime_genesis.models import utc_now
from prime_genesis.security import TenantContext

@dataclass(frozen=True)
class RuntimeEvent:
    event_id: str; tenant_id: str; product: str; event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)

SCHEMA = """
CREATE TABLE IF NOT EXISTS runtime_events (event_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
product TEXT NOT NULL, event_type TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_runtime_events_tenant ON runtime_events (tenant_id, created_at);
"""

class RuntimeEventStore:
    def __init__(self, path: str | Path) -> None:
        self.path=Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection=sqlite3.connect(self.path); self.connection.row_factory=sqlite3.Row
        self.connection.executescript(SCHEMA)
    def close(self) -> None: self.connection.close()
    def emit(self, context: TenantContext, *, product: str, event_type: str, payload: dict[str, Any] | None=None) -> RuntimeEvent:
        event=RuntimeEvent(f"evt-{uuid.uuid4().hex[:16]}", context.tenant_id, product, event_type, payload or {})
        self.connection.execute("INSERT INTO runtime_events VALUES (?, ?, ?, ?, ?, ?)",
            (event.event_id,event.tenant_id,event.product,event.event_type,json.dumps(event.payload,sort_keys=True),event.created_at))
        self.connection.commit(); return event
    def recent(self, context: TenantContext, *, limit: int=50) -> list[RuntimeEvent]:
        rows=self.connection.execute("SELECT * FROM runtime_events WHERE tenant_id=? ORDER BY created_at DESC LIMIT ?",
            (context.tenant_id,min(max(limit,1),200))).fetchall()
        return [RuntimeEvent(row['event_id'],row['tenant_id'],row['product'],row['event_type'],json.loads(row['payload_json']),row['created_at']) for row in rows]
