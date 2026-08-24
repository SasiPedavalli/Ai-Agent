from __future__ import annotations

import csv
import math
import statistics
from collections import Counter
from typing import Dict, List, Tuple

from .models import AnomalyFinding, QualityFinding


def load_csv(path: str) -> Tuple[List[str], List[Dict[str, str]]]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return reader.fieldnames or [], rows


def run_quality_checks(
    columns: List[str], rows: List[Dict[str, str]], rules: Dict
) -> Tuple[float, List[QualityFinding]]:
    findings: List[QualityFinding] = []
    total_checks = 0
    passed_checks = 0

    required = rules.get("required_columns", [])
    for col in required:
        total_checks += 1
        ok = col in columns
        passed_checks += int(ok)
        findings.append(
            QualityFinding(
                check=f"required_column:{col}",
                status="PASS" if ok else "FAIL",
                details="Column present" if ok else "Required column missing",
                severity="high" if not ok else "low",
            )
        )

    max_null_rate = float(rules.get("max_null_rate", 0.05))
    for col in columns:
        total_checks += 1
        if not rows:
            null_rate = 1.0
        else:
            nulls = sum(1 for r in rows if r.get(col, "").strip() in ("", "null", "None"))
            null_rate = nulls / len(rows)
        ok = null_rate <= max_null_rate
        passed_checks += int(ok)
        findings.append(
            QualityFinding(
                check=f"null_rate:{col}",
                status="PASS" if ok else "FAIL",
                details=f"null_rate={null_rate:.2%}, threshold={max_null_rate:.2%}",
                severity="high" if not ok else "low",
            )
        )

    if rules.get("unique_key"):
        key = rules["unique_key"]
        total_checks += 1
        values = [r.get(key, "") for r in rows]
        dupes = [v for v, c in Counter(values).items() if v and c > 1]
        ok = not dupes
        passed_checks += int(ok)
        findings.append(
            QualityFinding(
                check=f"unique_key:{key}",
                status="PASS" if ok else "FAIL",
                details="No duplicates" if ok else f"Duplicate keys: {dupes[:5]}",
                severity="high" if not ok else "low",
            )
        )

    for col, allowed in rules.get("allowed_values", {}).items():
        total_checks += 1
        bad = sorted({r.get(col, "") for r in rows if r.get(col, "") not in allowed})
        ok = not bad
        passed_checks += int(ok)
        findings.append(
            QualityFinding(
                check=f"allowed_values:{col}",
                status="PASS" if ok else "FAIL",
                details="All values allowed" if ok else f"Unexpected values: {bad[:5]}",
                severity="medium" if not ok else "low",
            )
        )

    score = 100.0 if total_checks == 0 else (passed_checks / total_checks) * 100.0
    return round(score, 2), findings


def detect_numeric_anomalies(
    rows: List[Dict[str, str]], numeric_columns: List[str], z_threshold: float = 3.0
) -> List[AnomalyFinding]:
    anomalies: List[AnomalyFinding] = []
    for col in numeric_columns:
        parsed = []
        for idx, row in enumerate(rows, start=2):
            try:
                parsed.append((idx, float(row.get(col, ""))))
            except (ValueError, TypeError):
                continue
        values = [v for _, v in parsed]
        if len(values) < 3:
            continue
        mean = statistics.mean(values)
        std = statistics.pstdev(values)
        if math.isclose(std, 0.0):
            continue
        for row_number, value in parsed:
            z = abs((value - mean) / std)
            if z >= z_threshold:
                anomalies.append(
                    AnomalyFinding(
                        column=col,
                        value=value,
                        row_number=row_number,
                        z_score=round(z, 3),
                        severity="high" if z >= z_threshold + 1 else "medium",
                    )
                )
    return anomalies
