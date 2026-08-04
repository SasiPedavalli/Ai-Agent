import json
import tempfile
import unittest
from pathlib import Path

from prime_genesis.engine import evolve
from prime_genesis.providers.mock import DeterministicProvider


class EngineTests(unittest.TestCase):
    def test_evolution_cycle_selects_a_champion_and_persists_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            benchmark = root / "benchmark.jsonl"
            benchmark.write_text(
                json.dumps({
                    "case_id": "case-1",
                    "input_text": "pipeline latency breached SLA",
                    "expected_terms": ["pipeline latency", "SLA"],
                }) + "\n",
                encoding="utf-8",
            )
            report = evolve(
                provider=DeterministicProvider(),
                benchmark_path=benchmark,
                db_path=root / "prime.db",
            )
            self.assertTrue((root / "prime.db").exists())
            self.assertEqual(report.previous_champion, "prime-genesis-v0")
            self.assertGreaterEqual(len(report.scorecards), 2)
            self.assertTrue(report.selected_champion.startswith("prime-"))


if __name__ == "__main__":
    unittest.main()
