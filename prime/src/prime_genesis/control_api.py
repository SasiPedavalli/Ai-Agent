from __future__ import annotations
import os
from dataclasses import asdict
from pathlib import Path
from typing import Annotated,Any
try:
 from fastapi import FastAPI,Header,HTTPException
 from fastapi.responses import HTMLResponse,JSONResponse
 from pydantic import BaseModel,Field
except ImportError as exc:raise RuntimeError("Install the API extra: pip install -e '.[api]'") from exc
from prime_genesis.canary import CanaryPolicy
from prime_genesis.engine import evolve
from prime_genesis.providers.mock import DeterministicProvider
from prime_genesis.runtime import PrimeRuntime
from prime_genesis.security import AuthorizationError,TenantContext
from prime_genesis.state import read_status
from prime_genesis.store import ExperimentStore
from prime_products.base import ProductRequest
ROOT=Path(os.getenv('PRIME_ROOT','.'));STATE_PATH=Path(os.getenv('PRIME_STATE_PATH',ROOT/'state/champion.json'));HISTORY_PATH=Path(os.getenv('PRIME_HISTORY_PATH',ROOT/'state/evolution-history.jsonl'));DB_PATH=Path(os.getenv('PRIME_DB_PATH',ROOT/'artifacts/prime.db'));RUNTIME_DB_PATH=Path(os.getenv('PRIME_RUNTIME_DB_PATH',ROOT/'artifacts/runtime.db'));BENCHMARK_PATH=Path(os.getenv('PRIME_BENCHMARK_PATH',ROOT/'data/benchmarks.jsonl'));HOLDOUT_PATH=Path(os.getenv('PRIME_HOLDOUT_PATH',ROOT/'data/holdout.calibration.jsonl'))
app=FastAPI(title='PRIME Control Plane',version='0.4.0')
class EvolutionRequest(BaseModel):provider:str=Field(default='mock',pattern='^(mock|openai)$');model:str|None=None;max_rounds:int=Field(default=2,ge=1,le=8);canary_traffic:float=Field(default=.1,gt=0,le=.5)
class ProductRunRequest(BaseModel):text:str=Field(min_length=1);sensitivity:str='standard';namespace:str='default';max_cost_usd:float|None=Field(default=None,ge=0);latency_target_ms:int|None=Field(default=None,ge=1);metadata:dict[str,Any]=Field(default_factory=dict)
class MemoryWriteRequest(BaseModel):namespace:str='default';content:str=Field(min_length=1);metadata:dict[str,Any]=Field(default_factory=dict)
class DocumentWriteRequest(BaseModel):namespace:str='default';title:str=Field(min_length=1);content:str=Field(min_length=1);metadata:dict[str,Any]=Field(default_factory=dict)
class BudgetWriteRequest(BaseModel):daily_limit_usd:float=Field(ge=0)
class FeedbackRequest(BaseModel):product:str;run_id:str;rating:int=Field(ge=1,le=5);comment:str='';metadata:dict[str,Any]=Field(default_factory=dict)
def _context(t,a,r='reader'):
 try:return TenantContext(t,a,frozenset(x.strip() for x in r.split(',') if x.strip()))
 except ValueError as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
def _runtime():return PrimeRuntime(RUNTIME_DB_PATH)
def _provider(n,m):
 if n=='mock':return DeterministicProvider()
 from prime_genesis.providers.openai_responses import OpenAIResponsesProvider
 return OpenAIResponsesProvider(model=m)
@app.exception_handler(AuthorizationError)
def auth_error(_r,e):return JSONResponse(status_code=403,content={'detail':str(e)})
@app.get('/health')
def health():return {'status':'ok','service':'prime-control-plane','version':'0.4.0'}
@app.get('/api/status')
def status():return read_status(STATE_PATH,HISTORY_PATH)
@app.get('/api/runs')
def runs(limit:int=20):
 s=ExperimentStore(DB_PATH)
 try:return s.recent_runs(min(max(limit,1),100))
 finally:s.close()
@app.post('/api/evolve')
def run_evolution(q:EvolutionRequest):
 if os.getenv('PRIME_API_EVOLUTION_ENABLED','false').lower()!='true':raise HTTPException(403,'API-triggered evolution is disabled.')
 return evolve(provider=_provider(q.provider,q.model),benchmark_path=BENCHMARK_PATH,holdout_path=HOLDOUT_PATH,db_path=DB_PATH,state_path=STATE_PATH,history_path=HISTORY_PATH,max_mutation_rounds=q.max_rounds,canary_policy=CanaryPolicy(traffic_fraction=q.canary_traffic)).to_dict()
@app.get('/api/products')
def products():
 r=_runtime()
 try:return r.list_products()
 finally:r.close()
@app.get('/api/models')
def models():
 r=_runtime()
 try:return r.list_models()
 finally:r.close()
@app.post('/api/products/{product}/run')
def run_product(product:str,q:ProductRunRequest,tenant:Annotated[str,Header(alias='X-Prime-Tenant')],actor:Annotated[str,Header(alias='X-Prime-Actor')],roles:Annotated[str,Header(alias='X-Prime-Roles')]='reader'):
 r=_runtime()
 try:return r.run_product(product,_context(tenant,actor,roles),ProductRequest(q.text,q.sensitivity,q.namespace,q.max_cost_usd,q.latency_target_ms,q.metadata)).to_dict()
 except KeyError as exc:raise HTTPException(404,str(exc)) from exc
 finally:r.close()
@app.post('/api/memory')
def write_memory(q:MemoryWriteRequest,tenant:Annotated[str,Header(alias='X-Prime-Tenant')],actor:Annotated[str,Header(alias='X-Prime-Actor')],roles:Annotated[str,Header(alias='X-Prime-Roles')]='reader'):
 r=_runtime()
 try:return asdict(r.ingest_memory(_context(tenant,actor,roles),namespace=q.namespace,content=q.content,metadata=q.metadata))
 finally:r.close()
@app.get('/api/memory/search')
def search_memory(query:str,tenant:Annotated[str,Header(alias='X-Prime-Tenant')],actor:Annotated[str,Header(alias='X-Prime-Actor')],roles:Annotated[str,Header(alias='X-Prime-Roles')]='reader',namespace:str|None=None,limit:int=10):
 r=_runtime()
 try:return [asdict(x) for x in r.search_memory(_context(tenant,actor,roles),query=query,namespace=namespace,limit=limit)]
 finally:r.close()
@app.post('/api/documents')
def write_document(q:DocumentWriteRequest,tenant:Annotated[str,Header(alias='X-Prime-Tenant')],actor:Annotated[str,Header(alias='X-Prime-Actor')],roles:Annotated[str,Header(alias='X-Prime-Roles')]='reader'):
 r=_runtime()
 try:return asdict(r.ingest_document(_context(tenant,actor,roles),namespace=q.namespace,title=q.title,content=q.content,metadata=q.metadata))
 finally:r.close()
@app.get('/api/documents/search')
def search_documents(query:str,tenant:Annotated[str,Header(alias='X-Prime-Tenant')],actor:Annotated[str,Header(alias='X-Prime-Actor')],roles:Annotated[str,Header(alias='X-Prime-Roles')]='reader',namespace:str|None=None,limit:int=5):
 r=_runtime()
 try:return [{'document':asdict(h.document),'score':h.score,'matched_terms':h.matched_terms} for h in r.search_documents(_context(tenant,actor,roles),query=query,namespace=namespace,limit=limit)]
 finally:r.close()
@app.post('/api/budget')
def set_budget(q:BudgetWriteRequest,tenant:Annotated[str,Header(alias='X-Prime-Tenant')],actor:Annotated[str,Header(alias='X-Prime-Actor')],roles:Annotated[str,Header(alias='X-Prime-Roles')]='reader'):
 r=_runtime();c=_context(tenant,actor,roles)
 try:r.budgets.set_daily_limit(c,q.daily_limit_usd);return asdict(r.budgets.authorize(c,0))
 finally:r.close()
@app.get('/api/budget')
def budget(tenant:Annotated[str,Header(alias='X-Prime-Tenant')],actor:Annotated[str,Header(alias='X-Prime-Actor')],roles:Annotated[str,Header(alias='X-Prime-Roles')]='reader'):
 r=_runtime()
 try:return asdict(r.budgets.authorize(_context(tenant,actor,roles),0))
 finally:r.close()
@app.post('/api/feedback')
def feedback(q:FeedbackRequest,tenant:Annotated[str,Header(alias='X-Prime-Tenant')],actor:Annotated[str,Header(alias='X-Prime-Actor')],roles:Annotated[str,Header(alias='X-Prime-Roles')]='reader'):
 r=_runtime()
 try:return asdict(r.record_feedback(_context(tenant,actor,roles),product=q.product,run_id=q.run_id,rating=q.rating,comment=q.comment,metadata=q.metadata))
 finally:r.close()
DASHBOARD="""<!doctype html><html><head><title>PRIME</title><style>body{font-family:system-ui;background:#080b12;color:#e9eefb;max-width:1000px;margin:auto;padding:48px}pre{background:#111827;padding:20px;border-radius:16px}</style></head><body><h1>PRIME Control Center</h1><pre id='data'>Loading</pre><script>Promise.all(['/api/status','/api/products','/api/models'].map(x=>fetch(x).then(r=>r.json()))).then(([status,products,models])=>data.textContent=JSON.stringify({status,products,models},null,2))</script></body></html>"""
@app.get('/',response_class=HTMLResponse)
def dashboard():return DASHBOARD
