from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from prime_genesis.state import read_status


class StateTests(unittest.TestCase):
    def test_uninitialized_status_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            status = read_status(Path(temp_dir) / "missing.json")
            self.assertFalse(status["initialized"])
            self.assertIsNone(status["champion"])


if __name__ == "__main__":
    unittest.main()
