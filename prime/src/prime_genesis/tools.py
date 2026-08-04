from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable
from prime_genesis.security import TenantContext, require_role

ToolHandler=Callable[[TenantContext,dict[str,Any]],dict[str,Any]]
@dataclass(frozen=True)
class ToolSpec:
    name:str; description:str; handler:ToolHandler; required_roles:tuple[str,...]=("reader","writer","admin")
class ToolRegistry:
    def __init__(self)->None:self._tools:dict[str,ToolSpec]={}
    def register(self,spec:ToolSpec)->None:
        if spec.name in self._tools: raise ValueError(f"Tool already registered: {spec.name}")
        self._tools[spec.name]=spec
    def list(self)->list[dict[str,Any]]:return [{"name":s.name,"description":s.description} for s in sorted(self._tools.values(),key=lambda x:x.name)]
    def invoke(self,name:str,context:TenantContext,arguments:dict[str,Any])->dict[str,Any]:
        if name not in self._tools: raise KeyError(f"Unknown tool: {name}")
        spec=self._tools[name]; require_role(context,*spec.required_roles); return spec.handler(context,arguments)
def extract_evidence(_context:TenantContext,arguments:dict[str,Any])->dict[str,Any]:
    text=str(arguments.get("text","")); terms=[str(t) for t in arguments.get("terms",[])]; matches=[t for t in terms if t.lower() in text.lower()]; return {"matches":matches,"match_count":len(matches)}
def compare_values(_context:TenantContext,arguments:dict[str,Any])->dict[str,Any]:
    left=arguments.get("left"); right=arguments.get("right"); return {"equal":left==right,"left":left,"right":right}
def default_tool_registry()->ToolRegistry:
    registry=ToolRegistry(); registry.register(ToolSpec("extract_evidence","Find supplied terms in the provided evidence text.",extract_evidence)); registry.register(ToolSpec("compare_values","Compare two explicit values without inferring missing context.",compare_values)); return registry
