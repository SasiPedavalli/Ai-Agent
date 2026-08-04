from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Any

try:
    from fastapi import Depends, FastAPI, Header, HTTPException
    from fastapi.responses import HTMLResponse, JSONResponse
    from pydantic import BaseModel, Field
except ImportError as exc:
    raise RuntimeError("Install the API extra: pip install -e '.[api]'") from exc

from prime_genesis.audit import TenantAuditExporter
from prime_genesis.auth import AuthenticationError, verify_token
from prime_genesis.budget import BudgetExceededError
from prime_genesis.canary import CanaryPolicy
from prime_genesis.engine import evolve
from prime_genesis.improvement import FeedbackProposalBuilder
from prime_genesis.maintenance import RuntimeMaintenance
from prime_genesis.providers.mock import DeterministicProvider
from prime_genesis.rate_limit import RateLimitExceededError
from prime_genesis.readiness import evaluate_readiness
from prime_genesis.runtime import PrimeRuntime
from prime_genesis.security import AuthorizationError, TenantContext
from prime_genesis.state import read_status
from prime_genesis.store import ExperimentStore
from prime_products.base import ProductRequest

ROOT = Path(os.getenv("PRIME_ROOT", "."))
STATE_PATH = Path(os.getenv("PRIME_STATE_PATH", ROOT / "state/champion.json"))
HISTORY_PATH = Path(os.getenv("PRIME_HISTORY_PATH", ROOT / "state/evolution-history.jsonl"))
DB_PATH = Path(os.getenv("PRIME_DB_PATH", ROOT / "artifacts/prime.db"))
RUNTIME_DB_PATH = Path(os.getenv("PRIME_RUNTIME_DB_PATH", ROOT / "artifacts/runtime.db"))
BENCHMARK_PATH = Path(os.getenv("PRIME_BENCHMARK_PATH", ROOT / "data/benchmarks.jsonl"))
HOLDOUT_PATH = Path(os.getenv("PRIME_HOLDOUT_PATH", ROOT / "data/holdout.calibration.jsonl"))

app = FastAPI(title="PRIME Control Plane", version="1.0.0")


class EvolutionRequest(BaseModel):
    provider: str = Field(default="mock", pattern="^(mock|openai)$")
    model: str | None = None
    max_rounds: int = Field(default=2, ge=1, le=8)
    canary_traffic: float = Field(default=0.1, gt=0, le=0.5)


class ProductRunRequest(BaseModel):
    text: str = Field(min_length=1)
    sensitivity: str = "standard"
    namespace: str = "default"
    max_cost_usd: float | None = Field(default=None, ge=0)
    latency_target_ms: int | None = Field(default=None, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryWriteRequest(BaseModel):
    namespace: str = "default"
    content: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentWriteRequest(BaseModel):
    namespace: str = "default"
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BudgetWriteRequest(BaseModel):
    daily_limit_usd: float = Field(ge=0)


class FeedbackRequest(BaseModel):
    product: str
    run_id: str
    rating: int = Field(ge=1, le=5)
    comment: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class MaintenanceRequest(BaseModel):
    runtime_event_days: int = Field(default=30, ge=1, le=3650)
    feedback_days: int = Field(default=365, ge=1, le=3650)


def request_context(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    tenant: Annotated[str | None, Header(alias="X-Prime-Tenant")] = None,
    actor: Annotated[str | None, Header(alias="X-Prime-Actor")] = None,
    roles: Annotated[str, Header(alias="X-Prime-Roles")] = "reader",
) -> TenantContext:
    mode = os.getenv("PRIME_AUTH_MODE", "local").lower()
    if mode == "hmac":
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Bearer token required")
        try:
            return verify_token(
                os.getenv("PRIME_AUTH_SECRET", ""), authorization[7:]
            ).to_context()
        except AuthenticationError as exc:
            raise HTTPException(401, str(exc)) from exc
    if mode != "local":
        raise HTTPException(500, "Unsupported PRIME_AUTH_MODE")
    if not tenant or not actor:
        raise HTTPException(401, "Local mode requires X-Prime-Tenant and X-Prime-Actor")
    try:
        return TenantContext(
            tenant,
            actor,
            frozenset(item.strip() for item in roles.split(",") if item.strip()),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


def _runtime() -> PrimeRuntime:
    return PrimeRuntime(RUNTIME_DB_PATH)


def _rate(runtime: PrimeRuntime, context: TenantContext, operation: str) -> None:
    decision = runtime.rate_limits.consume(
        context,
        operation=operation,
        limit=int(os.getenv("PRIME_RATE_LIMIT_PER_MINUTE", "60")),
    )
    if not decision.allowed:
        raise RateLimitExceededError(
            f"Rate limit exceeded; retry after {decision.reset_at}"
        )


def _provider(name: str, model: str | None):
    if name == "mock":
        return DeterministicProvider()
    from prime_genesis.providers.openai_responses import OpenAIResponsesProvider

    return OpenAIResponsesProvider(model=model)


def _require(context: TenantContext, *roles: str) -> None:
    if not context.has_role(*roles):
        raise HTTPException(403, f"One of roles {sorted(set(roles))} is required")


@app.exception_handler(AuthorizationError)
def authorization_error(_request, exc: AuthorizationError):
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(BudgetExceededError)
def budget_error(_request, exc: BudgetExceededError):
    return JSONResponse(status_code=402, content={"detail": str(exc)})


@app.exception_handler(RateLimitExceededError)
def rate_error(_request, exc: RateLimitExceededError):
    return JSONResponse(status_code=429, content={"detail": str(exc)})


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "prime-control-plane",
        "version": "1.0.0",
        "auth_mode": os.getenv("PRIME_AUTH_MODE", "local"),
    }


@app.get("/ready")
def ready() -> dict[str, Any]:
    report = evaluate_readiness(
        state_path=STATE_PATH,
        runtime_db_path=RUNTIME_DB_PATH,
    )
    if not report.ready:
        raise HTTPException(status_code=503, detail=report.to_dict())
    return report.to_dict()


@app.get("/api/status")
def status() -> dict[str, Any]:
    return read_status(STATE_PATH, HISTORY_PATH)


@app.get("/api/runs")
def runs(limit: int = 20) -> list[dict[str, Any]]:
    store = ExperimentStore(DB_PATH)
    try:
        return store.recent_runs(min(max(limit, 1), 100))
    finally:
        store.close()


@app.post("/api/evolve")
def run_evolution(
    request: EvolutionRequest,
    context: Annotated[TenantContext, Depends(request_context)],
) -> dict[str, Any]:
    _require(context, "admin")
    if os.getenv("PRIME_API_EVOLUTION_ENABLED", "false").lower() != "true":
        raise HTTPException(403, "API-triggered evolution is disabled")
    return evolve(
        provider=_provider(request.provider, request.model),
        benchmark_path=BENCHMARK_PATH,
        holdout_path=HOLDOUT_PATH,
        db_path=DB_PATH,
        state_path=STATE_PATH,
        history_path=HISTORY_PATH,
        max_mutation_rounds=request.max_rounds,
        canary_policy=CanaryPolicy(traffic_fraction=request.canary_traffic),
    ).to_dict()


@app.get("/api/products")
def products() -> list[dict[str, str]]:
    runtime = _runtime()
    try:
        return runtime.list_products()
    finally:
        runtime.close()


@app.get("/api/models")
def models() -> list[dict[str, Any]]:
    runtime = _runtime()
    try:
        return runtime.list_models()
    finally:
        runtime.close()


@app.post("/api/products/{product}/run")
def run_product(
    product: str,
    request: ProductRunRequest,
    context: Annotated[TenantContext, Depends(request_context)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any]:
    runtime = _runtime()
    operation = f"product:{product}"
    try:
        _rate(runtime, context, operation)
        if idempotency_key:
            cached = runtime.idempotency.get(
                context, operation=operation, key=idempotency_key
            )
            if cached is not None:
                return cached
        result = runtime.run_product(
            product,
            context,
            ProductRequest(
                request.text,
                request.sensitivity,
                request.namespace,
                request.max_cost_usd,
                request.latency_target_ms,
                request.metadata,
            ),
        ).to_dict()
        if idempotency_key:
            runtime.idempotency.put(
                context,
                operation=operation,
                key=idempotency_key,
                response=result,
            )
        return result
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    finally:
        runtime.close()


@app.post("/api/memory")
def memory_write(
    request: MemoryWriteRequest,
    context: Annotated[TenantContext, Depends(request_context)],
) -> dict[str, Any]:
    runtime = _runtime()
    try:
        _rate(runtime, context, "memory-write")
        return asdict(
            runtime.ingest_memory(
                context,
                namespace=request.namespace,
                content=request.content,
                metadata=request.metadata,
            )
        )
    finally:
        runtime.close()


@app.get("/api/memory/search")
def memory_search(
    query: str,
    context: Annotated[TenantContext, Depends(request_context)],
    namespace: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    runtime = _runtime()
    try:
        _rate(runtime, context, "memory-search")
        return [
            asdict(item)
            for item in runtime.search_memory(
                context, query=query, namespace=namespace, limit=limit
            )
        ]
    finally:
        runtime.close()


@app.post("/api/documents")
def document_write(
    request: DocumentWriteRequest,
    context: Annotated[TenantContext, Depends(request_context)],
) -> dict[str, Any]:
    runtime = _runtime()
    try:
        _rate(runtime, context, "document-write")
        return asdict(
            runtime.ingest_document(
                context,
                namespace=request.namespace,
                title=request.title,
                content=request.content,
                metadata=request.metadata,
            )
        )
    finally:
        runtime.close()


@app.get("/api/documents/search")
def document_search(
    query: str,
    context: Annotated[TenantContext, Depends(request_context)],
    namespace: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    runtime = _runtime()
    try:
        _rate(runtime, context, "document-search")
        return [
            {
                "document": asdict(hit.document),
                "score": hit.score,
                "matched_terms": hit.matched_terms,
            }
            for hit in runtime.search_documents(
                context, query=query, namespace=namespace, limit=limit
            )
        ]
    finally:
        runtime.close()


@app.post("/api/budget")
def set_budget(
    request: BudgetWriteRequest,
    context: Annotated[TenantContext, Depends(request_context)],
) -> dict[str, Any]:
    runtime = _runtime()
    try:
        runtime.budgets.set_daily_limit(context, request.daily_limit_usd)
        return asdict(runtime.budgets.authorize(context, 0))
    finally:
        runtime.close()


@app.get("/api/budget")
def budget(
    context: Annotated[TenantContext, Depends(request_context)],
) -> dict[str, Any]:
    runtime = _runtime()
    try:
        return asdict(runtime.budgets.authorize(context, 0))
    finally:
        runtime.close()


@app.post("/api/feedback")
def feedback(
    request: FeedbackRequest,
    context: Annotated[TenantContext, Depends(request_context)],
) -> dict[str, Any]:
    runtime = _runtime()
    try:
        _rate(runtime, context, "feedback")
        return asdict(
            runtime.record_feedback(
                context,
                product=request.product,
                run_id=request.run_id,
                rating=request.rating,
                comment=request.comment,
                metadata=request.metadata,
            )
        )
    finally:
        runtime.close()


@app.get("/api/audit")
def audit_export(
    context: Annotated[TenantContext, Depends(request_context)],
) -> dict[str, Any]:
    _require(context, "admin", "auditor")
    exporter = TenantAuditExporter(RUNTIME_DB_PATH)
    try:
        return asdict(exporter.export(context))
    finally:
        exporter.close()


@app.get("/api/evaluation-proposals")
def evaluation_proposals(
    context: Annotated[TenantContext, Depends(request_context)],
    maximum_rating: int = 2,
) -> list[dict[str, Any]]:
    _require(context, "admin", "evaluator")
    builder = FeedbackProposalBuilder(RUNTIME_DB_PATH)
    try:
        return [
            asdict(item)
            for item in builder.build(context, maximum_rating=maximum_rating)
        ]
    finally:
        builder.close()


@app.post("/api/maintenance")
def maintenance(
    request: MaintenanceRequest,
    context: Annotated[TenantContext, Depends(request_context)],
) -> dict[str, Any]:
    _require(context, "admin")
    manager = RuntimeMaintenance(RUNTIME_DB_PATH)
    try:
        return asdict(
            manager.purge(
                runtime_event_days=request.runtime_event_days,
                feedback_days=request.feedback_days,
            )
        )
    finally:
        manager.close()


DASHBOARD = """<!doctype html><html><head><title>PRIME</title><style>body{font-family:system-ui;background:#080b12;color:#e9eefb;max-width:1000px;margin:auto;padding:48px}pre{background:#111827;padding:20px;border-radius:16px}</style></head><body><h1>PRIME 1.0 Control Center</h1><p>Governed evolution, tenant products, readiness, audit, and operations.</p><pre id='data'>Loading</pre><script>Promise.all(['/api/status','/api/products','/api/models','/ready'].map(x=>fetch(x).then(r=>r.json()))).then(([status,products,models,readiness])=>data.textContent=JSON.stringify({status,products,models,readiness},null,2)).catch(e=>data.textContent=e)</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return DASHBOARD
