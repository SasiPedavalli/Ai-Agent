from __future__ import annotations
import re
from prime_genesis.memory import MemoryRecord
from prime_genesis.router import RouteDecision
from prime_genesis.security import TenantContext
from prime_genesis.tools import ToolRegistry
from prime_products.base import ProductAgent,ProductRequest,ProductResult
class DigitalTwinAgent(ProductAgent):
    name="digital-twin"; description="Assumption-explicit operational scenarios and counterfactual simulation support."
    PERCENT=re.compile(r"(?P<value>-?\d+(?:\.\d+)?)\s*(?:percent|%)",re.I)
    def run(self,*,context:TenantContext,request:ProductRequest,route:RouteDecision,memories:list[MemoryRecord],tools:ToolRegistry)->ProductResult:
        percentages=[float(m.group('value')) for m in self.PERCENT.finditer(request.text)]; primary=percentages[0] if percentages else None
        assumptions=["All factors not explicitly changed in the request remain constant.","This is a directional scenario, not a guaranteed forecast."]
        if memories: assumptions.append(f"{len(memories)} tenant-scoped baseline record(s) were available.")
        if primary is None:
            findings=("No explicit percentage change was supplied; only a qualitative scenario can be produced.",); recs=("Supply baseline values and one or more explicit changes for a quantified scenario.",); confidence=.45; summary="Generated a qualitative scenario with explicit missing-data limits."
        else:
            low=round(primary*.75,2); high=round(primary*1.25,2); findings=(f"Primary stated change: {primary:g}%; sensitivity band: {low:g}% to {high:g}%.",); recs=("Test capacity, staffing, dependency, and cost constraints across the sensitivity band.","Compare simulated outcomes with observed telemetry before operational decisions."); confidence=min(.90,.62+.03*len(memories)); summary=f"Generated a counterfactual scenario around a {primary:g}% stated change."
        return ProductResult(self.make_run_id(),context.tenant_id,self.name,summary,findings,(request.text.strip(),),recs,round(confidence,3),route,{"percentages":percentages,"assumptions":assumptions,"memory_records_considered":len(memories),"guaranteed_outcome":False})
