from __future__ import annotations
import uuid
from abc import ABC,abstractmethod
from dataclasses import asdict,dataclass,field
from typing import Any
from prime_genesis.memory import MemoryRecord
from prime_genesis.models import utc_now
from prime_genesis.router import RouteDecision
from prime_genesis.security import TenantContext
from prime_genesis.tools import ToolRegistry

@dataclass(frozen=True)
class ProductRequest:
    text:str; sensitivity:str="standard"; namespace:str="default"; max_cost_usd:float|None=None; latency_target_ms:int|None=None; metadata:dict[str,Any]=field(default_factory=dict)
    def __post_init__(self)->None:
        if not self.text.strip(): raise ValueError("Product request text is required")
        if not self.namespace.strip(): raise ValueError("Product request namespace is required")
@dataclass(frozen=True)
class ProductResult:
    run_id:str; tenant_id:str; product:str; summary:str; findings:tuple[str,...]; evidence:tuple[str,...]; recommendations:tuple[str,...]; confidence:float; route:RouteDecision; metadata:dict[str,Any]=field(default_factory=dict); created_at:str=field(default_factory=utc_now)
    def to_dict(self)->dict[str,Any]:return asdict(self)
class ProductAgent(ABC):
    name:str; description:str
    def make_run_id(self)->str:return f"product-{uuid.uuid4().hex[:16]}"
    @abstractmethod
    def run(self,*,context:TenantContext,request:ProductRequest,route:RouteDecision,memories:list[MemoryRecord],tools:ToolRegistry)->ProductResult: raise NotImplementedError
