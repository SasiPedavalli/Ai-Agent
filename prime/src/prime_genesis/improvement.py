from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from prime_genesis.models import utc_now
from prime_genesis.security import TenantContext, require_role


@dataclass(frozen=True)
class EvaluationProposal:
    proposal_id: str
    tenant_id: str
    product: str
    source_feedback_id: str
    issue_summary: str
    expected_behavior: str
    failure_class: str
    created_at: str


class FeedbackProposalBuilder:
    """Turns low-rating feedback into human-reviewed evaluation proposals.

    Proposals never enter protected or public benchmarks automatically.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row

    def close(self) -> None:
        self.connection.close()

    def build(
        self,
        context: TenantContext,
        *,
        maximum_rating: int = 2,
        destination: str | Path | None = None,
    ) -> list[EvaluationProposal]:
        require_role(context, "admin", "evaluator")
        if maximum_rating < 1 or maximum_rating > 5:
            raise ValueError("maximum_rating must be between 1 and 5")
        table = self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='feedback'"
        ).fetchone()
        if table is None:
            return []
        rows = self.connection.execute(
            "SELECT feedback_id, product, rating, comment, metadata_json, created_at "
            "FROM feedback WHERE tenant_id=? AND rating<=? ORDER BY created_at",
            (context.tenant_id, maximum_rating),
        ).fetchall()
        proposals: list[EvaluationProposal] = []
        for row in rows:
            metadata: dict[str, Any] = json.loads(row["metadata_json"])
            issue = row["comment"].strip() or str(
                metadata.get("issue_summary", "Low-rated product result requires review.")
            )
            expected = str(
                metadata.get(
                    "expected_behavior",
                    "Define an evidence-based expected result before adding this case to an evaluation suite.",
                )
            )
            failure_class = str(metadata.get("failure_class", "unspecified"))
            digest = hashlib.sha256(
                f"{context.tenant_id}|{row['feedback_id']}|{issue}|{expected}".encode()
            ).hexdigest()[:16]
            proposals.append(
                EvaluationProposal(
                    proposal_id=f"eval-proposal-{digest}",
                    tenant_id=context.tenant_id,
                    product=row["product"],
                    source_feedback_id=row["feedback_id"],
                    issue_summary=issue,
                    expected_behavior=expected,
                    failure_class=failure_class,
                    created_at=utc_now(),
                )
            )
        if destination is not None:
            path = Path(destination)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "".join(json.dumps(asdict(item), sort_keys=True) + "\n" for item in proposals),
                encoding="utf-8",
            )
        return proposals
