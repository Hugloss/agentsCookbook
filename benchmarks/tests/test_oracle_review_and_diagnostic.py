from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from benchmarks.diagnostic import (
    DiagnosticError, _SCORE_REPORT_FIELDS, prepare_diagnostic_suite,
)
from benchmarks.harness.oracle_reviews import OracleReviewError, validate_oracle_reviews
from benchmarks.harness.suite import SuiteError, load_suite


SOURCE = Path(__file__).resolve().parents[1] / "suites/repository-intelligence/heldout-v1"


class ReviewAndDiagnosticTests(unittest.TestCase):
    def test_qualified_label_without_source_campaign_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            score = root / "score.json"
            score.write_text(json.dumps({
                "schema": "agents-cookbook-heldout-observer-outcomes.v7",
                "projection_mode": "live",
                "campaign_qualification": {"status": "QUALIFIED"},
            }), encoding="utf-8")
            with self.assertRaisesRegex(DiagnosticError, "source score or campaign"):
                prepare_diagnostic_suite(
                    source_suite=SOURCE, source_results=root / "missing-results",
                    score_path=score, destination=root / "diagnostic",
                    include_tasks={"locate-repository-content-identity"},
                )
            self.assertFalse((root / "diagnostic").exists())

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
            source_results = root / "results"
            suite = load_suite(SOURCE)
            reports = {}
            for language in ("python", "typescript"):
                task_ids = sorted(
                    task_id for task_id, task in suite.tasks.items()
                    if task["family"].startswith(language + "-")
                )
                count = len(task_ids) * 9
                reports[language] = {
                    "task_ids": task_ids,
                    "expected_trials": count,
                    "observed_trials": count,
                    "status_counts": {"PASS": count},
                    "campaign_qualification": {"status": "QUALIFIED"},
                    **{field: [] for field in _SCORE_REPORT_FIELDS
                       if field not in {"expected_trials", "observed_trials",
                                        "status_counts", "campaign_qualification"}},
                }
            payload = {
                "schema": "agents-cookbook-heldout-observer-outcomes.v7",
                "projection_mode": "live",
                "selection": {"agents": ["opencode-native"]},
                "expected_trials": 108,
                "observed_trials": 108,
                "languages": reports,
                "campaign_qualification": {
                    "status": "QUALIFIED",
                    "languages": {name: row["campaign_qualification"]
                                  for name, row in reports.items()},
                },
            }
            score.write_text(json.dumps(payload), encoding="utf-8")
            target = root / "diagnostic"
            with mock.patch("benchmarks.diagnostic.read_campaign", return_value={
                "campaign_id": "a" * 64,
            }), mock.patch("benchmarks.diagnostic.build_report", side_effect=[
                {key: value for key, value in reports[name].items() if key != "task_ids"}
                for name in ("python", "typescript")
            ]):
                prepare_diagnostic_suite(
                    source_suite=SOURCE, source_results=source_results,
                    score_path=score, destination=target,
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
                    source_suite=SOURCE, source_results=source_results,
                    score_path=score, destination=target,
                    include_tasks={"locate-repository-content-identity"},
                )

            payload["languages"]["python"]["stability"] = [{"state": "unstable"}]
            score.write_text(json.dumps(payload), encoding="utf-8")
            with mock.patch("benchmarks.diagnostic.read_campaign", return_value={
                "campaign_id": "a" * 64,
            }), mock.patch("benchmarks.diagnostic.build_report", side_effect=[
                {key: value for key, value in reports[name].items()
                 if key != "task_ids" and key != "stability"} | {"stability": []}
                for name in ("python", "typescript")
            ]):
                with self.assertRaisesRegex(DiagnosticError, "disagrees"):
                    prepare_diagnostic_suite(
                        source_suite=SOURCE, source_results=source_results,
                        score_path=score, destination=root / "tampered",
                        include_tasks={"locate-repository-content-identity"},
                    )


if __name__ == "__main__":
    unittest.main()
