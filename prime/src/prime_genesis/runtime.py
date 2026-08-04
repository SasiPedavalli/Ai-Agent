from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
from typing import Any
from prime_genesis.feedback import FeedbackRecord,FeedbackStore
from prime_genesis.memory import MemoryRecord,TenantMemoryStore
from prime_genesis.observability import RuntimeEventStore
from prime_genesis.router import ModelRouter,RouteRequest
from prime_genesis.security import TenantContext
from prime_genesis.tools import ToolRegistry,default_tool_registry
from prime_products import CompanyBrainAgent,DigitalTwinAgent,GenomeAgent,GuardianXAgent,ProductAgent,ProductRequest,ProductResult
class PrimeRuntime:
    def __init__(self,path:str|Path="artifacts/runtime.db",*,router:ModelRouter|None=None,tools:ToolRegistry|None=None)->None:
        self.path=Path(path); self.memory=TenantMemoryStore(self.path); self.events=RuntimeEventStore(self.path); self.feedback=FeedbackStore(self.path); self.router=router or ModelRouter(); self.tools=tools or default_tool_registry()
        agents:tuple[ProductAgent,...]=(GuardianXAgent(),GenomeAgent(),CompanyBrainAgent(),DigitalTwinAgent()); self.products={a.name:a for a in agents}
    def close(self)->None:self.memory.close();self.events.close();self.feedback.close()
    def list_products(self)->list[dict[str,str]]:return [{"name":a.name,"description":a.description} for a in sorted(self.products.values(),key=lambda p:p.name)]
    def ingest_memory(self,context:TenantContext,*,namespace:str,content:str,metadata:dict[str,Any]|None=None)->MemoryRecord:
        record=self.memory.put(context,namespace=namespace,content=content,metadata=metadata); self.events.emit(context,product="company-brain",event_type="memory_ingested",payload={"memory_id":record.memory_id,"namespace":namespace}); return record
    def search_memory(self,context:TenantContext,*,query:str,namespace:str|None=None,limit:int=10)->list[MemoryRecord]:return self.memory.search(context,query=query,namespace=namespace,limit=limit)
    def run_product(self,product:str,context:TenantContext,request:ProductRequest)->ProductResult:
        if product not in self.products: raise KeyError(f"Unknown PRIME product: {product}")
        agent=self.products[product]; route=self.router.route(RouteRequest(product,request.text,request.sensitivity,request.max_cost_usd,request.latency_target_ms)); memories=self.memory.recent(context,namespace=request.namespace,limit=20)
        self.events.emit(context,product=product,event_type="run_started",payload={"route":asdict(route),"namespace":request.namespace,"memory_count":len(memories)})
        try: result=agent.run(context=context,request=request,route=route,memories=memories,tools=self.tools)
        except Exception as exc:
            self.events.emit(context,product=product,event_type="run_failed",payload={"error_type":type(exc).__name__}); raise
        self.events.emit(context,product=product,event_type="run_completed",payload={"run_id":result.run_id,"confidence":result.confidence,"finding_count":len(result.findings),"route_tier":route.tier}); return result
    def record_feedback(self,context:TenantContext,*,product:str,run_id:str,rating:int,comment:str="",metadata:dict[str,Any]|None=None)->FeedbackRecord:
        if product not in self.products: raise KeyError(f"Unknown PRIME product: {product}")
        record=self.feedback.record(context,product=product,run_id=run_id,rating=rating,comment=comment,metadata=metadata); self.events.emit(context,product=product,event_type="feedback_recorded",payload={"feedback_id":record.feedback_id,"rating":rating}); return record
