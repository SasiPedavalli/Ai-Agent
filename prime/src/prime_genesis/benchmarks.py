from __future__ import annotations

import json
from pathlib import Path

from prime_genesis.models import BenchmarkCase


def load_cases(path: str | Path) -> list[BenchmarkCase]:
    cases: list[BenchmarkCase] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            payload = json.loads(line)
            try:
                cases.append(
                    BenchmarkCase(
                        case_id=payload["case_id"],
                        input_text=payload["input_text"],
                        expected_terms=tuple(payload.get("expected_terms", [])),
                        forbidden_terms=tuple(payload.get("forbidden_terms", [])),
                        domain=payload.get("domain", "general"),
                        tags=tuple(payload.get("tags", [])),
                    )
                )
            except KeyError as exc:
                raise ValueError(f"Missing field on line {line_number}: {exc}") from exc
    if not cases:
        raise ValueError(f"Benchmark contains no cases: {path}")
    return cases
