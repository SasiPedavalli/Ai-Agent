from __future__ import annotations
import os
from dataclasses import asdict
from pathlib import Path
from typing import Annotated,Any
try:
 from fastapi import FastAPI,Header,HTTPException
 from fastapi.responses import HTMLResponse,JSONResponse
 from pydantic import BaseModel,Field
except ImportError as exc: raise RuntimeError("Install the API extra: pip install -e '.[api]'") from exc
from prime_genesis.canary import CanaryPolicy
from prime_genesis.engine import evolve
from prime_genesis.providers.mock import DeterministicProvider
from prime_genesis.runtime import PrimeRuntime
from prime_genesis.security import AuthorizationError,TenantContext
from prime_genesis.state import read_status
from prime_genesis.store import ExperimentStore
from prime_products.base import ProductRequest
ROOT=Path(os.getenv('PRIME_ROOT','.')); STATE_PATH=Path(os.getenv('PRIME_STATE_PATH',ROOT/'state/champion.json')); HISTORY_PATH=Path(os.getenv('PRIME_HISTORY_PATH',ROOT/'state/evolution-history.jsonl')); DB_PATH=Path(os.getenv('PRIME_DB_PATH',ROOT/'artifacts/prime.db')); RUNTIME_DB_PATH=Path(os.getenv('PRIME_RUNTIME_DB_PATH',ROOT/'artifacts/runtime.db')); BENCHMARK_PATH=Path(os.getenv('PRIME_BENCHMARK_PATH',ROOT/'data/benchmarks.jsonl')); HOLDOUT_PATH=Path(os.getenv('PRIME_HOLDOUT_PATH',ROOT/'data/holdout.calibration.jsonl'))
app=FastAPI(title='PRIME Control Plane',version='0.3.0')
class EvolutionRequest(BaseModel):
 provider:str=Field(default='mock',pattern='^(mock|openai)$'); model:str|None=None; max_rounds:int=Field(default=2,ge=1,le=8); canary_traffic:float=Field(default=.10,gt=0,le=.5)
class ProductRunRequest(BaseModel):
 text:str=Field(min_length=1); sensitivity:str='standard'; namespace:str='default'; max_cost_usd:float|None=Field(default=None,ge=0); latency_target_ms:int|None=Field(default=None,ge=1); metadata:dict[str,Any]=Field(default_factory=dict)
class MemoryWriteRequest(BaseModel): namespace:str='default'; content:str=Field(min_length=1); metadata:dict[str,Any]=Field(default_factory=dict)
class FeedbackRequest(BaseModel): product:str; run_id:str; rating:int=Field(ge=1,le=5); comment:str=''; metadata:dict[str,Any]=Field(default_factory=dict)
def _provider(name:str,model:str|None):
 if name=='mock': return DeterministicProvider()
 from prime_genesis.providers.openai_responses import OpenAIResponsesProvider
 return OpenAIResponsesProvider(model=model)
def _context(tenant:str,actor:str,roles:str='reader')->TenantContext:
 try:return TenantContext(tenant,actor,frozenset(r.strip() for r in roles.split(',') if r.strip()))
 except ValueError as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
def _runtime()->PrimeRuntime:return PrimeRuntime(RUNTIME_DB_PATH)
@app.exception_handler(AuthorizationError)
def auth_error(_request,exc:AuthorizationError):return JSONResponse(status_code=403,content={'detail':str(exc)})
@app.get('/health')
def health()->dict:return {'status':'ok','service':'prime-control-plane','version':'0.3.0'}
@app.get('/api/status')
def status()->dict:return read_status(STATE_PATH,HISTORY_PATH)
@app.get('/api/runs')
def runs(limit:int=20)->list[dict]:
 store=ExperimentStore(DB_PATH)
 try:return store.recent_runs(min(max(limit,1),100))
 finally:store.close()
@app.post('/api/evolve')
def run_evolution(request:EvolutionRequest)->dict:
 if os.getenv('PRIME_API_EVOLUTION_ENABLED','false').lower()!='true':raise HTTPException(status_code=403,detail='API-triggered evolution is disabled.')
 return evolve(provider=_provider(request.provider,request.model),benchmark_path=BENCHMARK_PATH,holdout_path=HOLDOUT_PATH,db_path=DB_PATH,state_path=STATE_PATH,history_path=HISTORY_PATH,max_mutation_rounds=request.max_rounds,canary_policy=CanaryPolicy(traffic_fraction=request.canary_traffic)).to_dict()
@app.get('/api/products')
def products()->list[dict[str,str]]:
 runtime=_runtime()
 try:return runtime.list_products()
 finally:runtime.close()
@app.post('/api/products/{product}/run')
def run_product(product:str,request:ProductRunRequest,tenant:Annotated[str,Header(alias='X-Prime-Tenant')],actor:Annotated[str,Header(alias='X-Prime-Actor')],roles:Annotated[str,Header(alias='X-Prime-Roles')]='reader')->dict:
 runtime=_runtime()
 try:return runtime.run_product(product,_context(tenant,actor,roles),ProductRequest(request.text,request.sensitivity,request.namespace,request.max_cost_usd,request.latency_target_ms,request.metadata)).to_dict()
 except KeyError as exc:raise HTTPException(status_code=404,detail=str(exc)) from exc
 finally:runtime.close()
@app.post('/api/memory')
def write_memory(request:MemoryWriteRequest,tenant:Annotated[str,Header(alias='X-Prime-Tenant')],actor:Annotated[str,Header(alias='X-Prime-Actor')],roles:Annotated[str,Header(alias='X-Prime-Roles')]='reader')->dict:
 runtime=_runtime()
 try:return asdict(runtime.ingest_memory(_context(tenant,actor,roles),namespace=request.namespace,content=request.content,metadata=request.metadata))
 finally:runtime.close()
@app.get('/api/memory/search')
def search_memory(query:str,tenant:Annotated[str,Header(alias='X-Prime-Tenant')],actor:Annotated[str,Header(alias='X-Prime-Actor')],roles:Annotated[str,Header(alias='X-Prime-Roles')]='reader',namespace:str|None=None,limit:int=10)->list[dict]:
 runtime=_runtime()
 try:return [asdict(r) for r in runtime.search_memory(_context(tenant,actor,roles),query=query,namespace=namespace,limit=limit)]
 finally:runtime.close()
@app.post('/api/feedback')
def feedback(request:FeedbackRequest,tenant:Annotated[str,Header(alias='X-Prime-Tenant')],actor:Annotated[str,Header(alias='X-Prime-Actor')],roles:Annotated[str,Header(alias='X-Prime-Roles')]='reader')->dict:
 runtime=_runtime()
 try:return asdict(runtime.record_feedback(_context(tenant,actor,roles),product=request.product,run_id=request.run_id,rating=request.rating,comment=request.comment,metadata=request.metadata))
 except KeyError as exc:raise HTTPException(status_code=404,detail=str(exc)) from exc
 finally:runtime.close()
DASHBOARD="""<!doctype html><html><head><meta charset='utf-8'><title>PRIME</title><style>body{font-family:system-ui;background:#080b12;color:#e9eefb;max-width:1000px;margin:auto;padding:48px}pre{background:#111827;padding:20px;border-radius:16px}</style></head><body><h1>PRIME Control Center</h1><p>Governed evolution and tenant-scoped product intelligence.</p><pre id='data'>Loading…</pre><script>Promise.all([fetch('/api/status').then(r=>r.json()),fetch('/api/products').then(r=>r.json())]).then(([s,p])=>data.textContent=JSON.stringify({status:s,products:p},null,2)).catch(e=>data.textContent=e)</script></body></html>"""
@app.get('/',response_class=HTMLResponse)
def dashboard()->str:return DASHBOARD
