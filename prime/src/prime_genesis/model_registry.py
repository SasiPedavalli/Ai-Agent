from __future__ import annotations
import os
from dataclasses import asdict,dataclass
from typing import Iterable
from prime_genesis.router import RouteDecision
@dataclass(frozen=True)
class ModelSpec:
 name:str; provider:str; model_id:str; tier:str; capabilities:tuple[str,...]; privacy_boundary:str='shared'; input_cost_per_million:float=0.0; output_cost_per_million:float=0.0; priority:int=10; enabled:bool=True
 def estimate_cost(self,text:str,expected_output_tokens:int=300)->float:
  return ((max(1,len(text)//4)*self.input_cost_per_million)+(expected_output_tokens*self.output_cost_per_million))/1_000_000
 def to_dict(self)->dict:return asdict(self)
class NoModelAvailableError(LookupError):pass
class ModelRegistry:
 FAILOVER={'local-private':('local-private',),'reasoning':('reasoning','balanced','fast'),'balanced':('balanced','fast'),'fast':('fast','balanced')}
 def __init__(self,models:Iterable[ModelSpec]=())->None:
  self._models={}; [self.register(m) for m in models]
 def register(self,model:ModelSpec)->None:
  if model.name in self._models:raise ValueError(f'Model already registered: {model.name}')
  self._models[model.name]=model
 def list(self,*,enabled_only:bool=False)->list[ModelSpec]:
  models=[m for m in self._models.values() if m.enabled or not enabled_only]; return sorted(models,key=lambda m:(-m.priority,m.name))
 def select(self,route:RouteDecision)->ModelSpec:
  required=set(route.required_capabilities)
  for tier in self.FAILOVER.get(route.tier,(route.tier,)):
   candidates=[m for m in self._models.values() if m.enabled and m.tier==tier and required.issubset(set(m.capabilities)) and (route.tier!='local-private' or m.privacy_boundary in {'tenant','customer','local'})]
   if candidates:return max(candidates,key=lambda m:(m.priority,m.name))
  raise NoModelAvailableError(f'No enabled model satisfies tier={route.tier!r} capabilities={sorted(required)}')
def _env(variable:str,*,name:str,tier:str,capabilities:tuple[str,...])->ModelSpec|None:
 model_id=os.getenv(variable)
 if not model_id:return None
 return ModelSpec(name,'openai',model_id,tier,capabilities,input_cost_per_million=float(os.getenv(f'{variable}_INPUT_COST_PER_MILLION','0')),output_cost_per_million=float(os.getenv(f'{variable}_OUTPUT_COST_PER_MILLION','0')),priority=100)
def default_model_registry()->ModelRegistry:
 basic=('text','structured-output'); models=[ModelSpec('local-private-default','prime-local','deterministic-private-v1','local-private',('private-inference','audit','text','structured-output'),'tenant',priority=20),ModelSpec('fast-default','prime-local','deterministic-fast-v1','fast',basic),ModelSpec('balanced-default','prime-local','deterministic-balanced-v1','balanced',basic),ModelSpec('reasoning-default','prime-local','deterministic-reasoning-v1','reasoning',('reasoning','structured-output','text'))]
 optional=(_env('PRIME_FAST_MODEL',name='fast-configured',tier='fast',capabilities=basic),_env('PRIME_BALANCED_MODEL',name='balanced-configured',tier='balanced',capabilities=basic),_env('PRIME_REASONING_MODEL',name='reasoning-configured',tier='reasoning',capabilities=('reasoning','structured-output','text')))
 models.extend(m for m in optional if m); return ModelRegistry(models)
