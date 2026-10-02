from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from benchmarks.harness.report import build_report
from benchmarks.harness.suite import SuiteDefinition


def _suite() -> SuiteDefinition:
    experiment = {
        "id": "stability",
        "version": 1,
        "suite": "repository-intelligence",
        "tasks": ["task"],
        "conditions": [
            {
                "id": "bare",
                "subject": "none",
                "agent": "agent",
                "trials": 3,
                "seed": 10,
            },
            {
                "id": "hashmarks",
                "subject": "hashmarks",
                "agent": "agent",
                "trials": 3,
                "seed": 10,
            },
        ],
        "scoring": {"id": "score", "version": 1, "metrics": ["task_success"]},
    }
    task = {
        "id": "task",
        "version": 1,
        "family": "test",
        "mode": "read_only",
        "repository": {
            "url": "https://example.invalid/repo.git",
            "commit": "1" * 40,
            "tree": "2" * 40,
        },
        "prompt": "find owner",
        "mutation": None,
        "oracle": {
            "adapter": "expected-json",
            "identity": {"id": "oracle", "version": "1"},
            "configuration": {"expected": {"ok": True}},
        },
        "budgets": {"timeout_seconds": 1},
        "contamination": {
            "allowed_change_globs": [],
            "allowed_generated_globs": [],
        },
    }
    subjects = {
        "none": {
            "id": "none",
            "kind": "control",
            "adapter": "none",
            "identity": {"id": "none", "version": "1"},
            "capabilities": [],
            "configuration": {},
        },
        "hashmarks": {
            "id": "hashmarks",
            "kind": "repository_intelligence",
            "adapter": "hashmarks",
            "identity": {"id": "hashmarks", "version": "runtime-observed"},
            "capabilities": [],
            "configuration": {},
        },
    }
    agents = {
        "agent": {
            "id": "agent",
            "adapter": "fake",
            "identity": {"id": "agent", "version": "runtime-observed"},
            "capabilities": [],
            "configuration": {},
        }
    }
    return SuiteDefinition(Path("."), experiment, {"task": task}, subjects, agents)


def _receipt(
    suite: SuiteDefinition,
    row: dict[str, object],
    status: str,
    trial_id: str,
) -> dict[str, object]:
    condition = next(
        value
        for value in suite.experiment["conditions"]
        if value["id"] == row["condition_id"]
    )
    return {
        "definition_id": row["definition_id"],
        "trial_id": trial_id,
        "experiment": suite.experiment,
        "task": suite.tasks["task"],
        "condition": suite.expanded_condition(condition),
        "status": status,
        "authority": {"subject": {"available": False}},
        "execution": {
            "trial_index": int(row["trial"]),
            "seed": int(row["seed"]),
        },
        "measurements": {"agent": {}},
    }


class BenchmarkStabilityReportingTests(unittest.TestCase):
    def test_report_preserves_replicate_variance_and_paired_transitions(self) -> None:
        suite = _suite()
        rows = {
            (str(row["condition_id"]), int(row["trial"])): row
            for row in suite.trial_definitions()
        }
        receipts = []
        bare_statuses = ("PASS", "FAIL", "PASS")
        hashmarks_statuses = ("PASS", "PASS", "PASS")
        for index in range(3):
            receipts.append(
                _receipt(
                    suite,
                    rows[("bare", index)],
                    bare_statuses[index],
                    ("a" if index == 0 else "b" if index == 1 else "c") * 64,
                )
            )
            receipts.append(
                _receipt(
                    suite,
                    rows[("hashmarks", index)],
                    hashmarks_statuses[index],
                    ("d" if index == 0 else "e" if index == 1 else "f") * 64,
                )
            )

        with mock.patch(
            "benchmarks.harness.report._receipts",
            return_value=receipts,
        ):
            report = build_report(suite=suite, results_root=Path("/unused"))

        self.assertEqual(report["schema"]["version"], 6)
        stability = {
            row["subject_id"]: row
            for row in report["stability"]
        }
        self.assertEqual(stability["none"]["state"], "unstable")
        self.assertEqual(stability["none"]["semantic_correct"], 2)
        self.assertEqual(stability["none"]["semantic_incorrect"], 1)
        self.assertEqual(stability["none"]["replicate_ids"], [10, 11, 12])
        self.assertEqual(stability["hashmarks"]["state"], "stable-correct")
        self.assertEqual(stability["hashmarks"]["semantic_correct"], 3)

        summary = report["paired_assistance_summary"]
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["subject_id"], "hashmarks")
        self.assertEqual(
            summary[0]["transitions"],
            {
                "gain": 1,
                "preserved": 2,
                "unresolved": 0,
                "regression": 0,
            },
        )
        self.assertEqual(
            [row["assistance_transition"] for row in report["paired_assistance"]],
            ["preserved", "gain", "preserved"],
        )
        self.assertTrue(
            all(
                row["replicate_id"] == row["seed"]
                for row in report["paired_assistance"]
            )
        )
        self.assertFalse(
            report["authority"]["replicate_identity_is_provider_sampling_seed"]
        )

    def test_non_outcome_is_execution_instability_not_semantic_failure(self) -> None:
        suite = _suite()
        rows = [
            row
            for row in suite.trial_definitions()
            if row["condition_id"] == "hashmarks"
        ]
        receipts = [
            _receipt(
                suite,
                row,
                "INCOMPLETE" if int(row["trial"]) == 1 else "PASS",
                chr(ord("a") + int(row["trial"])) * 64,
            )
            for row in rows
        ]
        with mock.patch(
            "benchmarks.harness.report._receipts",
            return_value=receipts,
        ):
            report = build_report(
                suite=suite,
                results_root=Path("/unused"),
                selected_definitions={
                    str(row["definition_id"]) for row in rows
                },
            )
        self.assertEqual(report["stability"][0]["state"], "execution-unstable")
        self.assertEqual(report["stability"][0]["valid_outcomes"], 2)
        self.assertEqual(report["stability"][0]["semantic_correct"], 2)

    def test_missing_replicate_remains_visible_in_stability_and_pair_exclusions(self) -> None:
        suite = _suite()
        rows = suite.trial_definitions()
        bare = next(row for row in rows if row["condition_id"] == "bare")
        with mock.patch("benchmarks.harness.report._receipts", return_value=[
            _receipt(suite, bare, "PASS", "a" * 64)
        ]):
            report = build_report(
                suite=suite, results_root=Path("/unused"), require_complete=False,
            )
        by_subject = {row["subject_id"]: row for row in report["stability"]}
        self.assertEqual(by_subject["none"]["replicates"], 3)
        self.assertEqual(by_subject["none"]["observed_replicates"], 1)
        self.assertEqual(by_subject["none"]["state"], "execution-unstable")
        self.assertEqual(by_subject["hashmarks"]["replicates"], 3)
        self.assertEqual(by_subject["hashmarks"]["observed_replicates"], 0)
        self.assertEqual(len(report["paired_assistance_exclusions"]), 3)


if __name__ == "__main__":
    unittest.main()
