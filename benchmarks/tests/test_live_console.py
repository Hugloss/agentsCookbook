from __future__ import annotations

import unittest
from pathlib import Path

from benchmarks.harness.live_console import (
    LiveCampaignProgress,
    LiveTaskMatrix,
    render_trial_failure,
)
from benchmarks.harness.runner import TrialRunResult
from benchmarks.harness.suite import load_suite


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
                statuses[(row["condition_id"], row["trial"])],
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
            "Replicate | Bare       | Hashmarks | Enola",
            rendered,
        )
        self.assertIn(
            "0         | FAIL       | PASS      | FAIL ",
            rendered,
        )
        self.assertIn(
            "1         | FAIL       | PASS      | PASS ",
            rendered,
        )
        self.assertIn(
            "2         | INCOMPLETE | FAIL      | PASS ",
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

    def test_progress_reports_step_elapsed_remaining_and_eta(self) -> None:
        suite, rows = self._prefix_opencode_rows()
        progress = LiveCampaignProgress(suite, rows)
        start = progress.start_line(rows[0], elapsed=65.0)
        self.assertIn("[1/9]", start)
        self.assertIn("task 1/1 locate-prefix-path-enumerator", start)
        self.assertIn("replicate 1/3", start)
        self.assertIn("elapsed 1m05s", start)
        self.assertIn("remaining 9", start)
        self.assertIn("ETA estimating...", start)

        executed = TrialRunResult(
            trial_id="a" * 64,
            definition_id="b" * 64,
            status="PASS",
            result_dir=Path("/tmp/result"),
            reused=False,
        )
        finished = progress.finish_line(
            executed,
            elapsed=125.0,
            trial_seconds=60.0,
        )
        self.assertIn("PROGRESS 1/9 (11.1%)", finished)
        self.assertIn("executed", finished)
        self.assertIn("avg 1m00s/trial", finished)
        self.assertIn("ETA 8m00s", finished)

        reused = TrialRunResult(
            trial_id="c" * 64,
            definition_id="d" * 64,
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
        self.assertIn("avg 1m00s/trial", resumed)
        self.assertIn("ETA 7m00s", resumed)

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
            self.assertIsNone(projection.record(row, "PASS"))

        self.assertIsNotNone(projection.record(rows[-1], "PASS"))


if __name__ == "__main__":
    unittest.main()
