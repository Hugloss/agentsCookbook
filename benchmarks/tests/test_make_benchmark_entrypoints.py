from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = ROOT / "Makefile"
ENV_EXAMPLE = ROOT / ".env.example"
PYTHON_VERSION = ROOT / ".python-version"
VALIDATE_WORKFLOW = ROOT / ".github" / "workflows" / "validate.yml"
BENCHMARK_README = ROOT / "benchmarks" / "README.md"
HELDOUT_README = (
    ROOT
    / "benchmarks"
    / "suites"
    / "repository-intelligence"
    / "heldout-v1"
    / "README.md"
)


@unittest.skipUnless(shutil.which("make"), "make is required for Makefile regressions")
class BenchmarkMakeEntrypointTests(unittest.TestCase):
    def test_makefile_contains_no_hidden_benchmark_authority_defaults(self) -> None:
        makefile = MAKEFILE.read_text(encoding="utf-8")
        env_example = ENV_EXAMPLE.read_text(encoding="utf-8")

        self.assertNotIn(
            "benchmarks/suites/repository-intelligence/heldout-v1",
            makefile,
        )
        self.assertNotIn("/tmp/agentscookbook-heldout-v1", makefile)
        self.assertNotIn("/absolute/path/to/Hashmarks", makefile)
        self.assertNotIn("--harness-root .", makefile)

        self.assertIn(
            "BENCHMARK_SUITE_PATH=benchmarks/suites/repository-intelligence/heldout-v1",
            env_example,
        )
        self.assertIn(
            "BENCHMARK_CAMPAIGN_ROOT=/tmp/agentscookbook-heldout-v1",
            env_example,
        )
        self.assertIn(
            "HASHMARKS_BENCH_SOURCE=/absolute/path/to/Hashmarks",
            env_example,
        )
        self.assertIn("BENCHMARK_HARNESS_REPO_ROOT=.", env_example)
        for native_path_setting in (
            "ENOLA_BENCH_EXECUTABLE=",
            "BENCHMARK_CODEX_EXECUTABLE=",
            "BENCHMARK_CODEX_HOME=",
            "BENCHMARK_OPENCODE_EXECUTABLE=",
            "BENCHMARK_OPENCODE_HOME=",
            "BENCHMARK_OPENCODE_CONFIG_HOME=",
        ):
            self.assertNotIn(native_path_setting, env_example)
        self.assertIn("BENCHMARK_AGENT=opencode-native", env_example)
        self.assertIn("BENCHMARK_OPENCODE_AGENT=build", env_example)
        self.assertIn("BENCHMARK_PASSTHROUGH_ENV_KEYS=", env_example)
        self.assertIn(
            "BENCHMARK_SCORE_SCRIPT_PATH=benchmarks/suites/repository-intelligence/heldout-v1/score.py",
            env_example,
        )
        self.assertIn(
            "BENCHMARK_SCORE_OUTPUT_PATH=/tmp/agentscookbook-heldout-v1/heldout-report.json",
            env_example,
        )

        # Do not drift back to ambiguous names that hide whether a path is
        # committed source/configuration or generated campaign state.
        self.assertNotIn("\nBENCHMARK_SUITE=", env_example)
        self.assertNotIn("\nBENCHMARK_ROOT=", env_example)
        self.assertNotIn("\nBENCHMARK_HARNESS_ROOT=", env_example)

    def test_repository_python_entrypoints_are_uv_owned(self) -> None:
        makefile = MAKEFILE.read_text(encoding="utf-8")
        workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
        benchmark_docs = BENCHMARK_README.read_text(encoding="utf-8")
        heldout_docs = HELDOUT_README.read_text(encoding="utf-8")

        self.assertEqual(PYTHON_VERSION.read_text(encoding="utf-8"), "3.11\n")

        for target in (
            "benchmark-check",
            "benchmark-check-all",
            "benchmark",
            "benchmark-report",
            "benchmark-score",
        ):
            self.assertIn(target, makefile)
        self.assertIn("uv run --no-project python -m benchmarks", makefile)
        self.assertIn(
            'uv run --no-project python "$(BENCHMARK_SCORE_SCRIPT_PATH)"',
            makefile,
        )
        self.assertNotIn("\n\t@python ", makefile)

        self.assertIn("uses: astral-sh/setup-uv@", workflow)
        self.assertIn("run: uv python install", workflow)
        self.assertNotIn("uses: actions/setup-python@", workflow)
        self.assertNotIn("run: python ", workflow)
        self.assertNotIn("\n          python ", workflow)
        self.assertNotIn('PYTHONPATH="$PWD/scripts" python ', workflow)
        self.assertNotIn(' STAGE="$stage/agent-economics" python ', workflow)

        self.assertNotIn("\npython -m benchmarks", benchmark_docs)
        self.assertNotIn("\npython -m benchmarks", heldout_docs)
        self.assertIn(
            "uv run --no-project python -m benchmarks",
            benchmark_docs,
        )
        self.assertIn(
            "uv run --no-project python -m benchmarks",
            heldout_docs,
        )

    def test_fast_check_is_not_trial_preflight(self) -> None:
        makefile = MAKEFILE.read_text(encoding="utf-8")

        check_block = makefile.split(
            "benchmark-check: _benchmark-agent-env", 1
        )[1].split(
            "benchmark-check-all: _benchmark-execution-env", 1
        )[0]
        self.assertIn(
            "uv run --no-project python -m benchmarks check",
            check_block,
        )
        self.assertIn("--env-file .env", check_block)
        self.assertIn("--suite", check_block)
        self.assertIn('--agent "$(BENCHMARK_AGENT)"', check_block)
        self.assertNotIn("--root", check_block)
        self.assertNotIn("--harness-root", check_block)
        self.assertNotIn("preflight", check_block)

        exhaustive = makefile.split(
            "benchmark-check-all: _benchmark-execution-env", 1
        )[1].split(
            "benchmark: _benchmark-execution-env", 1
        )[0]
        self.assertIn(
            "uv run --no-project python -m benchmarks preflight",
            exhaustive,
        )
        self.assertIn("--root", exhaustive)
        self.assertIn("--harness-root", exhaustive)

        benchmark_block = makefile.split(
            "benchmark: _benchmark-execution-env", 1
        )[1].split(
            "benchmark-report: _benchmark-selected-campaign-env", 1
        )[0]
        self.assertNotIn("benchmark-check", benchmark_block)
        self.assertNotIn("preflight", benchmark_block)
        self.assertIn('--agent "$(BENCHMARK_AGENT)"', benchmark_block)

        report_block = makefile.split(
            "benchmark-report: _benchmark-selected-campaign-env", 1
        )[1].split(
            "_benchmark-score-env: _benchmark-selected-campaign-env", 1
        )[0]
        self.assertNotIn("--harness-root", report_block)
        self.assertIn('--agent "$(BENCHMARK_AGENT)"', report_block)

    def test_make_benchmark_fails_before_execution_without_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                (
                    "make",
                    "--no-print-directory",
                    "-f",
                    str(MAKEFILE),
                    "benchmark",
                ),
                cwd=tmp,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ERROR: .env is required.", result.stdout)
        self.assertNotIn(
            "uv run --no-project python -m benchmarks run",
            result.stdout,
        )

    def test_make_benchmark_fails_closed_without_explicit_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(
                "BENCHMARK_SUITE_PATH=benchmarks/suites/example\n"
                "BENCHMARK_CAMPAIGN_ROOT=/work/campaign\n"
                "BENCHMARK_HARNESS_REPO_ROOT=/work/agentsCookbook\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                (
                    "make",
                    "--no-print-directory",
                    "-f",
                    str(MAKEFILE),
                    "benchmark",
                ),
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "BENCHMARK_AGENT must explicitly select the benchmark agent",
            result.stdout,
        )
        self.assertNotIn(
            "uv run --no-project python -m benchmarks run",
            result.stdout,
        )

    def test_make_dry_run_transports_explicit_env_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(
                "HASHMARKS_BENCH_SOURCE=/work/Hashmarks\n"
                "BENCHMARK_AGENT=opencode-native\n"
                "BENCHMARK_SUITE_PATH=benchmarks/suites/example\n"
                "BENCHMARK_CAMPAIGN_ROOT=/work/campaign\n"
                "BENCHMARK_HARNESS_REPO_ROOT=/work/agentsCookbook\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                (
                    "make",
                    "--no-print-directory",
                    "-n",
                    "-f",
                    str(MAKEFILE),
                    "benchmark",
                ),
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn(
            "uv run --no-project python -m benchmarks run",
            result.stdout,
        )
        self.assertIn("--env-file .env", result.stdout)
        self.assertNotIn(
            'HASHMARKS_BENCH_SOURCE="/work/Hashmarks"',
            result.stdout,
        )
        self.assertIn('--suite "benchmarks/suites/example"', result.stdout)
        self.assertIn('--root "/work/campaign"', result.stdout)
        self.assertIn('--harness-root "/work/agentsCookbook"', result.stdout)
        self.assertIn('--agent "opencode-native"', result.stdout)

    def test_make_score_transports_explicit_score_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(
                "BENCHMARK_AGENT=opencode-native\n"
                "BENCHMARK_SUITE_PATH=benchmarks/suites/example\n"
                "BENCHMARK_CAMPAIGN_ROOT=/work/campaign\n"
                "BENCHMARK_HARNESS_REPO_ROOT=/work/agentsCookbook\n"
                "BENCHMARK_SCORE_SCRIPT_PATH=benchmarks/suites/example/score.py\n"
                "BENCHMARK_SCORE_OUTPUT_PATH=/work/campaign/special-report.json\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                (
                    "make",
                    "--no-print-directory",
                    "-n",
                    "-f",
                    str(MAKEFILE),
                    "benchmark-score",
                ),
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn(
            'uv run --no-project python "benchmarks/suites/example/score.py"',
            result.stdout,
        )
        self.assertIn('--results "/work/campaign/results"', result.stdout)
        self.assertIn(
            '--output "/work/campaign/special-report.json"',
            result.stdout,
        )
        self.assertIn('--agent "opencode-native"', result.stdout)


if __name__ == "__main__":
    unittest.main()
