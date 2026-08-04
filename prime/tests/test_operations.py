from __future__ import annotations
import tempfile,unittest
from pathlib import Path
from prime_genesis.auth import AuthenticationError,issue_token,verify_token
from prime_genesis.backup import backup_sqlite
from prime_genesis.idempotency import IdempotencyStore
from prime_genesis.rate_limit import RateLimiter
from prime_genesis.security import TenantContext
class OperationsTests(unittest.TestCase):
 def test_signed_token_verification_tamper_and_expiry(self):
  secret='x'*32;context=TenantContext('acme','alice',frozenset({'reader','writer'}));token=issue_token(secret,context,ttl_seconds=60,now=100);self.assertEqual(verify_token(secret,token,now=120).to_context(),context)
  with self.assertRaises(AuthenticationError):verify_token(secret,token[:-1]+('A' if token[-1]!='A' else 'B'),now=120)
  with self.assertRaises(AuthenticationError):verify_token(secret,token,now=161)
 def test_rate_limit_is_scoped_by_actor_and_operation(self):
  with tempfile.TemporaryDirectory() as d:
   store=RateLimiter(Path(d)/'runtime.db');alice=TenantContext('acme','alice');bob=TenantContext('acme','bob')
   try:self.assertTrue(store.consume(alice,operation='run',limit=2,now=120).allowed);self.assertTrue(store.consume(alice,operation='run',limit=2,now=121).allowed);self.assertFalse(store.consume(alice,operation='run',limit=2,now=122).allowed);self.assertTrue(store.consume(bob,operation='run',limit=2,now=122).allowed);self.assertTrue(store.consume(alice,operation='search',limit=2,now=122).allowed)
   finally:store.close()
 def test_idempotency_is_tenant_scoped_and_expires(self):
  with tempfile.TemporaryDirectory() as d:
   store=IdempotencyStore(Path(d)/'runtime.db');alpha=TenantContext('alpha','a');beta=TenantContext('beta','b')
   try:store.put(alpha,operation='product',key='request-1',response={'run_id':'same'},ttl_seconds=60,now=100);self.assertEqual(store.get(alpha,operation='product',key='request-1',now=120),{'run_id':'same'});self.assertIsNone(store.get(beta,operation='product',key='request-1',now=120));self.assertIsNone(store.get(alpha,operation='product',key='request-1',now=161))
   finally:store.close()
 def test_backup_is_copied_and_hashed(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source=root/'runtime.db';source.write_bytes(b'prime-state');result=backup_sqlite(source,root/'backups/runtime.db');self.assertEqual(result.size_bytes,len(b'prime-state'));self.assertEqual(len(result.sha256),64)
if __name__=='__main__':unittest.main()
