from __future__ import annotations
from prime_genesis.memory import MemoryRecord
from prime_genesis.router import RouteDecision
from prime_genesis.security import TenantContext
from prime_genesis.tools import ToolRegistry
from prime_products.base import ProductAgent,ProductRequest,ProductResult
class GenomeAgent(ProductAgent):
    name="genome"; description="Longitudinal behavioral signatures for finance and healthcare decision support."
    FINANCE=("new device","new location","high-value","velocity","unusual","multiple transfers","failed login")
    HEALTH=("readmission","medication gap","missed follow-up","care gap","adherence","repeated visit")
    def run(self,*,context:TenantContext,request:ProductRequest,route:RouteDecision,memories:list[MemoryRecord],tools:ToolRegistry)->ProductResult:
        finance=tools.invoke("extract_evidence",context,{"text":request.text,"terms":list(self.FINANCE)})["matches"]
        health=tools.invoke("extract_evidence",context,{"text":request.text,"terms":list(self.HEALTH)})["matches"]
        indicators=finance+health; domain="finance" if finance and not health else "healthcare" if health and not finance else "mixed" if indicators else "undetermined"
        findings=[f"Observed indicator: {i}" for i in indicators]
        if memories: findings.append(f"Longitudinal comparison included {len(memories)} tenant-scoped record(s).")
        if not findings: findings.append("No configured longitudinal indicator was present in the supplied evidence.")
        recs=["Treat this output as a risk-support signal, not a diagnosis or confirmed fraud decision.","Review temporal sequence, baseline behavior, and missing context before action."]
        if domain=="finance": recs.append("Apply customer-approved verification controls before restricting activity.")
        if domain=="healthcare": recs.append("Route to an authorized clinician or care team for interpretation.")
        return ProductResult(self.make_run_id(),context.tenant_id,self.name,f"Constructed a {domain} behavioral signature from {len(indicators)} observed indicator(s).",tuple(findings),(request.text.strip(),) if indicators else (),tuple(recs),round(min(.93,.40+.09*len(indicators)+.015*len(memories)),3),route,{"domain":domain,"finance_indicators":finance,"health_indicators":health,"memory_records_considered":len(memories),"diagnosis_made":False,"fraud_confirmed":False})
