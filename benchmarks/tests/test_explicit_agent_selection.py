from __future__ import annotations

import unittest

from benchmarks.__main__ import _parser


class ExplicitAgentSelectionTests(unittest.TestCase):
    def test_check_requires_agent(self) -> None:
        with self.assertRaises(SystemExit):
            _parser().parse_args(
                ["check", "--suite", "suite", "--env-file", ".env"]
            )

    def test_preflight_requires_agent(self) -> None:
        with self.assertRaises(SystemExit):
            _parser().parse_args(
                [
                    "preflight",
                    "--suite",
                    "suite",
                    "--harness-root",
                    ".",
                ]
            )

    def test_run_requires_agent(self) -> None:
        with self.assertRaises(SystemExit):
            _parser().parse_args(
                [
                    "run",
                    "--suite",
                    "suite",
                    "--harness-root",
                    ".",
                ]
            )

    def test_run_accepts_explicit_agent(self) -> None:
        args = _parser().parse_args(
            [
                "run",
                "--suite",
                "suite",
                "--harness-root",
                ".",
                "--agent",
                "opencode-native",
            ]
        )
        self.assertEqual(args.agent, ["opencode-native"])


if __name__ == "__main__":
    unittest.main()
