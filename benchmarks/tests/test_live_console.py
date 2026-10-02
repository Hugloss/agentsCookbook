from __future__ import annotations

import unittest
import copy
from pathlib import Path

from benchmarks.harness.live_console import (
    LiveCampaignProgress,
    LiveTaskMatrix,
    TrialHeartbeat,
    render_trial_failure,
)
from benchmarks.harness.runner import TrialRunResult
from benchmarks.harness.suite import SuiteDefinition, load_suite


SUITE = Path("benchmarks/suites/repository-intelligence/heldout-v1")


class LiveTaskMatrixTests(unittest.TestCase):
    def _prefix_opencode_rows(self):
        suite = load_suite(SUITE)
        rows = [
            row
            for row in suite.trial_definitions()
            if row["task_id"] == "locate-prefix-path-enumerator"
            and row["condition_id"].endswith("opencode-native")
        ]
        return suite, rows

    def _receipt(
        self,
        suite,
        row,
        status,
        *,
        gradeable=True,
        invoked=None,
        subject_mcp_calls=None,
        tool_names=None,
        tool_observability=None,
    ):
        condition = next(
            item for item in suite.experiment["conditions"]
            if item["id"] == row["condition_id"]
        )
        return {
            "definition_id": row["definition_id"],
            "status": status,
            "task": suite.tasks[row["task_id"]],
            "condition": suite.expanded_condition(condition),
            "execution": {
                "trial_index": row["trial"],
                "replicate_id": row["replicate_id"],
                "admitted_state_sha256": "same-input",
            },
            "authority": {
                "agent": {"observed": {}},
                "harness": {"same": True},
                "environment": {"same": True},
                "mutation": None,
            },
            "scoring": {
                "oracle_grade": {
                    "semantic_gradeable": gradeable,
                    "semantic_success": status == "PASS" if gradeable else False,
                    "semantic_status": (
                        "CORRECT"
                        if gradeable and status == "PASS"
                        else "INCORRECT"
                        if gradeable and status == "FAIL"
                        else "UNSCORABLE"
                        if not gradeable
                        else None
                    ),
                }
            },
            "measurements": {
                "agent": {
                    "subject_tool_invoked": invoked,
                    "subject_mcp_calls": subject_mcp_calls,
                    "subject_tool_names": list(tool_names or ()),
                    "subject_tool_observability": tool_observability,
                }
            },
        }

    def _status(self, rows, complete=()):
        completed = set(complete)
        return {
            "rows": [
                {
                    "definition_id": row["definition_id"],
                    "state": "COMPLETE" if row["definition_id"] in completed else "PENDING",
                }
                for row in rows
            ],
            "complete_trials": len(completed),
            "pending_trials": len(rows) - len(completed),
            "interrupted_trials": 0,
        }

    def test_renders_compact_task_matrix_and_paired_transitions(self) -> None:
        suite, rows = self._prefix_opencode_rows()
        statuses = {
            ("none-opencode-native", 0): "FAIL",
            ("none-opencode-native", 1): "FAIL",
            ("none-opencode-native", 2): "INCOMPLETE",
            ("hashmarks-opencode-native", 0): "PASS",
            ("hashmarks-opencode-native", 1): "PASS",
            ("hashmarks-opencode-native", 2): "FAIL",
            ("enola-opencode-native", 0): "FAIL",
            ("enola-opencode-native", 1): "PASS",
            ("enola-opencode-native", 2): "PASS",
        }
        projection = LiveTaskMatrix(suite, rows)

        rendered = None
        for row in rows:
            value = projection.record(
                row,
                self._receipt(
                    suite,
                    row,
                    statuses[(row["condition_id"], row["trial"])],
                    invoked=(
                        row["trial"] != 2
                        if row["condition_id"] == "hashmarks-opencode-native"
                        else None
                    ),
                    subject_mcp_calls=(
                        row["trial"] + 1
                        if row["condition_id"] == "hashmarks-opencode-native"
                        and row["trial"] != 2
                        else 0
                    ),
                    tool_names=(
                        ["task_evidence", "find"]
                        if row["condition_id"] == "hashmarks-opencode-native"
                        and row["trial"] != 2
                        else []
                    ),
                    tool_observability=(
                        "complete"
                        if row["condition_id"] == "hashmarks-opencode-native"
                        else None
                    ),
                ),
            )
            if value is not None:
                self.assertIsNone(rendered)
                rendered = value

        self.assertIsNotNone(rendered)
        assert rendered is not None
        self.assertIn(
            "RESULT locate-prefix-path-enumerator [opencode-native]",
            rendered,
        )
        self.assertIn(
            "Replicate ID | Bare       | Hashmarks | Enola",
            rendered,
        )
        self.assertIn(
            "6201         | FAIL       | PASS      | FAIL ",
            rendered,
        )
        self.assertIn(
            "6202         | FAIL       | PASS      | PASS ",
            rendered,
        )
        self.assertIn(
            "6203         | INCOMPLETE | FAIL      | PASS ",
            rendered,
        )
        self.assertIn("Paired vs Bare", rendered)
        self.assertIn(
            "Hashmarks | 2    | 0         | 0          | 0          | 1",
            rendered,
        )
        self.assertIn(
            "Enola     | 1    | 0         | 1          | 0          | 1",
            rendered,
        )
        self.assertIn("Subject tool use", rendered)
        self.assertIn(
            "Hashmarks | 2       | 1           | 0       | 3",
            rendered,
        )
        self.assertIn(
            "Enola     | 0       | 0           | 3       | 0",
            rendered,
        )

    def test_progress_reports_step_elapsed_remaining_and_eta(self) -> None:
        suite, rows = self._prefix_opencode_rows()
        progress = LiveCampaignProgress(
            suite, rows, self._status(rows, complete=[rows[1]["definition_id"]])
        )
        start = progress.start_line(rows[0], elapsed=65.0)
        self.assertIn("[1/9 this run]", start)
        self.assertIn("task 1/1 locate-prefix-path-enumerator", start)
        self.assertIn("replicate 1/3", start)
        self.assertIn("run elapsed 1m05s", start)
        self.assertIn("verified 1/9", start)
        self.assertIn("pending 8", start)
        self.assertIn("execution ETA estimating...", start)

        executed = TrialRunResult(
            trial_id="a" * 64,
            definition_id=rows[0]["definition_id"],
            status="PASS",
            result_dir=Path("/tmp/result"),
            reused=False,
        )
        finished = progress.finish_line(
            executed,
            elapsed=125.0,
            trial_seconds=60.0,
        )
        self.assertIn("PROGRESS processed 1/9 (11.1%)", finished)
        self.assertIn("verified 2/9", finished)
        self.assertIn("executed", finished)
        self.assertIn("avg 1m00s/execution", finished)
        self.assertIn("execution ETA 7m00s", finished)

        reused = TrialRunResult(
            trial_id="c" * 64,
            definition_id=rows[1]["definition_id"],
            status="PASS",
            result_dir=Path("/tmp/reused"),
            reused=True,
        )
        resumed = progress.finish_line(
            reused,
            elapsed=126.0,
            trial_seconds=0.1,
        )
        self.assertIn("reused", resumed)
        self.assertIn("verified 2/9", resumed)
        self.assertIn("avg 1m00s/execution", resumed)
        self.assertIn("execution ETA 7m00s", resumed)

    def test_eta_uses_condition_specific_runtime_samples(self) -> None:
        suite, rows = self._prefix_opencode_rows()
        progress = LiveCampaignProgress(suite, rows, self._status(rows))

        for row, seconds in ((rows[0], 60.0), (rows[1], 60.0), (rows[3], 180.0)):
            progress.finish_line(
                TrialRunResult(
                    trial_id="a" * 64,
                    definition_id=row["definition_id"],
                    status="PASS",
                    result_dir=Path("/tmp/result"),
                    reused=False,
                ),
                elapsed=seconds,
                trial_seconds=seconds,
            )

        start = progress.start_line(rows[4], elapsed=300.0)
        self.assertIn("pending 6", start)
        self.assertIn("execution ETA 12m00s", start)

    def test_failure_envelope_is_agent_readable_and_preserves_diagnostic(self) -> None:
        _, rows = self._prefix_opencode_rows()
        result = TrialRunResult(
            trial_id="a" * 64,
            definition_id="b" * 64,
            status="INCOMPLETE",
            result_dir=Path("/tmp/evidence"),
            reused=False,
            reason="agent terminal event was turn.failed",
            stage="agent-execution",
            reason_code="agent-terminal-failed",
            diagnostic="Traceback (most recent call last):\nValueError: boom",
        )
        rendered = render_trial_failure(
            row=rows[0],
            subject="none",
            result=result,
        )
        assert rendered is not None
        self.assertIn("FAILURE locate-prefix-path-enumerator", rendered)
        self.assertIn("Replicate ordinal: 1", rendered)
        self.assertIn("Replicate ID: 6201", rendered)
        self.assertIn("Status: INCOMPLETE", rendered)
        self.assertIn("Stage: agent-execution", rendered)
        self.assertIn("Reason code: agent-terminal-failed", rendered)
        self.assertIn("Evidence: /tmp/evidence", rendered)
        self.assertIn("--- diagnostic ---", rendered)
        self.assertIn("ValueError: boom", rendered)

    def test_recovered_failure_explicitly_says_model_was_not_retried(self) -> None:
        _, rows = self._prefix_opencode_rows()
        result = TrialRunResult(
            trial_id="a" * 64,
            definition_id="b" * 64,
            status="INCOMPLETE",
            result_dir=Path("/tmp/evidence"),
            reused=False,
            reason="previous trial launch was interrupted before a complete receipt",
            stage="campaign-recovery",
            reason_code="interrupted-launch",
            recovered=True,
        )
        rendered = render_trial_failure(
            row=rows[0],
            subject="none",
            result=result,
        )
        assert rendered is not None
        self.assertIn("Recovery: prior interrupted launch sealed", rendered)
        self.assertIn("model was not retried", rendered)

    def test_does_not_render_until_selected_task_agent_group_is_complete(self) -> None:
        suite, rows = self._prefix_opencode_rows()
        projection = LiveTaskMatrix(suite, rows)

        for row in rows[:-1]:
            self.assertIsNone(projection.record(row, self._receipt(suite, row, "PASS")))

        self.assertIsNotNone(
            projection.record(rows[-1], self._receipt(suite, rows[-1], "PASS"))
        )

    def test_ungradeable_fail_is_excluded_from_live_pairs(self) -> None:
        suite, rows = self._prefix_opencode_rows()
        projection = LiveTaskMatrix(suite, rows)
        rendered = None
        for row in rows:
            gradeable = not (row["condition_id"] == "none-opencode-native" and row["trial"] == 0)
            status = "FAIL" if row["condition_id"] == "none-opencode-native" else "PASS"
            rendered = projection.record(
                row, self._receipt(suite, row, status, gradeable=gradeable)
            ) or rendered
        assert rendered is not None
        self.assertIn("6201         | UNGRADABLE", rendered)
        self.assertIn("Hashmarks | 2    | 0         | 0          | 0          | 1", rendered)

    def test_same_subject_conditions_have_distinct_columns(self) -> None:
        suite, original = self._prefix_opencode_rows()
        experiment = copy.deepcopy(suite.experiment)
        extra = copy.deepcopy(next(
            item for item in experiment["conditions"]
            if item["id"] == "hashmarks-opencode-native"
        ))
        extra["id"] = "hashmarks-opencode-extra"
        experiment["conditions"].append(extra)
        expanded_suite = SuiteDefinition(
            suite.root, experiment, suite.tasks, suite.subjects, suite.agents
        )
        rows = [
            row for row in expanded_suite.trial_definitions()
            if row["task_id"] == original[0]["task_id"]
            and row["condition_id"].endswith("opencode-native")
            or row["task_id"] == original[0]["task_id"]
            and row["condition_id"] == extra["id"]
        ]
        projection = LiveTaskMatrix(expanded_suite, rows)
        rendered = None
        for row in rows:
            rendered = projection.record(
                row, self._receipt(expanded_suite, row, "PASS")
            ) or rendered
        assert rendered is not None
        self.assertIn("Hashmarks (hashmarks-opencode-native)", rendered)
        self.assertIn("Hashmarks (hashmarks-opencode-extra)", rendered)

    def test_heartbeat_reports_stage_only_after_interval(self) -> None:
        suite, rows = self._prefix_opencode_rows()
        progress = LiveCampaignProgress(suite, rows, self._status(rows))
        now = [100.0]
        emitted = []
        heartbeat = TrialHeartbeat(
            progress=progress,
            row=rows[0],
            run_started=90.0,
            emit=emitted.append,
            interval=30.0,
            clock=lambda: now[0],
        )
        self.assertIsNone(heartbeat.tick(129.0))
        heartbeat.update_stage("agent-execution")
        line = heartbeat.tick(130.0)
        assert line is not None
        self.assertIn("stage agent-execution", line)
        self.assertIn("trial elapsed 30s", line)
        self.assertIn("verified 0/9", line)
        self.assertIsNone(heartbeat.tick(131.0))
        heartbeat.__exit__(None, None, None)
        self.assertIsNone(heartbeat.tick(160.0))
        self.assertEqual(emitted, [])


if __name__ == "__main__":
    unittest.main()
