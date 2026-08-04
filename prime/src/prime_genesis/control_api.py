from __future__ import annotations

import os
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel, Field
except ImportError as exc:
    raise RuntimeError("Install the API extra: pip install -e '.[api]'") from exc

from prime_genesis.canary import CanaryPolicy
from prime_genesis.engine import evolve
from prime_genesis.providers.mock import DeterministicProvider
from prime_genesis.state import read_status
from prime_genesis.store import ExperimentStore


ROOT = Path(os.getenv("PRIME_ROOT", "."))
STATE_PATH = Path(os.getenv("PRIME_STATE_PATH", ROOT / "state/champion.json"))
HISTORY_PATH = Path(os.getenv("PRIME_HISTORY_PATH", ROOT / "state/evolution-history.jsonl"))
DB_PATH = Path(os.getenv("PRIME_DB_PATH", ROOT / "artifacts/prime.db"))
BENCHMARK_PATH = Path(os.getenv("PRIME_BENCHMARK_PATH", ROOT / "data/benchmarks.jsonl"))
HOLDOUT_PATH = Path(
    os.getenv("PRIME_HOLDOUT_PATH", ROOT / "data/holdout.calibration.jsonl")
)

app = FastAPI(title="PRIME Control Plane", version="0.2.0")


class EvolutionRequest(BaseModel):
    provider: str = Field(default="mock", pattern="^(mock|openai)$")
    model: str | None = None
    max_rounds: int = Field(default=2, ge=1, le=8)
    canary_traffic: float = Field(default=0.10, gt=0.0, le=0.50)


def _provider(name: str, model: str | None):
    if name == "mock":
        return DeterministicProvider()
    from prime_genesis.providers.openai_responses import OpenAIResponsesProvider

    return OpenAIResponsesProvider(model=model)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "prime-control-plane", "version": "0.2.0"}


@app.get("/api/status")
def status() -> dict:
    return read_status(STATE_PATH, HISTORY_PATH)


@app.get("/api/runs")
def runs(limit: int = 20) -> list[dict]:
    limit = min(max(limit, 1), 100)
    store = ExperimentStore(DB_PATH)
    try:
        return store.recent_runs(limit)
    finally:
        store.close()


@app.post("/api/evolve")
def run_evolution(request: EvolutionRequest) -> dict:
    if os.getenv("PRIME_API_EVOLUTION_ENABLED", "false").lower() != "true":
        raise HTTPException(
            status_code=403,
            detail=(
                "API-triggered evolution is disabled. "
                "Set PRIME_API_EVOLUTION_ENABLED=true explicitly."
            ),
        )
    report = evolve(
        provider=_provider(request.provider, request.model),
        benchmark_path=BENCHMARK_PATH,
        holdout_path=HOLDOUT_PATH,
        db_path=DB_PATH,
        state_path=STATE_PATH,
        history_path=HISTORY_PATH,
        max_mutation_rounds=request.max_rounds,
        canary_policy=CanaryPolicy(traffic_fraction=request.canary_traffic),
    )
    return report.to_dict()


DASHBOARD = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>PRIME Control Center</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
    body { margin:0; background:#080b12; color:#e9eefb; }
    main { max-width:1100px; margin:0 auto; padding:48px 24px; }
    h1 { font-size:44px; margin:0 0 8px; letter-spacing:-1.5px; }
    .sub { color:#9aa8c7; margin-bottom:32px; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px; }
    .card { background:#111827; border:1px solid #26324a; border-radius:18px; padding:20px; }
    .label { color:#8da0c6; font-size:12px; text-transform:uppercase; letter-spacing:1.2px; }
    .value { font-size:24px; font-weight:700; margin-top:8px; overflow-wrap:anywhere; }
    pre { white-space:pre-wrap; background:#0b1020; padding:18px; border-radius:14px; border:1px solid #26324a; }
    .ok { color:#78e6a3; }
  </style>
</head>
<body>
<main>
  <div class="label ok">Progressive Recursive Intelligence & Mutation Engine</div>
  <h1>PRIME Control Center</h1>
  <p class="sub">Governed daily evolution, protected evaluations, canary promotion, and rollback evidence.</p>
  <section class="grid">
    <div class="card"><div class="label">Champion</div><div id="champion" class="value">Loading…</div></div>
    <div class="card"><div class="label">Generation</div><div id="generation" class="value">—</div></div>
    <div class="card"><div class="label">Latest run</div><div id="run" class="value">—</div></div>
    <div class="card"><div class="label">Evolution history</div><div id="history" class="value">—</div></div>
  </section>
  <h2>Active policy</h2>
  <pre id="policy">Loading…</pre>
</main>
<script>
async function refresh() {
  const response = await fetch('/api/status');
  const status = await response.json();
  if (!status.initialized) {
    document.querySelector('#champion').textContent = 'Not initialized';
    document.querySelector('#policy').textContent = 'Run PRIME evolution to initialize state.';
    return;
  }
  const c = status.champion;
  document.querySelector('#champion').textContent = c.version_id;
  document.querySelector('#generation').textContent = c.generation;
  document.querySelector('#run').textContent = status.latest_run.run_id;
  document.querySelector('#history').textContent = status.history_count;
  document.querySelector('#policy').textContent = JSON.stringify({
    workflow_steps:c.workflow_steps,
    model_route:c.model_route,
    retrieval_policy:c.retrieval_policy,
    response_contract:c.response_contract
  }, null, 2);
}
refresh().catch(error => document.querySelector('#policy').textContent = error.toString());
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return DASHBOARD
