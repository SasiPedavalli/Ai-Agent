from __future__ import annotations
import json,sqlite3,time
from pathlib import Path
from typing import Any
from prime_genesis.security import TenantContext
SCHEMA="""CREATE TABLE IF NOT EXISTS idempotency_keys (tenant_id TEXT NOT NULL,operation TEXT NOT NULL,idempotency_key TEXT NOT NULL,response_json TEXT NOT NULL,expires_at INTEGER NOT NULL,PRIMARY KEY (tenant_id,operation,idempotency_key));"""
class IdempotencyStore:
 def __init__(self,path:str|Path)->None:self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self.connection=sqlite3.connect(self.path);self.connection.executescript(SCHEMA)
 def close(self)->None:self.connection.close()
 def get(self,context:TenantContext,*,operation:str,key:str,now:int|None=None)->dict[str,Any]|None:
  if not key or len(key)>200:raise ValueError('idempotency key must contain 1 to 200 characters')
  current=int(time.time() if now is None else now);row=self.connection.execute('SELECT response_json,expires_at FROM idempotency_keys WHERE tenant_id=? AND operation=? AND idempotency_key=?',(context.tenant_id,operation,key)).fetchone()
  if row is None:return None
  if int(row[1])<=current:self.connection.execute('DELETE FROM idempotency_keys WHERE tenant_id=? AND operation=? AND idempotency_key=?',(context.tenant_id,operation,key));self.connection.commit();return None
  return json.loads(row[0])
 def put(self,context:TenantContext,*,operation:str,key:str,response:dict[str,Any],ttl_seconds:int=86400,now:int|None=None)->None:
  if not key or len(key)>200:raise ValueError('idempotency key must contain 1 to 200 characters')
  current=int(time.time() if now is None else now);self.connection.execute('INSERT OR REPLACE INTO idempotency_keys VALUES (?, ?, ?, ?, ?)',(context.tenant_id,operation,key,json.dumps(response,sort_keys=True),current+ttl_seconds));self.connection.commit()
