from __future__ import annotations
import re
from prime_genesis.memory import MemoryRecord
from prime_genesis.router import RouteDecision
from prime_genesis.security import TenantContext
from prime_genesis.tools import ToolRegistry
from prime_products.base import ProductAgent,ProductRequest,ProductResult
class CompanyBrainAgent(ProductAgent):
    name="company-brain"; description="Tenant-isolated organizational memory, evidence retrieval, and conflict detection."
    VALUE=re.compile(r"\b\d+(?:\.\d+)?(?:%|[- ]?(?:day|days|hour|hours|port|gb|tb))?\b",re.I)
    @classmethod
    def _values(cls,text:str)->list[str]: return cls.VALUE.findall(text)
    def run(self,*,context:TenantContext,request:ProductRequest,route:RouteDecision,memories:list[MemoryRecord],tools:ToolRegistry)->ProductResult:
        source=self._values(request.text); conflicts=[]; evidence=[request.text.strip()]
        for memory in memories:
            values=self._values(memory.content)
            if source and values and set(source)!=set(values):
                conflicts.append({"memory_id":memory.memory_id,"request_values":", ".join(source),"memory_values":", ".join(values)}); evidence.append(memory.content)
        findings=[]
        if conflicts:
            findings=[f"Detected {len(conflicts)} possible numeric or policy conflict(s)."]+[f"Conflict with {c['memory_id']}: request [{c['request_values']}] vs memory [{c['memory_values']}]" for c in conflicts]
        elif memories: findings=[f"Retrieved {len(memories)} tenant-scoped memory record(s); no explicit numeric conflict was detected."]
        else: findings=["No tenant memory was available for evidence comparison."]
        return ProductResult(self.make_run_id(),context.tenant_id,self.name,f"Found {len(conflicts)} possible organizational knowledge conflict(s)." if conflicts else "Completed tenant-scoped organizational evidence review.",tuple(findings),tuple(dict.fromkeys(evidence)),("Verify document dates, owners, and authority before resolving a conflict.","Preserve both sources and record the human-approved decision."),round(min(.95,.55+.08*len(conflicts)+.02*len(memories)),3),route,{"memory_records_considered":len(memories),"conflicts":conflicts,"automatic_policy_change":False})
