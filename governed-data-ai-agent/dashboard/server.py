from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app.agent import GovernedDataAIAgent
from app.audit import AuditStore
from app.models import DataSource

ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).resolve().parent / "static"
SAMPLE = ROOT / "data" / "sample_customer_events.csv"
RULES = ROOT / "config" / "data_quality_rules.json"
POLICY = ROOT / "config" / "governance_policy.json"
RUNTIME = ROOT / ".runtime"
RUNTIME.mkdir(exist_ok=True)

app = FastAPI(title="Governed Data & AI Operations Agent", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "agent": "Governed Data & AI Operations Agent", "version": "1.0.0"}


@app.get("/api/sample", response_class=PlainTextResponse)
def sample() -> str:
    return SAMPLE.read_text(encoding="utf-8")


@app.post("/api/analyze")
async def analyze(request: Request) -> dict:
    raw = await request.body()
    if not raw:
        raise HTTPException(status_code=400, detail="CSV body is required")
    if len(raw) > 2_000_000:
        raise HTTPException(status_code=413, detail="Demo accepts CSV files up to 2 MB")

    qp = request.query_params
    asset_name = qp.get("asset_name", "uploaded_asset").strip() or "uploaded_asset"
    owner = qp.get("owner", "data-platform@company.com").strip()
    domain = qp.get("domain", "customer-telemetry").strip() or "customer-telemetry"
    environment = qp.get("environment", "dev")
    if environment not in {"dev", "test", "prod"}:
        raise HTTPException(status_code=400, detail="environment must be dev, test, or prod")

    approved = qp.get("approved", "false").lower() == "true"
    lineage_registered = qp.get("lineage_registered", "false").lower() == "true"

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as tmp:
            tmp.write(raw)
            tmp_path = tmp.name

        source = DataSource(
            name=asset_name,
            path=tmp_path,
            owner=owner,
            domain=domain,
            environment=environment,
            approved=approved,
            lineage_registered=lineage_registered,
        )
        agent = GovernedDataAIAgent(
            policy=load_json(POLICY),
            audit_store=AuditStore(str(RUNTIME / "agent_audit.db")),
        )
        result = agent.run(source, load_json(RULES)).to_dict()
        result["source"]["path"] = f"upload://{asset_name}.csv"
        result["trace"]["input_output_traceability"]["source_path"] = result["source"]["path"]
        return result
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Agent could not analyze this CSV: {exc}") from exc
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
