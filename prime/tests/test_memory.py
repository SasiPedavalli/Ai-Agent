from __future__ import annotations
import tempfile,unittest
from pathlib import Path
from prime_genesis.memory import TenantMemoryStore
from prime_genesis.security import AuthorizationError,TenantContext
class MemoryTests(unittest.TestCase):
 def test_tenant_memory_isolation_and_write_roles(self):
  with tempfile.TemporaryDirectory() as d:
   store=TenantMemoryStore(Path(d)/'runtime.db')
   try:
    aw=TenantContext('alpha','alice',frozenset({'writer'})); ar=TenantContext('alpha','anna',frozenset({'reader'})); br=TenantContext('beta','bob',frozenset({'reader'}))
    record=store.put(aw,namespace='policy',content='Service retention is 30 days.')
    self.assertEqual(store.get(ar,record.memory_id),record); self.assertIsNone(store.get(br,record.memory_id)); self.assertEqual(len(store.search(ar,query='30 days')),1); self.assertEqual(store.search(br,query='30 days'),[])
    with self.assertRaises(AuthorizationError): store.put(ar,namespace='policy',content='unauthorized')
   finally: store.close()
if __name__=='__main__':unittest.main()
