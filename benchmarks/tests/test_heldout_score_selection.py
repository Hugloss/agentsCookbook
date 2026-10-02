from __future__ import annotations

import json
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from benchmarks.harness.regrade import RegradeError
from benchmarks.harness.suite import load_suite


HELDOUT = (
    Path(__file__).resolve().parents[1]
    / "suites/repository-intelligence/heldout-v1"
)
SCORE = HELDOUT / "score.py"


class HeldoutScoreSelectionTests(unittest.TestCase):
    def test_score_covers_exactly_the_selected_agents(self) -> None:
        suite = load_suite(HELDOUT)
        conditions = {
            str(row["id"]): row for row in suite.experiment["conditions"]
        }
        score_main = runpy.run_path(str(SCORE))["main"]

        for value, agents in (
            ("opencode-native", {"opencode-native"}),
            ("codex-native,opencode-native", {"codex-native", "opencode-native"}),
        ):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / "score.json"
                selected_by_language: list[set[str]] = []

                def report(*, selected_definitions, require_complete, **kwargs):
                    self.assertTrue(require_complete)
                    selected_by_language.append(selected_definitions)
                    return {
                        "expected_trials": len(selected_definitions),
                        "observed_trials": len(selected_definitions),
                        "status_counts": {"PASS": len(selected_definitions)},
                        "campaign_qualification": {
                            "status": "QUALIFIED",
                            "complete": True,
                            "invalid_outcomes": 0,
                            "mixed_execution_authority": False,
                            "mixed_localization_scoring_policy": False,
                        },
                        "conditions": {},
                        "paired_assistance": [],
                        "paired_assistance_summary": [],
                        "stability": [],
                        "agent_profiles": {},
                        "cross_agent_observations": [],
                    }

                with (
                    mock.patch.dict(score_main.__globals__, {"build_report": report}),
                    mock.patch.object(
                        sys,
                        "argv",
                        [
                            str(SCORE),
                            "--results",
                            str(Path(tmp) / "results"),
                            "--output",
                            str(output),
                            "--agent",
                            value,
                        ],
                    ),
                ):
                    self.assertEqual(score_main(), 0)

                expected_ids = {
                    str(row["definition_id"])
                    for row in suite.trial_definitions()
                    if conditions[str(row["condition_id"])]["agent"] in agents
                }
                self.assertEqual(len(selected_by_language), 2)
                self.assertFalse(selected_by_language[0] & selected_by_language[1])
                self.assertEqual(set.union(*selected_by_language), expected_ids)
                payload = json.loads(output.read_text(encoding="utf-8"))
                self.assertEqual(
                    payload["schema"],
                    "agents-cookbook-heldout-observer-outcomes.v5",
                )
                self.assertEqual(payload["selection"], {"agents": sorted(agents)})
                self.assertEqual(payload["projection_mode"], "live")
                self.assertEqual(
                    payload["campaign_qualification"]["status"],
                    "QUALIFIED",
                )
                self.assertEqual(payload["expected_trials"], 108 * len(agents))
                self.assertEqual(payload["observed_trials"], 108 * len(agents))
                self.assertEqual(
                    payload["authority"]["cross_agent_comparison"],
                    "descriptive-only"
                    if len(agents) == 2
                    else "not-applicable-single-agent-selection",
                )

    def test_offline_score_uses_projected_rows_and_preserves_output_on_failure(self) -> None:
        score_main = runpy.run_path(str(SCORE))["main"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            output = root / "score.json"
            calls = []

            def project(*, selected_definitions, **kwargs):
                calls.append(len(selected_definitions))
                return [{}], [{
                    "current_definition_id": str(len(calls)),
                    "source_trial_id": "a" * 64,
                    "source_result_sha256": "b" * 64,
                    "projection_identity": "c" * 64,
                }]

            def report(*, projected_receipts, selected_definitions, **kwargs):
                self.assertEqual(projected_receipts, [{}])
                return {
                    "expected_trials": len(selected_definitions),
                    "observed_trials": len(selected_definitions),
                    "status_counts": {"PASS": len(selected_definitions)},
                    "campaign_qualification": {"status": "QUALIFIED"},
                    "conditions": {},
                    "paired_assistance": [],
                    "paired_assistance_summary": [],
                    "stability": [],
                    "agent_profiles": {},
                    "cross_agent_observations": [],
                }

            argv = [
                str(SCORE), "--regrade-source-results", str(source),
                "--output", str(output), "--agent", "opencode-native",
            ]
            with (
                mock.patch.dict(score_main.__globals__, {
                    "project_campaign_receipts": project,
                    "build_report": report,
                }),
                mock.patch.object(sys, "argv", argv),
            ):
                self.assertEqual(score_main(), 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["projection_mode"], "offline-regrade")
            self.assertEqual(len(payload["source_lineage"]), 2)
            self.assertEqual(calls, [54, 54])

            def fail(**kwargs):
                raise RegradeError("source changed")

            before = output.read_bytes()
            with (
                mock.patch.dict(score_main.__globals__, {
                    "project_campaign_receipts": fail,
                }),
                mock.patch.object(sys, "argv", argv),
                self.assertRaisesRegex(SystemExit, "source changed"),
            ):
                score_main()
            self.assertEqual(output.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
