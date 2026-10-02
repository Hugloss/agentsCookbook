from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from benchmarks.diagnostic import DiagnosticError, prepare_diagnostic_suite
from benchmarks.harness.oracle_reviews import OracleReviewError, validate_oracle_reviews
from benchmarks.harness.suite import SuiteError, load_suite


SOURCE = Path(__file__).resolve().parents[1] / "suites/repository-intelligence/heldout-v1"


class ReviewAndDiagnosticTests(unittest.TestCase):
    def test_required_review_cannot_be_bypassed_by_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "suite"
            shutil.copytree(SOURCE, copy)
            (copy / "qualification/oracle-reviews.json").unlink()
            with self.assertRaisesRegex(SuiteError, "oracle review evidence is missing"):
                load_suite(copy)

    def test_first_review_is_recorded_but_does_not_approve_campaign(self) -> None:
        result = validate_oracle_reviews(load_suite(SOURCE), require_complete=False)
        self.assertEqual(result["first_reviewed_tasks"], 12)
        self.assertEqual(result["approved_tasks"], 0)
        with self.assertRaisesRegex(OracleReviewError, "incomplete"):
            validate_oracle_reviews(load_suite(SOURCE), require_complete=True)

    def test_diagnostic_is_separate_and_has_ten_paired_replicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            score = root / "score.json"
            score.write_text(json.dumps({
                "campaign_qualification": {"status": "QUALIFIED"},
                "languages": {},
            }), encoding="utf-8")
            target = root / "diagnostic"
            prepare_diagnostic_suite(
                source_suite=SOURCE, score_path=score, destination=target,
                include_tasks={"locate-repository-content-identity"},
            )
            suite = load_suite(target)
            self.assertEqual(len(suite.trial_definitions()), 60)
            self.assertEqual(suite.experiment["tasks"], ["locate-repository-content-identity"])
            self.assertEqual(suite.experiment["oracle_reviews"],
                             "qualification/oracle-reviews.json")
            self.assertIn("diagnostic-only", (target / "diagnostic-source.json").read_text())
            with self.assertRaises(DiagnosticError):
                prepare_diagnostic_suite(
                    source_suite=SOURCE, score_path=score, destination=target,
                    include_tasks={"locate-repository-content-identity"},
                )


if __name__ == "__main__":
    unittest.main()
