from __future__ import annotations
import unittest
from prime_genesis.router import ModelRouter,RouteRequest
class RouterTests(unittest.TestCase):
 def test_restricted_workload_uses_private_tier(self):
  decision=ModelRouter().route(RouteRequest(domain='genome',text='patient record',sensitivity='regulated')); self.assertEqual(decision.tier,'local-private'); self.assertIn('private-inference',decision.required_capabilities)
 def test_counterfactual_uses_reasoning_tier(self):
  self.assertEqual(ModelRouter().route(RouteRequest(domain='digital-twin',text='Simulate a demand counterfactual')).tier,'reasoning')
if __name__=='__main__':unittest.main()
