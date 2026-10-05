from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout

from benchmarks.__main__ import _emit_run_results, _parser


class BenchmarkRunOutputTests(unittest.TestCase):
    def test_run_json_results_is_opt_in(self) -> None:
        default = _parser().parse_args(["run", "--new", "--env-file", ".env"])
        explicit = _parser().parse_args(
            ["run", "--new", "--env-file", ".env", "--json-results"]
        )

        self.assertFalse(default.json_results)
        self.assertTrue(explicit.json_results)

    def test_run_results_do_not_flood_stdout_by_default(self) -> None:
        results = [
            {
                "status": "INCOMPLETE",
                "reason_code": "agent-terminal-failed",
                "result_dir": "/tmp/evidence",
            }
        ]
        output = io.StringIO()

        with redirect_stdout(output):
            _emit_run_results(results, enabled=False)

        self.assertEqual(output.getvalue(), "")

    def test_run_results_can_still_be_emitted_explicitly(self) -> None:
        results = [{"status": "PASS", "trial_id": "abc"}]
        output = io.StringIO()

        with redirect_stdout(output):
            _emit_run_results(results, enabled=True)

        self.assertEqual(json.loads(output.getvalue()), results)


if __name__ == "__main__":
    unittest.main()
