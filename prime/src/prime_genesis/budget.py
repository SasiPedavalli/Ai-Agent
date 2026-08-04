from __future__ import annotations
import sqlite3,uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from prime_genesis.models import utc_now
from prime_genesis.security import TenantContext,require_role
@dataclass(frozen=True)
class BudgetDecision:
 allowed:bool; daily_limit_usd:float|None; spent_today_usd:float; estimated_cost_usd:float; remaining_after_usd:float|None; reason:str
class BudgetExceededError(RuntimeError):pass
SCHEMA="""CREATE TABLE IF NOT EXISTS tenant_budgets (tenant_id TEXT PRIMARY KEY,daily_limit_usd REAL NOT NULL,updated_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS model_usage (usage_id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,product TEXT NOT NULL,model_name TEXT NOT NULL,estimated_cost_usd REAL NOT NULL,actual_cost_usd REAL,usage_date TEXT NOT NULL,created_at TEXT NOT NULL);CREATE INDEX IF NOT EXISTS idx_model_usage_tenant_date ON model_usage (tenant_id,usage_date);"""
class TenantBudgetStore:
 def __init__(self,path:str|Path)->None:self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self.connection=sqlite3.connect(self.path);self.connection.row_factory=sqlite3.Row;self.connection.executescript(SCHEMA)
 def close(self)->None:self.connection.close()
 def set_daily_limit(self,context:TenantContext,limit_usd:float)->None:
  require_role(context,'admin')
  if limit_usd<0:raise ValueError('daily budget cannot be negative')
  self.connection.execute('INSERT OR REPLACE INTO tenant_budgets VALUES (?, ?, ?)',(context.tenant_id,limit_usd,utc_now()));self.connection.commit()
 def spent_today(self,context:TenantContext)->float:
  row=self.connection.execute('SELECT COALESCE(SUM(COALESCE(actual_cost_usd,estimated_cost_usd)),0) AS total FROM model_usage WHERE tenant_id=? AND usage_date=?',(context.tenant_id,date.today().isoformat())).fetchone();return float(row['total'])
 def authorize(self,context:TenantContext,estimated_cost_usd:float)->BudgetDecision:
  row=self.connection.execute('SELECT daily_limit_usd FROM tenant_budgets WHERE tenant_id=?',(context.tenant_id,)).fetchone();spent=self.spent_today(context)
  if row is None:return BudgetDecision(True,None,spent,estimated_cost_usd,None,'No tenant limit is configured.')
  limit=float(row['daily_limit_usd']);remaining=limit-spent-estimated_cost_usd;allowed=remaining>=-1e-12
  return BudgetDecision(allowed,limit,spent,estimated_cost_usd,max(0.0,remaining),'Budget available.' if allowed else 'Estimated model cost exceeds the remaining daily tenant budget.')
 def record(self,context:TenantContext,*,product:str,model_name:str,estimated_cost_usd:float,actual_cost_usd:float|None=None)->str:
  usage_id=f"usage-{uuid.uuid4().hex[:16]}";self.connection.execute('INSERT INTO model_usage VALUES (?, ?, ?, ?, ?, ?, ?, ?)',(usage_id,context.tenant_id,product,model_name,estimated_cost_usd,actual_cost_usd,date.today().isoformat(),utc_now()));self.connection.commit();return usage_id
