from __future__ import annotations

import unittest

from prime_genesis.governance import decide
from prime_genesis.models import Scorecard


def scorecard(
    version_id: str,
    *,
    composite: float,
    safety: float = 1.0,
    quality: float = 0.8,
) -> Scorecard:
    return Scorecard(
        version_id=version_id,
        split="public",
        quality=quality,
        safety=safety,
        reliability=0.8,
        latency_ms=100.0,
        estimated_cost_usd=0.01,
        composite=composite,
        results=(),
    )


class GovernanceTests(unittest.TestCase):
    def test_better_safe_candidate_is_promoted(self) -> None:
        decision = decide(
            scorecard("champion", composite=0.80),
            scorecard("candidate", composite=0.84),
        )
        self.assertTrue(decision.approved)

    def test_unsafe_candidate_is_rejected(self) -> None:
        decision = decide(
            scorecard("champion", composite=0.80),
            scorecard("candidate", composite=0.90, safety=0.0),
        )
        self.assertFalse(decision.approved)
        self.assertIn("safety gate", decision.reason)


if __name__ == "__main__":
    unittest.main()
