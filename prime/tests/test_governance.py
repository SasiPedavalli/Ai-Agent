import unittest

from prime_genesis.governance import decide
from prime_genesis.models import Scorecard


def score(version: str, composite: float, quality: float = 0.8, safety: float = 1.0, reliability: float = 0.8) -> Scorecard:
    return Scorecard(
        version_id=version,
        quality=quality,
        safety=safety,
        reliability=reliability,
        latency_ms=10.0,
        estimated_cost_usd=0.0,
        composite=composite,
        results=(),
    )


class GovernanceTests(unittest.TestCase):
    def test_better_safe_candidate_is_promoted(self) -> None:
        decision = decide(score("champion", 0.80), score("challenger", 0.83, quality=0.82, reliability=0.82))
        self.assertTrue(decision.approved)

    def test_unsafe_candidate_is_rejected(self) -> None:
        decision = decide(score("champion", 0.80), score("challenger", 0.90, safety=0.8))
        self.assertFalse(decision.approved)
        self.assertIn("safety gate", decision.reason)


if __name__ == "__main__":
    unittest.main()
