from __future__ import annotations

import unittest
from pathlib import Path

from benchmarks.harness.live_console import LiveTaskMatrix
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

    def test_does_not_render_until_selected_task_agent_group_is_complete(self) -> None:
        suite, rows = self._prefix_opencode_rows()
        projection = LiveTaskMatrix(suite, rows)

        for row in rows[:-1]:
            self.assertIsNone(projection.record(row, "PASS"))

        self.assertIsNotNone(projection.record(rows[-1], "PASS"))


if __name__ == "__main__":
    unittest.main()
