from __future__ import annotations

import unittest

from prime_genesis.canary import simulate_canary
from prime_genesis.models import Scorecard


def card(version: str, *, quality: float, safety: float, reliability: float) -> Scorecard:
    return Scorecard(
        version_id=version,
        split="holdout",
        quality=quality,
        safety=safety,
        reliability=reliability,
        latency_ms=100.0,
        estimated_cost_usd=0.0,
        composite=0.9,
        results=(),
    )


class CanaryTests(unittest.TestCase):
    def test_canary_rolls_back_unsafe_candidate(self) -> None:
        result = simulate_canary(
            card("champion", quality=0.9, safety=1.0, reliability=0.9),
            card("challenger", quality=0.95, safety=0.0, reliability=0.95),
        )
        self.assertFalse(result.passed)
        self.assertTrue(result.rollback_required)
        self.assertIn("Rollback", result.reason)


if __name__ == "__main__":
    unittest.main()
