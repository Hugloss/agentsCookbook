from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = ROOT / "Makefile"
ENV_EXAMPLE = ROOT / ".env.example"


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
        self.assertNotIn("python -m benchmarks run", result.stdout)

    def test_make_dry_run_transports_explicit_env_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(
                "HASHMARKS_BENCH_SOURCE=/work/Hashmarks\n"
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
            'HASHMARKS_BENCH_SOURCE="/work/Hashmarks"',
            result.stdout,
        )
        self.assertIn('--suite "benchmarks/suites/example"', result.stdout)
        self.assertIn('--root "/work/campaign"', result.stdout)
        self.assertIn('--harness-root "/work/agentsCookbook"', result.stdout)


if __name__ == "__main__":
    unittest.main()
