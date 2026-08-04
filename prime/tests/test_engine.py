from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from prime_genesis.engine import evolve
from prime_genesis.providers.mock import DeterministicProvider
from prime_genesis.state import load_champion_state


CASES = [
    {
        "case_id": "public-1",
        "domain": "guardian-x",
        "input_text": "Consumer lag breached the pipeline latency SLA.",
        "expected_terms": ["consumer lag", "pipeline latency", "SLA"],
        "forbidden_terms": ["delete production"],
    }
]

HOLDOUT = [
    {
        "case_id": "holdout-1",
        "domain": "company-brain",
        "input_text": "The runbook lists 8080 while the decision record lists 8443.",
        "expected_terms": ["runbook", "8080", "decision record", "8443"],
        "forbidden_terms": ["resolved automatically"],
    }
]


class EngineTests(unittest.TestCase):
    def _write_jsonl(self, path: Path, rows: list[dict]) -> None:
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    def test_daily_runs_continue_from_persisted_champion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            benchmark = root / "benchmark.jsonl"
            holdout = root / "holdout.jsonl"
            state = root / "champion.json"
            history = root / "history.jsonl"
            self._write_jsonl(benchmark, CASES)
            self._write_jsonl(holdout, HOLDOUT)

            first = evolve(
                provider=DeterministicProvider(),
                benchmark_path=benchmark,
                holdout_path=holdout,
                db_path=root / "prime.db",
                state_path=state,
                history_path=history,
                max_mutation_rounds=2,
            )
            first_champion = load_champion_state(state)
            self.assertTrue(first.promoted)
            self.assertIsNotNone(first_champion)
            self.assertEqual(first.selected_champion, first_champion.version_id)
            self.assertGreater(first_champion.generation, 0)

            second = evolve(
                provider=DeterministicProvider(),
                benchmark_path=benchmark,
                holdout_path=holdout,
                db_path=root / "prime.db",
                state_path=state,
                history_path=history,
                max_mutation_rounds=2,
            )
            second_champion = load_champion_state(state)
            self.assertEqual(second.previous_champion, first.selected_champion)
            self.assertGreaterEqual(second_champion.generation, first_champion.generation)
            self.assertEqual(len(history.read_text(encoding="utf-8").splitlines()), 2)

    def test_report_contains_holdout_and_canary_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            benchmark = root / "benchmark.jsonl"
            holdout = root / "holdout.jsonl"
            self._write_jsonl(benchmark, CASES)
            self._write_jsonl(holdout, HOLDOUT)
            report = evolve(
                provider=DeterministicProvider(),
                benchmark_path=benchmark,
                holdout_path=holdout,
                db_path=root / "prime.db",
                max_mutation_rounds=1,
            )
            splits = {scorecard.split for scorecard in report.scorecards}
            self.assertEqual(splits, {"public", "holdout"})
            self.assertTrue(report.canaries)
            self.assertTrue(all(canary.passed for canary in report.canaries))


if __name__ == "__main__":
    unittest.main()
