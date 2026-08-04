from __future__ import annotations
import tempfile,unittest
from pathlib import Path
from prime_genesis.budget import BudgetExceededError,TenantBudgetStore
from prime_genesis.model_registry import ModelRegistry,ModelSpec
from prime_genesis.router import RouteDecision
from prime_genesis.runtime import PrimeRuntime
from prime_genesis.security import TenantContext
from prime_products.base import ProductRequest
class PlatformTests(unittest.TestCase):
 def test_model_registry_selects_private_and_failover_models(self):
  registry=ModelRegistry([ModelSpec('fast','test','fast','fast',('text','structured-output')),ModelSpec('private','test','private','local-private',('private-inference','audit','text'),privacy_boundary='tenant')]);self.assertEqual(registry.select(RouteDecision('local-private','private',('private-inference','audit'))).name,'private');self.assertEqual(registry.select(RouteDecision('balanced','balanced',('text','structured-output'))).name,'fast')
 def test_budget_rejects_spend_over_limit(self):
  with tempfile.TemporaryDirectory() as d:
   store=TenantBudgetStore(Path(d)/'runtime.db');admin=TenantContext('acme','admin',frozenset({'admin'}))
   try:store.set_daily_limit(admin,.001);store.record(admin,product='guardian-x',model_name='model',estimated_cost_usd=.0006);self.assertFalse(store.authorize(admin,.0005).allowed)
   finally:store.close()
 def test_retrieval_is_tenant_scoped_and_added_to_result(self):
  with tempfile.TemporaryDirectory() as d:
   runtime=PrimeRuntime(Path(d)/'runtime.db');alpha=TenantContext('alpha','writer',frozenset({'reader','writer'}));beta=TenantContext('beta','reader')
   try:
    runtime.ingest_document(alpha,namespace='architecture',title='Runbook',content='The service listens on port 8080 and uses Kafka consumer lag alerts.');self.assertEqual(runtime.search_documents(beta,query='Kafka'),[]);result=runtime.run_product('company-brain',alpha,ProductRequest(text='The architecture decision uses port 8443.',namespace='architecture'));self.assertEqual(len(result.metadata['retrieved_documents']),1);self.assertIn('model',result.metadata);self.assertIn('budget',result.metadata)
   finally:runtime.close()
 def test_runtime_enforces_tenant_budget(self):
  with tempfile.TemporaryDirectory() as d:
   registry=ModelRegistry([ModelSpec('paid','test','paid','balanced',('text','structured-output'),input_cost_per_million=1000,output_cost_per_million=1000)]);runtime=PrimeRuntime(Path(d)/'runtime.db',models=registry);admin=TenantContext('acme','admin',frozenset({'admin','reader'}))
   try:
    runtime.budgets.set_daily_limit(admin,.0001)
    with self.assertRaises(BudgetExceededError):runtime.run_product('guardian-x',admin,ProductRequest(text='pipeline latency'))
   finally:runtime.close()
if __name__=='__main__':unittest.main()
