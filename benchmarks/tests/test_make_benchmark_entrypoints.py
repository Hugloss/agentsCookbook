"""Observable contracts for the thin Make benchmark entrypoints."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from benchmarks.__main__ import main

ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = ROOT / "Makefile"
ENV_EXAMPLE = ROOT / ".env.example"


class BenchmarkMakeEntrypointTests(unittest.TestCase):
    def test_make_delegates_configuration_to_cli(self) -> None:
        makefile = MAKEFILE.read_text(encoding="utf-8")
        self.assertNotIn("-include .env", makefile)
        self.assertNotIn("awk -F=", makefile)
        for target, command in (
            ("benchmark-check", "check"),
            ("benchmark-check-all", "preflight"),
            ("benchmark", "run"),
            ("benchmark-report", "report"),
            ("benchmark-score", "score"),
        ):
            with self.subTest(target=target):
                self.assertIn(
                    f"{target}:\n\t@uv run --no-project python -m benchmarks {command} --env-file .env",
                    makefile,
                )
        self.assertNotIn("release-check:", makefile)
        self.assertIn("BENCHMARK_AGENT=\n", ENV_EXAMPLE.read_text(encoding="utf-8"))

    def test_make_dry_run_does_not_expand_configuration_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(
                "BENCHMARK_AGENT=codex-native,opencode-native\n"
                "BENCHMARK_SUITE_PATH=private-suite\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                ("make", "-n", "-f", str(MAKEFILE), "benchmark"),
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--env-file .env", result.stdout)
        self.assertNotIn("private-suite", result.stdout)
        self.assertNotIn("codex-native", result.stdout)

    def test_missing_env_file_fails_before_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / ".env"
            with self.assertRaisesRegex(
                SystemExit, "benchmark env file does not exist"
            ):
                main(["run", "--env-file", str(file)])
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_missing_agent_fails_even_with_explicit_cli_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / ".env"
            file.write_text(
                "BENCHMARK_SUITE_PATH=benchmarks/suites/repository-intelligence/heldout-v1\n"
                "BENCHMARK_CAMPAIGN_ROOT=/tmp/unused-campaign\n"
                "BENCHMARK_HARNESS_REPO_ROOT=.\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SystemExit, "BENCHMARK_AGENT"):
                main(["run", "--env-file", str(file), "--agent", "codex-native"])
