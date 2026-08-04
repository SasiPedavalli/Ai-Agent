from __future__ import annotations
from dataclasses import asdict,replace
from pathlib import Path
from typing import Any
from prime_genesis.budget import BudgetExceededError,TenantBudgetStore
from prime_genesis.feedback import FeedbackRecord,FeedbackStore
from prime_genesis.idempotency import IdempotencyStore
from prime_genesis.memory import MemoryRecord,TenantMemoryStore
from prime_genesis.model_registry import ModelRegistry,default_model_registry
from prime_genesis.observability import RuntimeEventStore
from prime_genesis.rate_limit import RateLimiter
from prime_genesis.retrieval import DocumentRecord,RetrievalHit,TenantDocumentStore
from prime_genesis.router import ModelRouter,RouteRequest
from prime_genesis.security import TenantContext
from prime_genesis.tools import ToolRegistry,default_tool_registry
from prime_products import CompanyBrainAgent,DigitalTwinAgent,GenomeAgent,GuardianXAgent,ProductAgent,ProductRequest,ProductResult
class PrimeRuntime:
 def __init__(self,path:str|Path='artifacts/runtime.db',*,router:ModelRouter|None=None,tools:ToolRegistry|None=None,models:ModelRegistry|None=None)->None:
  self.path=Path(path);self.memory=TenantMemoryStore(self.path);self.documents=TenantDocumentStore(self.path);self.events=RuntimeEventStore(self.path);self.feedback=FeedbackStore(self.path);self.budgets=TenantBudgetStore(self.path);self.rate_limits=RateLimiter(self.path);self.idempotency=IdempotencyStore(self.path);self.router=router or ModelRouter();self.tools=tools or default_tool_registry();self.models=models or default_model_registry();agents:tuple[ProductAgent,...]=(GuardianXAgent(),GenomeAgent(),CompanyBrainAgent(),DigitalTwinAgent());self.products={a.name:a for a in agents}
 def close(self)->None:self.memory.close();self.documents.close();self.events.close();self.feedback.close();self.budgets.close();self.rate_limits.close();self.idempotency.close()
 def list_products(self)->list[dict[str,str]]:return [{'name':a.name,'description':a.description} for a in sorted(self.products.values(),key=lambda p:p.name)]
 def list_models(self)->list[dict[str,Any]]:return [m.to_dict() for m in self.models.list()]
 def ingest_memory(self,context:TenantContext,*,namespace:str,content:str,metadata:dict[str,Any]|None=None)->MemoryRecord:
  record=self.memory.put(context,namespace=namespace,content=content,metadata=metadata);self.events.emit(context,product='company-brain',event_type='memory_ingested',payload={'memory_id':record.memory_id,'namespace':namespace});return record
 def ingest_document(self,context:TenantContext,*,namespace:str,title:str,content:str,metadata:dict[str,Any]|None=None)->DocumentRecord:
  record=self.documents.add(context,namespace=namespace,title=title,content=content,metadata=metadata);self.events.emit(context,product='company-brain',event_type='document_ingested',payload={'document_id':record.document_id,'namespace':namespace});return record
 def search_documents(self,context:TenantContext,*,query:str,namespace:str|None=None,limit:int=5)->list[RetrievalHit]:return self.documents.search(context,query=query,namespace=namespace,limit=limit)
 def search_memory(self,context:TenantContext,*,query:str,namespace:str|None=None,limit:int=10)->list[MemoryRecord]:return self.memory.search(context,query=query,namespace=namespace,limit=limit)
 def run_product(self,product:str,context:TenantContext,request:ProductRequest)->ProductResult:
  if product not in self.products:raise KeyError(f'Unknown PRIME product: {product}')
  agent=self.products[product];route=self.router.route(RouteRequest(product,request.text,request.sensitivity,request.max_cost_usd,request.latency_target_ms));model=self.models.select(route);estimated=model.estimate_cost(request.text);budget=self.budgets.authorize(context,estimated)
  if not budget.allowed:self.events.emit(context,product=product,event_type='budget_rejected',payload=asdict(budget));raise BudgetExceededError(budget.reason)
  memories=self.memory.recent(context,namespace=request.namespace,limit=20);hits=self.documents.search(context,query=request.text,namespace=request.namespace,limit=5);retrieved=[MemoryRecord(f'retrieved-{h.document.document_id}',context.tenant_id,h.document.namespace,h.document.content,{'title':h.document.title,'retrieval_score':h.score,'matched_terms':list(h.matched_terms)},h.document.created_at) for h in hits]
  self.events.emit(context,product=product,event_type='run_started',payload={'route':asdict(route),'model':model.to_dict(),'namespace':request.namespace,'memory_count':len(memories),'retrieval_count':len(hits),'estimated_cost_usd':estimated})
  try:result=agent.run(context=context,request=request,route=route,memories=memories+retrieved,tools=self.tools)
  except Exception as exc:self.events.emit(context,product=product,event_type='run_failed',payload={'error_type':type(exc).__name__});raise
  usage_id=self.budgets.record(context,product=product,model_name=model.name,estimated_cost_usd=estimated);metadata=dict(result.metadata);metadata.update({'model':model.to_dict(),'budget':asdict(budget),'usage_id':usage_id,'retrieved_documents':[{'document_id':h.document.document_id,'title':h.document.title,'score':h.score,'matched_terms':list(h.matched_terms)} for h in hits]});result=replace(result,metadata=metadata);self.events.emit(context,product=product,event_type='run_completed',payload={'run_id':result.run_id,'model_name':model.name,'usage_id':usage_id});return result
 def record_feedback(self,context:TenantContext,*,product:str,run_id:str,rating:int,comment:str='',metadata:dict[str,Any]|None=None)->FeedbackRecord:
  if product not in self.products:raise KeyError(f'Unknown PRIME product: {product}')
  record=self.feedback.record(context,product=product,run_id=run_id,rating=rating,comment=comment,metadata=metadata);self.events.emit(context,product=product,event_type='feedback_recorded',payload={'feedback_id':record.feedback_id,'rating':rating});return record
