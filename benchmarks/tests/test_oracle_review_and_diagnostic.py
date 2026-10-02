from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from benchmarks.__main__ import main
from benchmarks.diagnostic import (
    DiagnosticError,
    _SCORE_REPORT_FIELDS,
    prepare_diagnostic_suite,
)
from benchmarks.harness.oracle_reviews import (
    OracleReviewError,
    oracle_review_guide,
    validate_oracle_reviews,
)
from benchmarks.harness.oracle_review_runner import (
    DECISION_PREFIX,
    REVIEWER_ID,
    run_pending_oracle_reviews,
)
from benchmarks.harness.suite import SuiteError, load_suite


SOURCE = (
    Path(__file__).resolve().parents[1] / "suites/repository-intelligence/heldout-v1"
)


class ReviewAndDiagnosticTests(unittest.TestCase):
    def test_qualified_label_without_source_campaign_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            score = root / "score.json"
            score.write_text(
                json.dumps(
                    {
                        "schema": "agents-cookbook-heldout-observer-outcomes.v7",
                        "projection_mode": "live",
                        "campaign_qualification": {"status": "QUALIFIED"},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(DiagnosticError, "source score or campaign"):
                prepare_diagnostic_suite(
                    source_suite=SOURCE,
                    source_results=root / "missing-results",
                    score_path=score,
                    destination=root / "diagnostic",
                    include_tasks={"locate-repository-content-identity"},
                )
            self.assertFalse((root / "diagnostic").exists())

    def test_required_review_cannot_be_bypassed_by_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "suite"
            shutil.copytree(SOURCE, copy)
            (copy / "qualification/oracle-reviews.json").unlink()
            with self.assertRaisesRegex(
                SuiteError, "oracle review evidence is missing"
            ):
                load_suite(copy)

    def test_explicit_review_path_is_the_bound_review_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "suite"
            shutil.copytree(SOURCE, copy)
            experiment_path = copy / "experiment.json"
            experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
            configured = "qualification/reviews-alt.json"
            experiment["oracle_reviews"] = configured
            alternate = copy / configured
            alternate.write_bytes(
                (copy / "qualification/oracle-reviews.json").read_bytes()
            )
            (copy / "qualification/oracle-reviews.json").unlink()
            experiment_path.write_text(json.dumps(experiment), encoding="utf-8")
            self.assertEqual(
                validate_oracle_reviews(load_suite(copy), require_complete=False)[
                    "first_reviewed_tasks"
                ],
                12,
            )

    def test_review_path_cannot_escape_suite_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "suite"
            shutil.copytree(SOURCE, copy)
            experiment_path = copy / "experiment.json"
            experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
            experiment["oracle_reviews"] = "../outside.json"
            experiment_path.write_text(json.dumps(experiment), encoding="utf-8")
            with self.assertRaisesRegex(SuiteError, "escapes suite root"):
                load_suite(copy)

    def test_one_review_is_default_and_only_escalated_task_remains_pending(self) -> None:
        result = validate_oracle_reviews(load_suite(SOURCE), require_complete=False)
        self.assertEqual(result["first_reviewed_tasks"], 12)
        self.assertEqual(result["approved_tasks"], 11)
        self.assertEqual(
            result["pending_tasks"],
            ["locate-repository-content-identity"],
        )
        self.assertEqual(
            result["escalated_tasks"],
            ["locate-repository-content-identity"],
        )
        with self.assertRaisesRegex(
            OracleReviewError,
            "1 evidence-escalated task",
        ):
            validate_oracle_reviews(load_suite(SOURCE), require_complete=True)

    def test_second_review_completes_only_escalated_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "suite"
            shutil.copytree(SOURCE, copy)
            review_path = copy / "qualification/oracle-reviews.json"
            evidence = json.loads(review_path.read_text(encoding="utf-8"))
            row = evidence["tasks"]["locate-repository-content-identity"]
            row["reviews"].append(
                {
                    "decision": "unique",
                    "reason": (
                        "Independent source inspection confirms the test-shard "
                        "content identity is computed by this function."
                    ),
                    "reviewer": "independent-review-b",
                    "task_digest": row["task_digest"],
                }
            )
            review_path.write_text(
                json.dumps(evidence, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            result = validate_oracle_reviews(load_suite(copy), require_complete=True)
            self.assertTrue(result["complete"])
            self.assertEqual(result["approved_tasks"], 12)

    def test_escalation_requires_a_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "suite"
            shutil.copytree(SOURCE, copy)
            suite = load_suite(copy)
            review_path = copy / "qualification/oracle-reviews.json"
            evidence = json.loads(review_path.read_text(encoding="utf-8"))
            requirement = evidence["tasks"]["locate-repository-content-identity"][
                "review_requirement"
            ]
            requirement["escalation_reason"] = None
            review_path.write_text(json.dumps(evidence), encoding="utf-8")
            with self.assertRaisesRegex(
                OracleReviewError,
                "escalated oracle review reason missing",
            ):
                validate_oracle_reviews(suite, require_complete=False)

    def test_oracle_review_runner_reviews_only_pending_escalation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "suite"
            shutil.copytree(SOURCE, copy)
            suite = load_suite(copy)
            task = suite.tasks["locate-repository-content-identity"]
            task_digest = validate_oracle_reviews(
                suite, require_complete=False
            ) and json.loads(
                (copy / "qualification/oracle-reviews.json").read_text(
                    encoding="utf-8"
                )
            )["tasks"]["locate-repository-content-identity"]["task_digest"]

            def materialize(**kwargs):
                kwargs["destination"].mkdir(parents=True)

            def review(_workspace, prompt):
                self.assertIn("locate-repository-content-identity", prompt)
                self.assertIn("hashmarks/test_shards.py", prompt)
                self.assertNotIn(
                    "hashes canonical source paths and bytes",
                    prompt,
                )
                payload = {
                    "task_id": "locate-repository-content-identity",
                    "task_digest": task_digest,
                    "decision": "unique",
                    "reason": "Independent inspection found one semantic owner.",
                }
                return {
                    "stdout": "audit\n" + DECISION_PREFIX + json.dumps(payload),
                    "command_identity": "sha256:review-command",
                }

            with (
                mock.patch(
                    "benchmarks.harness.oracle_review_runner.materialize_repository",
                    side_effect=materialize,
                ),
                mock.patch(
                    "benchmarks.harness.oracle_review_runner._run_review",
                    side_effect=review,
                ),
            ):
                result = run_pending_oracle_reviews(
                    suite,
                    cache_root=Path(tmp) / "cache",
                )

            self.assertTrue(result["complete"])
            self.assertEqual(result["approved_tasks"], 12)
            self.assertEqual(
                [row["task_id"] for row in result["reviewed_tasks"]],
                ["locate-repository-content-identity"],
            )
            evidence = json.loads(
                (copy / "qualification/oracle-reviews.json").read_text(
                    encoding="utf-8"
                )
            )
            reviews = evidence["tasks"]["locate-repository-content-identity"][
                "reviews"
            ]
            self.assertEqual(len(reviews), 2)
            self.assertEqual(reviews[-1]["reviewer"], REVIEWER_ID)
            self.assertEqual(reviews[-1]["decision"], "unique")

    def test_oracle_review_runner_preserves_ambiguous_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "suite"
            shutil.copytree(SOURCE, copy)
            suite = load_suite(copy)
            row = json.loads(
                (copy / "qualification/oracle-reviews.json").read_text(
                    encoding="utf-8"
                )
            )["tasks"]["locate-repository-content-identity"]

            def materialize(**kwargs):
                kwargs["destination"].mkdir(parents=True)

            payload = {
                "task_id": "locate-repository-content-identity",
                "task_digest": row["task_digest"],
                "decision": "ambiguous",
                "reason": "Independent inspection found two defensible owners.",
            }
            with (
                mock.patch(
                    "benchmarks.harness.oracle_review_runner.materialize_repository",
                    side_effect=materialize,
                ),
                mock.patch(
                    "benchmarks.harness.oracle_review_runner._run_review",
                    return_value={
                        "stdout": DECISION_PREFIX + json.dumps(payload),
                        "command_identity": "sha256:review-command",
                    },
                ),
            ):
                result = run_pending_oracle_reviews(
                    suite,
                    cache_root=Path(tmp) / "cache",
                )

            self.assertFalse(result["complete"])
            self.assertEqual(
                result["pending_tasks"],
                ["locate-repository-content-identity"],
            )
            evidence = json.loads(
                (copy / "qualification/oracle-reviews.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                evidence["tasks"]["locate-repository-content-identity"][
                    "reviews"
                ][-1]["decision"],
                "ambiguous",
            )

    def test_oracle_review_cli_prints_next_action_and_succeeds(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(
                main(["oracle-review", "--suite", str(SOURCE)]),
                0,
            )
        rendered = output.getvalue()
        self.assertIn("Oracle review BLOCKED: 11/12 tasks approved", rendered)
        self.assertIn("make benchmark-oracle-review-check", rendered)

    def test_oracle_review_cli_execute_dispatches_runner(self) -> None:
        output = io.StringIO()
        with (
            mock.patch(
                "benchmarks.__main__.run_pending_oracle_reviews",
                return_value={
                    "reviewed_tasks": [
                        {"task_id": "locate-repository-content-identity"}
                    ],
                    "approved_tasks": 12,
                    "pending_tasks": [],
                    "complete": True,
                },
            ) as run,
            redirect_stdout(output),
        ):
            self.assertEqual(
                main(
                    [
                        "oracle-review",
                        "--suite",
                        str(SOURCE),
                        "--execute",
                    ]
                ),
                0,
            )
        self.assertTrue(run.called)
        self.assertIn('"complete": true', output.getvalue())

    def test_oracle_review_guide_hands_off_without_self_approval(self) -> None:
        suite = load_suite(SOURCE)
        guide = oracle_review_guide(suite)
        self.assertIn("Oracle review BLOCKED: 11/12 tasks approved", guide)
        self.assertIn("One independent source review is the default.", guide)
        self.assertIn("This command does not self-approve benchmark truth.", guide)
        self.assertIn("locate-repository-content-identity", guide)
        self.assertNotIn("locate-prefix-path-enumerator", guide)
        self.assertIn("required independent reviews: 2", guide)
        self.assertIn("existing independent reviews: 1", guide)
        self.assertIn("Prior heldout-v1 runs showed", guide)
        self.assertIn("make benchmark-oracle-review-check", guide)
        self.assertIn("make benchmark", guide)
        self.assertEqual(
            validate_oracle_reviews(suite, require_complete=False)[
                "approved_tasks"
            ],
            11,
        )

    def test_diagnostic_is_separate_and_has_ten_paired_replicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            score = root / "score.json"
            source_results = root / "results"
            suite = load_suite(SOURCE)
            reports = {}
            for language in ("python", "typescript"):
                task_ids = sorted(
                    task_id
                    for task_id, task in suite.tasks.items()
                    if task["family"].startswith(language + "-")
                )
                count = len(task_ids) * 9
                reports[language] = {
                    "task_ids": task_ids,
                    "expected_trials": count,
                    "observed_trials": count,
                    "status_counts": {"PASS": count},
                    "campaign_qualification": {"status": "QUALIFIED"},
                    **{
                        field: []
                        for field in _SCORE_REPORT_FIELDS
                        if field
                        not in {
                            "expected_trials",
                            "observed_trials",
                            "status_counts",
                            "campaign_qualification",
                        }
                    },
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
                    "languages": {
                        name: row["campaign_qualification"]
                        for name, row in reports.items()
                    },
                },
            }
            score.write_text(json.dumps(payload), encoding="utf-8")
            target = root / "diagnostic"
            with (
                mock.patch(
                    "benchmarks.diagnostic.read_campaign",
                    return_value={
                        "campaign_id": "a" * 64,
                    },
                ),
                mock.patch(
                    "benchmarks.diagnostic.build_report",
                    side_effect=[
                        {
                            key: value
                            for key, value in reports[name].items()
                            if key != "task_ids"
                        }
                        for name in ("python", "typescript")
                    ],
                ),
            ):
                prepare_diagnostic_suite(
                    source_suite=SOURCE,
                    source_results=source_results,
                    score_path=score,
                    destination=target,
                    include_tasks={"locate-repository-content-identity"},
                )
            suite = load_suite(target)
            self.assertEqual(len(suite.trial_definitions()), 60)
            self.assertEqual(
                suite.experiment["tasks"], ["locate-repository-content-identity"]
            )
            self.assertEqual(
                suite.experiment["oracle_reviews"], "qualification/oracle-reviews.json"
            )
            self.assertIn(
                "diagnostic-only", (target / "diagnostic-source.json").read_text()
            )
            with self.assertRaises(DiagnosticError):
                prepare_diagnostic_suite(
                    source_suite=SOURCE,
                    source_results=source_results,
                    score_path=score,
                    destination=target,
                    include_tasks={"locate-repository-content-identity"},
                )

            payload["languages"]["python"]["stability"] = [{"state": "unstable"}]
            score.write_text(json.dumps(payload), encoding="utf-8")
            with (
                mock.patch(
                    "benchmarks.diagnostic.read_campaign",
                    return_value={
                        "campaign_id": "a" * 64,
                    },
                ),
                mock.patch(
                    "benchmarks.diagnostic.build_report",
                    side_effect=[
                        {
                            key: value
                            for key, value in reports[name].items()
                            if key != "task_ids" and key != "stability"
                        }
                        | {"stability": []}
                        for name in ("python", "typescript")
                    ],
                ),
            ):
                with self.assertRaisesRegex(DiagnosticError, "disagrees"):
                    prepare_diagnostic_suite(
                        source_suite=SOURCE,
                        source_results=source_results,
                        score_path=score,
                        destination=root / "tampered",
                        include_tasks={"locate-repository-content-identity"},
                    )


if __name__ == "__main__":
    unittest.main()
