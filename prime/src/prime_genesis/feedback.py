from __future__ import annotations

import json, sqlite3, uuid
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any
from prime_genesis.models import utc_now
from prime_genesis.security import TenantContext

@dataclass(frozen=True)
class FeedbackRecord:
    feedback_id: str; tenant_id: str; product: str; run_id: str; rating: int
    comment: str=""; metadata: dict[str, Any]=field(default_factory=dict); created_at: str=field(default_factory=utc_now)

SCHEMA="""
CREATE TABLE IF NOT EXISTS feedback (feedback_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, product TEXT NOT NULL,
run_id TEXT NOT NULL, rating INTEGER NOT NULL, comment TEXT NOT NULL, metadata_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_feedback_tenant_product ON feedback (tenant_id, product, created_at);
"""

class FeedbackStore:
    def __init__(self,path:str|Path)->None:
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.connection=sqlite3.connect(self.path); self.connection.row_factory=sqlite3.Row; self.connection.executescript(SCHEMA)
    def close(self)->None:self.connection.close()
    def record(self,context:TenantContext,*,product:str,run_id:str,rating:int,comment:str="",metadata:dict[str,Any]|None=None)->FeedbackRecord:
        if rating<1 or rating>5: raise ValueError("rating must be between 1 and 5")
        record=FeedbackRecord(f"fb-{uuid.uuid4().hex[:16]}",context.tenant_id,product,run_id,rating,comment.strip(),metadata or {})
        self.connection.execute("INSERT INTO feedback VALUES (?, ?, ?, ?, ?, ?, ?, ?)",(record.feedback_id,record.tenant_id,record.product,record.run_id,record.rating,record.comment,json.dumps(record.metadata,sort_keys=True),record.created_at)); self.connection.commit(); return record
    def summary(self,context:TenantContext,product:str|None=None)->dict[str,Any]:
        if product is None: rows=self.connection.execute("SELECT rating FROM feedback WHERE tenant_id=?",(context.tenant_id,)).fetchall()
        else: rows=self.connection.execute("SELECT rating FROM feedback WHERE tenant_id=? AND product=?",(context.tenant_id,product)).fetchall()
        ratings=[int(row['rating']) for row in rows]
        return {"count":len(ratings),"average_rating":mean(ratings) if ratings else None,"low_rating_count":sum(r<=2 for r in ratings)}
