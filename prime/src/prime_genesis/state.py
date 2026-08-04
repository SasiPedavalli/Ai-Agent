from __future__ import annotations

import json
from pathlib import Path

from prime_genesis.models import AgentVersion, EvolutionReport, Scorecard, utc_now


STATE_SCHEMA_VERSION = 1


def load_champion_state(path: str | Path | None) -> AgentVersion | None:
    if path is None:
        return None
    state_path = Path(path)
    if not state_path.exists() or not state_path.read_text(encoding="utf-8").strip():
        return None
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    champion = payload.get("champion")
    return AgentVersion.from_dict(champion) if champion else None


def save_champion_state(
    path: str | Path,
    *,
    champion: AgentVersion,
    report: EvolutionReport,
    scorecard: Scorecard,
) -> None:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": STATE_SCHEMA_VERSION,
        "updated_at": utc_now(),
        "champion": champion.to_dict(),
        "latest_run": {
            "run_id": report.run_id,
            "previous_champion": report.previous_champion,
            "selected_champion": report.selected_champion,
            "promoted": report.promoted,
            "rollback_performed": report.rollback_performed,
            "provider_name": report.provider_name,
            "completed_at": report.completed_at,
        },
        "champion_scorecard": {
            "version_id": scorecard.version_id,
            "split": scorecard.split,
            "quality": scorecard.quality,
            "safety": scorecard.safety,
            "reliability": scorecard.reliability,
            "latency_ms": scorecard.latency_ms,
            "estimated_cost_usd": scorecard.estimated_cost_usd,
            "composite": scorecard.composite,
        },
    }
    state_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def append_history(path: str | Path, report: EvolutionReport) -> None:
    history_path = Path(path)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "run_id": report.run_id,
        "started_at": report.started_at,
        "completed_at": report.completed_at,
        "previous_champion": report.previous_champion,
        "selected_champion": report.selected_champion,
        "promoted": report.promoted,
        "rollback_performed": report.rollback_performed,
        "provider_name": report.provider_name,
        "candidate_count": max(0, len(report.scorecards) - 1),
        "decision_count": len(report.decisions),
        "canary_count": len(report.canaries),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(summary, sort_keys=True) + "\n")


def read_status(state_path: str | Path, history_path: str | Path | None = None) -> dict:
    path = Path(state_path)
    state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    history_count = 0
    if history_path is not None and Path(history_path).exists():
        history_count = sum(
            1 for line in Path(history_path).read_text(encoding="utf-8").splitlines() if line
        )
    return {
        "initialized": bool(state),
        "champion": state.get("champion"),
        "latest_run": state.get("latest_run"),
        "history_count": history_count,
    }
