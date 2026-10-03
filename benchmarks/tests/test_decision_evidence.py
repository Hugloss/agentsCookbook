from __future__ import annotations

import unittest

from benchmarks.harness.decision_evidence import build_decision_evidence


class DecisionEvidenceTests(unittest.TestCase):
    def test_decision_evidence_separates_runtime_semantic_format_and_assistance(self) -> None:
        report = {
            "expected_trials": 6,
            "observed_trials": 6,
            "status_counts": {"PASS": 3, "FAIL": 2, "INCOMPLETE": 1},
            "campaign_qualification": {
                "status": "NOT_QUALIFIED",
                "complete": True,
                "invalid_outcomes": 1,
            },
            "diagnostics": [
                {
                    "task_id": "runtime-task",
                    "primary": "agent-terminal",
                    "reason_code": "agent-terminal-failed",
                    "stage": "execution",
                },
                {
                    "task_id": "semantic-task",
                    "primary": "semantic-incorrect",
                    "reason_code": None,
                    "stage": None,
                },
            ],
            "stability": [
                {
                    "task_id": "semantic-task",
                    "agent_id": "opencode-native",
                    "subject_id": "hashmarks",
                    "state": "unstable",
                    "valid_outcomes": 3,
                    "gradeable_outcomes": 3,
                    "semantic_correct": 2,
                    "semantic_incorrect": 1,
                }
            ],
            "agent_profiles": {
                "opencode-native": {
                    "format_contract": {
                        "state": "strict-contract-saturated-noncompliant",
                        "observations": 3,
                        "compliant": 0,
                        "noncompliant": 3,
                        "answer_shapes": {"JSON_FENCE": 3},
                        "semantic_gradeable_observations": 3,
                        "semantic_gradeable": 3,
                        "interpretation": "strict format only",
                    },
                    "source_read_observability": [
                        "not-authoritatively-exposed-by-opencode-export"
                    ],
                }
            },
            "conditions": {},
            "subject_adoption": [
                {
                    "agent_id": "opencode-native",
                    "subject_id": "hashmarks",
                    "state": "configured-never-invoked",
                    "invocation_unknown_trials": 0,
                }
            ],
            "paired_assistance_summary": [],
            "paired_assistance_usage_summary": [],
            "task_assistance_evidence": [
                {
                    "task_id": "semantic-task",
                    "evidence_signals": [
                        "bare-headroom-observed",
                        "subject-not-invoked",
                    ],
                }
            ],
        }

        evidence = build_decision_evidence(report)

        self.assertEqual(
            evidence["schema"],
            "agents-cookbook-benchmark-decision-evidence.v1",
        )
        self.assertTrue(evidence["authority"]["derived_only"])
        self.assertFalse(evidence["authority"]["ranking_performed"])
        self.assertFalse(evidence["authority"]["recommendation_performed"])
        self.assertEqual(evidence["surfaces"]["runtime"]["trials"], 1)
        self.assertEqual(
            evidence["surfaces"]["runtime"]["tasks"],
            ["runtime-task"],
        )
        self.assertEqual(
            evidence["surfaces"]["runtime"]["reason_codes"],
            {"agent-terminal-failed": 1},
        )
        self.assertEqual(
            evidence["surfaces"]["semantic"]["rows"][0]["task_id"],
            "semantic-task",
        )
        self.assertEqual(
            evidence["surfaces"]["assistance"]["task_signal_counts"],
            {
                "bare-headroom-observed": 1,
                "subject-not-invoked": 1,
            },
        )
        self.assertEqual(
            evidence["evidence_gaps"]["source_read_observability"],
            ["not-authoritatively-exposed-by-opencode-export"],
        )
        self.assertEqual(
            evidence["evidence_signals"],
            [
                "bare-headroom-observed",
                "configured-subject-never-invoked",
                "runtime-or-host-instability-observed",
                "semantic-misses-observed",
                "source-read-archaeology-unavailable",
                "strict-format-saturation-observed",
                "subject-not-invoked",
            ],
        )

    def test_decision_evidence_tolerates_older_report_without_task_projection(self) -> None:
        evidence = build_decision_evidence(
            {
                "expected_trials": 1,
                "observed_trials": 1,
                "status_counts": {"PASS": 1},
                "campaign_qualification": {"status": "QUALIFIED"},
                "diagnostics": [],
                "stability": [],
                "agent_profiles": {},
                "conditions": {},
                "subject_adoption": [],
                "paired_assistance_summary": [],
                "paired_assistance_usage_summary": [],
            }
        )

        self.assertEqual(
            evidence["surfaces"]["assistance"]["task_evidence"],
            [],
        )
        self.assertEqual(evidence["evidence_signals"], [])


if __name__ == "__main__":
    unittest.main()
