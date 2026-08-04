from __future__ import annotations
import sqlite3,time
from dataclasses import dataclass
from pathlib import Path
from prime_genesis.security import TenantContext
class RateLimitExceededError(RuntimeError):pass
@dataclass(frozen=True)
class RateLimitDecision:allowed:bool;limit:int;remaining:int;reset_at:int
SCHEMA="""CREATE TABLE IF NOT EXISTS rate_limits (tenant_id TEXT NOT NULL,actor_id TEXT NOT NULL,operation TEXT NOT NULL,window_start INTEGER NOT NULL,request_count INTEGER NOT NULL,PRIMARY KEY (tenant_id,actor_id,operation,window_start));"""
class RateLimiter:
 def __init__(self,path:str|Path)->None:self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self.connection=sqlite3.connect(self.path);self.connection.executescript(SCHEMA)
 def close(self)->None:self.connection.close()
 def consume(self,context:TenantContext,*,operation:str,limit:int=60,window_seconds:int=60,now:int|None=None)->RateLimitDecision:
  if limit<1 or window_seconds<1:raise ValueError('rate limit and window must be positive')
  current=int(time.time() if now is None else now);start=current-current%window_seconds;row=self.connection.execute('SELECT request_count FROM rate_limits WHERE tenant_id=? AND actor_id=? AND operation=? AND window_start=?',(context.tenant_id,context.actor_id,operation,start)).fetchone();count=int(row[0]) if row else 0;allowed=count<limit
  if allowed:count+=1;self.connection.execute('INSERT OR REPLACE INTO rate_limits VALUES (?, ?, ?, ?, ?)',(context.tenant_id,context.actor_id,operation,start,count));self.connection.commit()
  return RateLimitDecision(allowed,limit,max(0,limit-count),start+window_seconds)
