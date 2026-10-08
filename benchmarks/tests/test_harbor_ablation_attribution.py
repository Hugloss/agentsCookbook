"""Focused regressions for controlled Harbor component ablations."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

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
            if subject != "none"
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

    def test_ordinary_two_arm_results_are_not_an_ablation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = build_ablation_report(Path(tmp))

        self.assertFalse(report["applicable"])
        self.assertEqual(report["summary"]["matched_quartets"], 0)


if __name__ == "__main__":
    unittest.main()
