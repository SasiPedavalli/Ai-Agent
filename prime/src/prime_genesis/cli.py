from __future__ import annotations
import argparse,json,os
from pathlib import Path
from prime_genesis.auth import issue_token,verify_token
from prime_genesis.backup import backup_sqlite
from prime_genesis.canary import CanaryPolicy
from prime_genesis.engine import evolve
from prime_genesis.providers.mock import DeterministicProvider
from prime_genesis.runtime import PrimeRuntime
from prime_genesis.security import TenantContext
from prime_genesis.state import read_status
from prime_products.base import ProductRequest
def _provider(name,model):
 if name=='mock':return DeterministicProvider()
 from prime_genesis.providers.openai_responses import OpenAIResponsesProvider
 return OpenAIResponsesProvider(model=model)
def _ctx(a):return TenantContext(a.tenant,a.actor,frozenset(r.strip() for r in a.roles.split(',') if r.strip()))
def _ca(p,roles='reader'):p.add_argument('--tenant',required=True);p.add_argument('--actor',required=True);p.add_argument('--roles',default=roles);p.add_argument('--runtime-db',default='artifacts/runtime.db')
def build_parser():
 x=argparse.ArgumentParser(prog='prime');s=x.add_subparsers(dest='command',required=True)
 p=s.add_parser('evolve');p.add_argument('--provider',choices=('mock','openai'),default='mock');p.add_argument('--model');p.add_argument('--benchmark',default='data/benchmarks.jsonl');p.add_argument('--holdout',default='data/holdout.calibration.jsonl');p.add_argument('--db',default='artifacts/prime.db');p.add_argument('--state',default='state/champion.json');p.add_argument('--history',default='state/evolution-history.jsonl');p.add_argument('--json-report',default='artifacts/latest-report.json');p.add_argument('--max-rounds',type=int,default=2);p.add_argument('--canary-traffic',type=float,default=.1)
 p=s.add_parser('status');p.add_argument('--state',default='state/champion.json');p.add_argument('--history',default='state/evolution-history.jsonl');p.add_argument('--json',action='store_true')
 for name in ('products','models'):p=s.add_parser(name);p.add_argument('--runtime-db',default='artifacts/runtime.db')
 p=s.add_parser('run-product');p.add_argument('product',choices=('guardian-x','genome','company-brain','digital-twin'));p.add_argument('--text',required=True);p.add_argument('--namespace',default='default');p.add_argument('--sensitivity',default='standard');p.add_argument('--max-cost-usd',type=float);p.add_argument('--latency-target-ms',type=int);p.add_argument('--json',action='store_true');_ca(p)
 p=s.add_parser('memory-add');p.add_argument('--namespace',default='default');p.add_argument('--content',required=True);_ca(p,'writer')
 p=s.add_parser('memory-search');p.add_argument('--query',required=True);p.add_argument('--namespace');p.add_argument('--limit',type=int,default=10);_ca(p)
 p=s.add_parser('document-add');p.add_argument('--namespace',default='default');p.add_argument('--title',required=True);p.add_argument('--content',required=True);_ca(p,'writer')
 p=s.add_parser('document-search');p.add_argument('--query',required=True);p.add_argument('--namespace');p.add_argument('--limit',type=int,default=5);_ca(p)
 p=s.add_parser('budget-set');p.add_argument('--limit-usd',type=float,required=True);_ca(p,'admin')
 p=s.add_parser('budget-status');_ca(p)
 p=s.add_parser('token-issue');p.add_argument('--tenant',required=True);p.add_argument('--actor',required=True);p.add_argument('--roles',default='reader');p.add_argument('--ttl',type=int,default=3600)
 p=s.add_parser('token-verify');p.add_argument('--token',required=True)
 p=s.add_parser('backup');p.add_argument('--source',default='artifacts/runtime.db');p.add_argument('--destination',required=True)
 p=s.add_parser('serve');p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=8080)
 return x
def main():
 a=build_parser().parse_args()
 if a.command=='evolve':
  r=evolve(provider=_provider(a.provider,a.model),benchmark_path=a.benchmark,holdout_path=a.holdout,db_path=a.db,state_path=a.state,history_path=a.history,max_mutation_rounds=a.max_rounds,canary_policy=CanaryPolicy(traffic_fraction=a.canary_traffic));Path(a.json_report).parent.mkdir(parents=True,exist_ok=True);Path(a.json_report).write_text(json.dumps(r.to_dict(),indent=2)+'\n');print(r.selected_champion);return 0
 if a.command=='status':print(json.dumps(read_status(a.state,a.history),indent=2));return 0
 if a.command=='token-issue':print(issue_token(os.getenv('PRIME_AUTH_SECRET',''),_ctx(a),ttl_seconds=a.ttl));return 0
 if a.command=='token-verify':print(json.dumps(verify_token(os.getenv('PRIME_AUTH_SECRET',''),a.token).__dict__,indent=2));return 0
 if a.command=='backup':print(json.dumps(backup_sqlite(a.source,a.destination).__dict__,indent=2));return 0
 if a.command=='serve':
  import uvicorn;uvicorn.run('prime_genesis.control_api:app',host=a.host,port=a.port);return 0
 rt=PrimeRuntime(a.runtime_db)
 try:
  if a.command=='products':print(json.dumps(rt.list_products(),indent=2))
  elif a.command=='models':print(json.dumps(rt.list_models(),indent=2))
  elif a.command=='run-product':print(json.dumps(rt.run_product(a.product,_ctx(a),ProductRequest(a.text,a.sensitivity,a.namespace,a.max_cost_usd,a.latency_target_ms)).to_dict(),indent=2))
  elif a.command=='memory-add':print(json.dumps(rt.ingest_memory(_ctx(a),namespace=a.namespace,content=a.content).__dict__,indent=2))
  elif a.command=='memory-search':print(json.dumps([r.__dict__ for r in rt.search_memory(_ctx(a),query=a.query,namespace=a.namespace,limit=a.limit)],indent=2))
  elif a.command=='document-add':print(json.dumps(rt.ingest_document(_ctx(a),namespace=a.namespace,title=a.title,content=a.content).__dict__,indent=2))
  elif a.command=='document-search':print(json.dumps([{'document':h.document.__dict__,'score':h.score,'matched_terms':h.matched_terms} for h in rt.search_documents(_ctx(a),query=a.query,namespace=a.namespace,limit=a.limit)],indent=2))
  elif a.command=='budget-set':rt.budgets.set_daily_limit(_ctx(a),a.limit_usd);print(json.dumps(rt.budgets.authorize(_ctx(a),0).__dict__,indent=2))
  elif a.command=='budget-status':print(json.dumps(rt.budgets.authorize(_ctx(a),0).__dict__,indent=2))
  return 0
 finally:rt.close()
if __name__=='__main__':raise SystemExit(main())
