from __future__ import annotations
import re
from prime_genesis.memory import MemoryRecord
from prime_genesis.router import RouteDecision
from prime_genesis.security import TenantContext
from prime_genesis.tools import ToolRegistry
from prime_products.base import ProductAgent,ProductRequest,ProductResult
class GuardianXAgent(ProductAgent):
    name="guardian-x"; description="Evidence-linked reliability, security, data, AI, and cost intelligence."
    SIGNALS={"reliability":("latency","lag","timeout","failed","failure","unavailable","sla"),"data-quality":("schema","null","duplicate","freshness","missing","drift"),"security":("credential","unauthorized","permission","attack","vulnerability"),"cost":("cost","spend","warehouse","idle","overprovision","budget"),"ai-quality":("hallucination","model","prompt","evaluation","drift")}
    def run(self,*,context:TenantContext,request:ProductRequest,route:RouteDecision,memories:list[MemoryRecord],tools:ToolRegistry)->ProductResult:
        sentences=[p.strip() for p in re.split(r"(?<=[.!?])\s+|\n+",request.text) if p.strip()]; findings=[]; evidence=[]; categories=[]
        for category,terms in self.SIGNALS.items():
            matches=tools.invoke("extract_evidence",context,{"text":request.text,"terms":list(terms)})["matches"]
            if matches:
                categories.append(category); findings.append(f"{category} signal: {', '.join(matches)}")
                evidence.extend(s for s in sentences if any(t in s.lower() for t in matches))
        if memories: findings.append(f"{len(memories)} tenant-scoped context record(s) were available for comparison.")
        if not findings: findings.append("No known reliability, security, quality, or cost signal was detected in the supplied evidence.")
        recs=["Validate the signal against telemetry and deployment history before remediation.","Create a reversible diagnostic action and record its evidence."]
        if "reliability" in categories: recs.append("Compare the incident start time with recent deployments and dependency health.")
        if "cost" in categories: recs.append("Compare utilization with configured capacity before resizing resources.")
        if "security" in categories: recs.append("Escalate to an authorized security reviewer; do not expose credentials in logs.")
        return ProductResult(self.make_run_id(),context.tenant_id,self.name,f"Detected {len(categories)} operational signal category(ies)." if categories else "No supported operational incident category was identified.",tuple(findings),tuple(dict.fromkeys(evidence)),tuple(dict.fromkeys(recs)),round(min(.95,.45+.10*len(categories)+.02*len(evidence)),3),route,{"categories":categories,"memory_records_considered":len(memories),"automatic_remediation_executed":False})
