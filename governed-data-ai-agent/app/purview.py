from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Protocol


class PurviewGateway(Protocol):
    def publish_governance_result(self, asset_name: str, payload: Dict) -> None: ...


class MockPurviewGateway:
    """Local demo adapter that mirrors the boundary used for Microsoft Purview.

    The default demo intentionally avoids pretending to call a live Purview tenant.
    Swap this adapter for your organization's authenticated Purview SDK/REST client.
    """

    def __init__(self, output_path: str = "purview_publish_log.jsonl") -> None:
        self.output_path = Path(output_path)

    def publish_governance_result(self, asset_name: str, payload: Dict) -> None:
        record = {
            "asset_name": asset_name,
            "classifications": payload["metadata"]["classifications"],
            "sensitivity": payload["metadata"]["sensitivity"],
            "quality_score": payload["quality_score"],
            "policy_decision": payload["policy"]["decision"],
            "run_id": payload["run_id"],
            "input_hash": payload["input_hash"],
            "output_hash": payload["output_hash"],
        }
        with self.output_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")
