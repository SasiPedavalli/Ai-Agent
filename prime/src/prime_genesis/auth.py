from __future__ import annotations
import base64,hashlib,hmac,json,time
from dataclasses import asdict,dataclass
from prime_genesis.security import TenantContext
class AuthenticationError(PermissionError):pass
@dataclass(frozen=True)
class AuthClaims:
 tenant_id:str;actor_id:str;roles:tuple[str,...];issued_at:int;expires_at:int
 def to_context(self)->TenantContext:return TenantContext(self.tenant_id,self.actor_id,frozenset(self.roles))
def _enc(data:bytes)->str:return base64.urlsafe_b64encode(data).decode().rstrip('=')
def _dec(data:str)->bytes:return base64.urlsafe_b64decode(data+'='*(-len(data)%4))
def issue_token(secret:str,context:TenantContext,*,ttl_seconds:int=3600,now:int|None=None)->str:
 if len(secret)<32:raise ValueError('PRIME auth secret must contain at least 32 characters')
 if ttl_seconds<1 or ttl_seconds>86400:raise ValueError('token TTL must be between 1 and 86400 seconds')
 issued=int(time.time() if now is None else now);claims=AuthClaims(context.tenant_id,context.actor_id,tuple(sorted(context.roles)),issued,issued+ttl_seconds);header=_enc(json.dumps({'alg':'HS256','typ':'PRIME'},separators=(',',':'),sort_keys=True).encode());payload=_enc(json.dumps(asdict(claims),separators=(',',':'),sort_keys=True).encode());sig=_enc(hmac.new(secret.encode(),f'{header}.{payload}'.encode(),hashlib.sha256).digest());return f'{header}.{payload}.{sig}'
def verify_token(secret:str,token:str,*,now:int|None=None)->AuthClaims:
 if len(secret)<32:raise AuthenticationError('PRIME authentication is misconfigured')
 try:
  header,payload,supplied=token.split('.');expected=_enc(hmac.new(secret.encode(),f'{header}.{payload}'.encode(),hashlib.sha256).digest())
  if not hmac.compare_digest(expected,supplied):raise AuthenticationError('invalid token signature')
  if json.loads(_dec(header))!={'alg':'HS256','typ':'PRIME'}:raise AuthenticationError('unsupported token header')
  data=json.loads(_dec(payload));claims=AuthClaims(data['tenant_id'],data['actor_id'],tuple(data['roles']),int(data['issued_at']),int(data['expires_at']))
 except AuthenticationError:raise
 except Exception as exc:raise AuthenticationError('malformed PRIME token') from exc
 current=int(time.time() if now is None else now)
 if claims.issued_at>current+60:raise AuthenticationError('token issued in the future')
 if claims.expires_at<=current:raise AuthenticationError('token expired')
 claims.to_context();return claims
