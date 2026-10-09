"""Focused regressions for controlled Harbor component ablations."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from benchmarks.harness.ablation_attribution import (
    build_ablation_report,
    quartet_projection,
)


FULL_TOOLS = [
    "repository_context",
    "find",
    "task_evidence",
    "change_impact",
]


def _treatment(subject: str) -> dict[str, object] | None:
    if subject == "none":
        return None
    if subject == "hashmarks":
        return {
            "tools": FULL_TOOLS,
            "projection_identity": "sha256:full",
            "source_contract_identity": "sha256:contract",
            "full_contract": True,
        }
    if subject == "hashmarks-no-task-evidence":
        return {
            "tools": [
                "repository_context",
                "find",
                "change_impact",
            ],
            "projection_identity": "sha256:without",
            "source_contract_identity": "sha256:contract",
            "full_contract": False,
        }
    if subject == "hashmarks-task-evidence-only":
        return {
            "tools": ["task_evidence"],
            "projection_identity": "sha256:only",
            "source_contract_identity": "sha256:contract",
            "full_contract": False,
        }
    raise AssertionError(subject)


def _projection(
    subject: str,
    *,
    status: str,
    task_evidence_invoked: bool = False,
) -> dict[str, object]:
    tools = (
        ["mcp__hashmarks__task_evidence"]
        if task_evidence_invoked
        else (
            ["mcp__hashmarks__find"]
            if subject not in ("none", "hashmarks-task-evidence-only")
            else []
        )
    )
    return {
        "receipt": {
            "backend": "harbor",
            "task_id": "locate-owner",
            "harness": "codex",
            "subject": subject,
            "model": "provider/model",
            "replicate_id": 6201,
            "status": status,
            "execution": {
                "campaign_id": "campaign",
                "mcp_treatment": _treatment(subject),
            },
        },
        "trace": {
            "available": True,
            "tool_order_complete": True,
            "subject_tools": tools,
        },
        "answer": None,
    }


def _quartet(
    *,
    bare: str = "FAIL",
    full: str = "PASS",
    removed: str = "FAIL",
    only: str = "PASS",
    full_invoked: bool = True,
    only_invoked: bool = True,
) -> dict[str, dict[str, object]]:
    return {
        "none": _projection("none", status=bare),
        "hashmarks": _projection(
            "hashmarks",
            status=full,
            task_evidence_invoked=full_invoked,
        ),
        "hashmarks-no-task-evidence": _projection(
            "hashmarks-no-task-evidence",
            status=removed,
        ),
        "hashmarks-task-evidence-only": _projection(
            "hashmarks-task-evidence-only",
            status=only,
            task_evidence_invoked=only_invoked,
        ),
    }


class HarborAblationAttributionTests(unittest.TestCase):
    def test_matched_quartet_can_support_necessity_and_sufficiency_contrasts(
        self,
    ) -> None:
        result = quartet_projection(_quartet())

        self.assertTrue(result["treatment_authority_valid"])
        self.assertEqual(
            result["necessity"],
            "SUPPORTED_NECESSITY_CONTRAST",
        )
        self.assertEqual(
            result["sufficiency"],
            "SUPPORTED_SUFFICIENCY_CONTRAST",
        )
        self.assertEqual(
            result["classification"],
            "NECESSARY_AND_SUFFICIENT_CONTRAST",
        )
        self.assertFalse(result["positive_causal_proof_claimed"])

    def test_positive_score_contrast_is_unattributable_without_invocation(
        self,
    ) -> None:
        result = quartet_projection(
            _quartet(
                full_invoked=False,
                only_invoked=False,
            )
        )

        self.assertEqual(
            result["necessity"],
            "UNATTRIBUTABLE_FULL_NEVER_INVOKED_TASK_EVIDENCE",
        )
        self.assertEqual(
            result["sufficiency"],
            "UNATTRIBUTABLE_ONLY_ARM_NEVER_INVOKED_TASK_EVIDENCE",
        )
        self.assertEqual(
            result["classification"],
            "NO_ISOLATED_TASK_EVIDENCE_SIGNAL",
        )

    def test_removal_pass_means_task_evidence_was_not_necessary_in_replicate(
        self,
    ) -> None:
        result = quartet_projection(
            _quartet(removed="PASS")
        )

        self.assertEqual(
            result["necessity"],
            "NOT_NECESSARY_IN_THIS_REPLICATE",
        )
        self.assertEqual(
            result["sufficiency"],
            "SUPPORTED_SUFFICIENCY_CONTRAST",
        )
        self.assertEqual(
            result["classification"],
            "SUFFICIENCY_SIGNAL",
        )

    def test_malformed_removal_arm_fails_treatment_authority(self) -> None:
        arms = _quartet()
        receipt = arms["hashmarks-no-task-evidence"]["receipt"]
        receipt["execution"]["mcp_treatment"]["tools"] = ["find"]

        result = quartet_projection(arms)

        self.assertFalse(result["treatment_authority_valid"])
        self.assertEqual(
            result["treatment_authority_error"],
            "removal-arm-not-single-tool-ablation",
        )
        self.assertEqual(
            result["necessity"],
            "UNQUALIFIED_TREATMENT_AUTHORITY",
        )
        self.assertEqual(
            result["sufficiency"],
            "UNQUALIFIED_TREATMENT_AUTHORITY",
        )

    def test_frozen_projection_does_not_prove_host_advertised_catalog(self) -> None:
        result = quartet_projection(_quartet())
        self.assertTrue(result["treatment_authority_valid"])
        self.assertFalse(result["observed_catalog_advertisement_proven"])
        for observed in result["observed_call_projection"].values():
            self.assertEqual(observed["status"], "NO_DISALLOWED_CALL_OBSERVED")
            self.assertFalse(observed["catalog_advertisement_proven"])

    def test_removal_arm_invoking_withheld_task_evidence_invalidates_contrast(
        self,
    ) -> None:
        arms = _quartet()
        arms["hashmarks-no-task-evidence"]["trace"]["subject_tools"] = [
            "mcp__hashmarks__task_evidence"
        ]
        result = quartet_projection(arms)
        self.assertFalse(result["treatment_authority_valid"])
        self.assertIn(
            "UNQUALIFIED_DISALLOWED_CALL",
            result["treatment_authority_error"],
        )
        self.assertEqual(
            result["observed_call_projection"]["hashmarks-no-task-evidence"][
                "disallowed_calls"
            ],
            ["mcp__hashmarks__task_evidence"],
        )
        self.assertEqual(
            result["classification"], "UNQUALIFIED_TREATMENT_AUTHORITY"
        )
        self.assertFalse(result["positive_causal_proof_claimed"])

    def test_task_evidence_only_arm_calling_find_invalidates_contrast(self) -> None:
        arms = _quartet()
        arms["hashmarks-task-evidence-only"]["trace"]["subject_tools"] = [
            "mcp__hashmarks__task_evidence",
            "mcp__hashmarks__find",
        ]
        result = quartet_projection(arms)
        self.assertFalse(result["treatment_authority_valid"])
        self.assertIn(
            "hashmarks-task-evidence-only",
            result["treatment_authority_error"],
        )
        self.assertEqual(
            result["sufficiency"], "UNQUALIFIED_TREATMENT_AUTHORITY"
        )

    def test_bare_arm_hashmarks_call_is_not_an_admitted_control(self) -> None:
        arms = _quartet()
        arms["none"]["trace"]["subject_tools"] = ["mcp__hashmarks__find"]
        result = quartet_projection(arms)
        self.assertFalse(result["treatment_authority_valid"])
        self.assertIn("none", result["treatment_authority_error"])

    def test_unknown_hashmarks_call_is_not_assumed_to_be_allowed(self) -> None:
        arms = _quartet()
        arms["hashmarks"]["trace"]["subject_tools"] = [
            "mcp__hashmarks__mystery",
            "mcp__hashmarks__task_evidence",
        ]
        result = quartet_projection(arms)
        self.assertFalse(result["treatment_authority_valid"])
        self.assertEqual(
            result["observed_call_projection"]["hashmarks"]["status"],
            "UNQUALIFIED_UNRESOLVED_CALL",
        )
        self.assertEqual(
            result["observed_call_projection"]["hashmarks"]["unresolved_calls"],
            ["mcp__hashmarks__mystery"],
        )

    def test_missing_or_partial_trace_cannot_admit_a_positive_ablation(self) -> None:
        for trace in (
            {"available": False},
            {"available": True, "subject_tools": []},
            {"available": True, "tool_order_complete": False, "subject_tools": []},
        ):
            arms = _quartet()
            arms["hashmarks-no-task-evidence"]["trace"] = trace
            result = quartet_projection(arms)
            self.assertFalse(result["treatment_authority_valid"])
            self.assertEqual(
                result["observed_call_projection"][
                    "hashmarks-no-task-evidence"
                ]["status"],
                "UNQUALIFIED_TRACE_INCOMPLETE",
            )

    def _report_from_quartets(
        self, quartets: list[dict[str, dict[str, object]]]
    ) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            projections = {}
            for index, arms in enumerate(quartets):
                for subject, row in arms.items():
                    row["receipt"]["replicate_id"] = 6201 + index
                    directory = root / f"{index:02d}-{subject}"
                    directory.mkdir()
                    projections[directory.name] = row
            with mock.patch(
                "benchmarks.harness.ablation_attribution.load_harbor_bundle_projection",
                side_effect=lambda directory: projections[directory.name],
            ):
                return build_ablation_report(root)

    def test_aggregate_uses_only_complete_treatment_qualified_quartets(self) -> None:
        valid = _quartet()
        bad_tools = _quartet(
            bare="PASS", full="FAIL", removed="PASS", only="FAIL"
        )
        bad_tools["hashmarks-no-task-evidence"]["trace"]["subject_tools"] = [
            "mcp__hashmarks__task_evidence"
        ]
        incomplete = _quartet(
            bare="PASS", full="FAIL", removed="PASS", only="FAIL"
        )
        incomplete["hashmarks-task-evidence-only"]["receipt"]["status"] = "INCOMPLETE"
        report = self._report_from_quartets([valid, bad_tools, incomplete])
        summary = report["summary"]
        self.assertEqual(summary["matched_quartets"], 3)
        self.assertEqual(summary["qualified_complete_quartets"], 1)
        self.assertEqual(summary["treatment_unqualified_quartets"], 1)
        self.assertEqual(summary["incomplete_outcome_quartets"], 1)
        self.assertEqual(summary["excluded_matched_quartets"], 2)
        by_harness = report["by_harness"]["codex"]
        self.assertEqual(by_harness["matched_quartets"], 3)
        self.assertEqual(by_harness["qualified_complete_quartets"], 1)
        self.assertEqual(
            by_harness["success_rate"],
            {
                "none": 0.0,
                "hashmarks": 1.0,
                "hashmarks-no-task-evidence": 0.0,
                "hashmarks-task-evidence-only": 1.0,
            },
        )
        self.assertEqual(by_harness["task_evidence_removal_drop"], 1.0)
        self.assertEqual(by_harness["task_evidence_only_uplift_vs_bare"], 1.0)

    def test_no_qualified_complete_quartet_means_unknown_aggregate(self) -> None:
        bad_tools = _quartet()
        bad_tools["hashmarks-task-evidence-only"]["trace"]["subject_tools"] = [
            "mcp__hashmarks__find"
        ]
        report = self._report_from_quartets([bad_tools])
        summary = report["summary"]
        self.assertEqual(summary["matched_quartets"], 1)
        self.assertEqual(summary["qualified_complete_quartets"], 0)
        self.assertEqual(summary["excluded_matched_quartets"], 1)
        by_harness = report["by_harness"]["codex"]
        self.assertEqual(by_harness["qualified_complete_quartets"], 0)
        self.assertTrue(all(value is None for value in by_harness["success_rate"].values()))
        self.assertIsNone(by_harness["full_uplift_vs_bare"])
        self.assertIsNone(by_harness["task_evidence_removal_drop"])
        self.assertIsNone(by_harness["task_evidence_only_uplift_vs_bare"])

    def test_incomplete_or_unmatched_groups_do_not_enter_aggregate(self) -> None:
        partial = _quartet()
        partial.pop("hashmarks-task-evidence-only")
        report = self._report_from_quartets([partial])
        self.assertEqual(report["summary"]["matched_quartets"], 0)
        self.assertEqual(report["summary"]["incomplete_groups"], 1)
        self.assertEqual(report["summary"]["qualified_complete_quartets"], 0)
        self.assertIsNone(report["by_harness"]["codex"]["full_uplift_vs_bare"])

    def test_ordinary_two_arm_results_are_not_an_ablation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = build_ablation_report(Path(tmp))

        self.assertFalse(report["applicable"])
        self.assertEqual(report["summary"]["matched_quartets"], 0)


if __name__ == "__main__":
    unittest.main()
