from __future__ import annotations
import tempfile,unittest
from pathlib import Path
from prime_genesis.runtime import PrimeRuntime
from prime_genesis.security import TenantContext
from prime_products.base import ProductRequest
class RuntimeTests(unittest.TestCase):
 def test_all_products_run_and_emit_tenant_scoped_results(self):
  with tempfile.TemporaryDirectory() as d:
   runtime=PrimeRuntime(Path(d)/'runtime.db'); context=TenantContext('acme','operator',frozenset({'reader','writer'}))
   try:
    runtime.ingest_memory(context,namespace='default',content='The deployment runbook lists port 8080.')
    cases={'guardian-x':'Kafka consumer lag caused pipeline latency to breach the SLA.','genome':'A new device initiated an unusual high-value transfer from a new location.','company-brain':'The current architecture record lists port 8443.','digital-twin':'Simulate a 30 percent demand increase with fixed compute capacity.'}
    for product,text in cases.items():
     result=runtime.run_product(product,context,ProductRequest(text=text)); self.assertEqual(result.product,product); self.assertEqual(result.tenant_id,'acme'); self.assertTrue(result.findings); self.assertGreater(result.confidence,0)
    self.assertGreaterEqual(len(runtime.events.recent(context)),9)
   finally: runtime.close()
 def test_company_brain_detects_explicit_conflict(self):
  with tempfile.TemporaryDirectory() as d:
   runtime=PrimeRuntime(Path(d)/'runtime.db'); context=TenantContext('acme','operator',frozenset({'reader','writer'}))
   try:
    runtime.ingest_memory(context,namespace='architecture',content='The deployment runbook lists port 8080.')
    result=runtime.run_product('company-brain',context,ProductRequest(text='The latest architecture record lists port 8443.',namespace='architecture'))
    self.assertEqual(len(result.metadata['conflicts']),1); self.assertFalse(result.metadata['automatic_policy_change'])
   finally: runtime.close()
 def test_feedback_is_recorded_per_tenant(self):
  with tempfile.TemporaryDirectory() as d:
   runtime=PrimeRuntime(Path(d)/'runtime.db'); alpha=TenantContext('alpha','a'); beta=TenantContext('beta','b')
   try:
    runtime.record_feedback(alpha,product='guardian-x',run_id='run-alpha',rating=2,comment='missed dependency')
    self.assertEqual(runtime.feedback.summary(alpha)['count'],1); self.assertEqual(runtime.feedback.summary(beta)['count'],0)
   finally: runtime.close()
if __name__=='__main__':unittest.main()
