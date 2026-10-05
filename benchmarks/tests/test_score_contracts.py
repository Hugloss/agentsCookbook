from __future__ import annotations

import os
import unittest
from pathlib import Path

from benchmarks.__main__ import _validate_score_cli


ROOT = Path(__file__).resolve().parents[1]
GENERIC_SCORE_SCRIPTS = (
    ROOT / "suites/repository-intelligence/heldout-v1/score.py",
    ROOT / "suites/repository-intelligence/headroom-v1/score.py",
    ROOT / "suites/repository-intelligence/context-invariance-v1/score.py",
    ROOT / "suites/repository-intelligence/behavioral-v3/score.py",
    ROOT / "suites/repository-intelligence/behavioral-v4/score.py",
    ROOT / "suites/repository-intelligence/multidomain-v2/score.py",
)


class ScoreContractTests(unittest.TestCase):
    def test_generic_score_scripts_accept_exact_frozen_definition_contract(self) -> None:
        for script in GENERIC_SCORE_SCRIPTS:
            with self.subTest(script=script.parent.name):
                _validate_score_cli(script, os.environ)


if __name__ == "__main__":
    unittest.main()
