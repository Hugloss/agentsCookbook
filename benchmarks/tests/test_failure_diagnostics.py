from __future__ import annotations

import unittest

from benchmarks.adapters.opencode_native import _run_failure_diagnostic
from benchmarks.harness.model import Observation
from benchmarks.harness.runner import _agent_failure_diagnostic


class FailureDiagnosticTests(unittest.TestCase):
    def test_runner_prefers_preserved_adapter_diagnostic(self) -> None:
        observation = Observation(
            {
                "failure_diagnostic": (
                    "OpenCode export diagnostic:\n"
                    "Error: opencode export: terminal assistant message has no final text\n"
                    "    at extractFinalAnswer"
                )
            },
            "",
        )

        diagnostic = _agent_failure_diagnostic(
            observation,
            reason="agent terminal event was turn.failed",
        )

        self.assertIn("OpenCode export diagnostic", diagnostic)
        self.assertIn("at extractFinalAnswer", diagnostic)
        self.assertNotEqual(diagnostic, "agent terminal event was turn.failed")

    def test_runner_exception_traceback_remains_highest_priority(self) -> None:
        observation = Observation(
            {"failure_diagnostic": "adapter diagnostic"},
            "",
        )

        diagnostic = _agent_failure_diagnostic(
            observation,
            reason="terminal failure",
            exception_traceback="Traceback (most recent call last):\nValueError: boom",
        )

        self.assertEqual(
            diagnostic,
            "Traceback (most recent call last):\nValueError: boom",
        )

    def test_opencode_failure_diagnostic_preserves_export_stack_and_run_stderr(
        self,
    ) -> None:
        diagnostic = _run_failure_diagnostic(
            {
                "status": 0,
                "stdout": '{"type":"run"}',
                "stderr": "provider stack line",
                "error": None,
                "signal": None,
            },
            export_diagnostic=(
                "Error: opencode export: terminal assistant message has no final text\n"
                "    at extractFinalAnswer"
            ),
            runtime_stderr="",
        )

        assert diagnostic is not None
        self.assertIn("OpenCode export diagnostic", diagnostic)
        self.assertIn("at extractFinalAnswer", diagnostic)
        self.assertIn("OpenCode run stderr", diagnostic)
        self.assertIn("provider stack line", diagnostic)

    def test_opencode_nonzero_falls_back_to_bounded_stdout_tail(self) -> None:
        diagnostic = _run_failure_diagnostic(
            {
                "status": 17,
                "stdout": "x" * 3000 + "tail-marker",
                "stderr": "",
                "error": None,
                "signal": None,
            },
            export_diagnostic=None,
            runtime_stderr=None,
        )

        assert diagnostic is not None
        self.assertIn("OpenCode run stdout tail", diagnostic)
        self.assertIn("tail-marker", diagnostic)
        self.assertLess(len(diagnostic), 2200)


if __name__ == "__main__":
    unittest.main()
