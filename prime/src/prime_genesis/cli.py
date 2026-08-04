from __future__ import annotations

import argparse
import json
from pathlib import Path

from prime_genesis.canary import CanaryPolicy
from prime_genesis.engine import evolve
from prime_genesis.providers.mock import DeterministicProvider
from prime_genesis.runtime import PrimeRuntime
from prime_genesis.security import TenantContext
from prime_genesis.state import read_status
from prime_products.base import ProductRequest


def _provider(name: str, model: str | None):
    if name == "mock": return DeterministicProvider()
    if name == "openai":
        from prime_genesis.providers.openai_responses import OpenAIResponsesProvider
        return OpenAIResponsesProvider(model=model)
    raise ValueError(f"Unsupported provider: {name}")

def _context(args: argparse.Namespace) -> TenantContext:
    return TenantContext(args.tenant,args.actor,frozenset(r.strip() for r in args.roles.split(',') if r.strip()))
def _context_args(parser: argparse.ArgumentParser,roles: str="reader") -> None:
    parser.add_argument('--tenant',required=True); parser.add_argument('--actor',required=True); parser.add_argument('--roles',default=roles); parser.add_argument('--runtime-db',default='artifacts/runtime.db')

def build_parser() -> argparse.ArgumentParser:
    parser=argparse.ArgumentParser(prog='prime',description='PRIME evolution and product control plane'); subs=parser.add_subparsers(dest='command',required=True)
    p=subs.add_parser('evolve'); p.add_argument('--provider',choices=('mock','openai'),default='mock'); p.add_argument('--model'); p.add_argument('--benchmark',default='data/benchmarks.jsonl'); p.add_argument('--holdout',default='data/holdout.calibration.jsonl'); p.add_argument('--db',default='artifacts/prime.db'); p.add_argument('--state',default='state/champion.json'); p.add_argument('--history',default='state/evolution-history.jsonl'); p.add_argument('--json-report',default='artifacts/latest-report.json'); p.add_argument('--max-rounds',type=int,default=2); p.add_argument('--canary-traffic',type=float,default=.10)
    p=subs.add_parser('status'); p.add_argument('--state',default='state/champion.json'); p.add_argument('--history',default='state/evolution-history.jsonl'); p.add_argument('--json',action='store_true')
    p=subs.add_parser('products'); p.add_argument('--runtime-db',default='artifacts/runtime.db')
    p=subs.add_parser('run-product'); p.add_argument('product',choices=('guardian-x','genome','company-brain','digital-twin')); p.add_argument('--text',required=True); p.add_argument('--namespace',default='default'); p.add_argument('--sensitivity',default='standard'); p.add_argument('--max-cost-usd',type=float); p.add_argument('--latency-target-ms',type=int); p.add_argument('--json',action='store_true'); _context_args(p)
    p=subs.add_parser('memory-add'); p.add_argument('--namespace',default='default'); p.add_argument('--content',required=True); _context_args(p,'writer')
    p=subs.add_parser('memory-search'); p.add_argument('--query',required=True); p.add_argument('--namespace'); p.add_argument('--limit',type=int,default=10); _context_args(p)
    p=subs.add_parser('serve'); p.add_argument('--host',default='127.0.0.1'); p.add_argument('--port',type=int,default=8080)
    return parser

def _write(path:str|Path,payload:dict)->Path:
    out=Path(path); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8'); return out

def main()->int:
    args=build_parser().parse_args()
    if args.command=='evolve':
        report=evolve(provider=_provider(args.provider,args.model),benchmark_path=args.benchmark,holdout_path=args.holdout,db_path=args.db,state_path=args.state,history_path=args.history,max_mutation_rounds=args.max_rounds,canary_policy=CanaryPolicy(traffic_fraction=args.canary_traffic)); out=_write(args.json_report,report.to_dict()); print(f"Run: {report.run_id}\nSelected champion: {report.selected_champion}\nPromoted: {report.promoted}\nReport: {out}"); return 0
    if args.command=='status':
        status=read_status(args.state,args.history)
        if args.json: print(json.dumps(status,indent=2))
        elif not status['initialized']: print('PRIME has not completed an evolution run yet.')
        else: print(f"Champion: {status['champion']['version_id']}\nGeneration: {status['champion']['generation']}\nHistory entries: {status['history_count']}")
        return 0
    if args.command=='products':
        runtime=PrimeRuntime(args.runtime_db)
        try: print(json.dumps(runtime.list_products(),indent=2))
        finally: runtime.close()
        return 0
    if args.command=='run-product':
        runtime=PrimeRuntime(args.runtime_db)
        try:
            result=runtime.run_product(args.product,_context(args),ProductRequest(args.text,args.sensitivity,args.namespace,args.max_cost_usd,args.latency_target_ms))
            print(json.dumps(result.to_dict(),indent=2) if args.json else result.summary+'\n'+'\n'.join(f'- {x}' for x in result.findings))
        finally: runtime.close()
        return 0
    if args.command=='memory-add':
        runtime=PrimeRuntime(args.runtime_db)
        try: print(json.dumps(runtime.ingest_memory(_context(args),namespace=args.namespace,content=args.content).__dict__,indent=2))
        finally: runtime.close()
        return 0
    if args.command=='memory-search':
        runtime=PrimeRuntime(args.runtime_db)
        try: print(json.dumps([r.__dict__ for r in runtime.search_memory(_context(args),query=args.query,namespace=args.namespace,limit=args.limit)],indent=2))
        finally: runtime.close()
        return 0
    if args.command=='serve':
        try: import uvicorn
        except ImportError as exc: raise RuntimeError("Install the API extra: pip install -e '.[api]'") from exc
        uvicorn.run('prime_genesis.control_api:app',host=args.host,port=args.port,reload=False); return 0
    return 1
if __name__=='__main__': raise SystemExit(main())
