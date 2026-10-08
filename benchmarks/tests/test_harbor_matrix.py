"""Contracts for the experimental Harbor cross-harness projection."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from benchmarks.harbor_matrix import (
    MATRIX_SCHEMA,
    REPORT_SCHEMA,
    HarborSettings,
    MatrixMode,
    build_report,
    harbor_argv,
    load_matrix,
    plan_rows,
    preflight,
    write_mcp_config,
)
from benchmarks.config import BenchmarkConfig
from benchmarks.harness.harbor_backend import credential_file, settings_from_config
from benchmarks.matrix_profiles import load_profile
from benchmarks.harness.suite import load_suite


ROOT = Path(__file__).resolve().parents[2]
MATRIX = (
    ROOT
    / "benchmarks"
    / "harbor"
    / "repository-intelligence-v1.json"
)
SUITE = (
    ROOT
    / "benchmarks"
    / "suites"
    / "repository-intelligence"
    / "heldout-v1"
)


class HarborMatrixTests(unittest.TestCase):
    def test_checked_in_matrix_has_small_smoke_and_paired_matrix(self) -> None:
        matrix = load_matrix(MATRIX)

        self.assertEqual(
            matrix["schema"],
            MATRIX_SCHEMA,
        )
        self.assertEqual(
            matrix["subjects"],
            ["none", "hashmarks"],
        )
        self.assertEqual(
            matrix["harnesses"],
            ["opencode", "codex", "claude-code"],
        )
        self.assertEqual(
            matrix["modes"]["smoke"],
            {
                "tasks": ["locate-prefix-path-enumerator"],
                "attempts": 1,
            },
        )
        self.assertEqual(
            matrix["modes"]["matrix"]["attempts"],
            3,
        )

    def test_plan_pairs_bare_and_hashmarks_per_harness(self) -> None:
        rows = plan_rows(
            harnesses=("opencode", "codex"),
            tasks=("task-a",),
            attempts=2,
        )

        self.assertEqual(len(rows), 8)
        self.assertEqual(
            {
                (
                    row["harness"],
                    row["subject"],
                    row["attempt"],
                )
                for row in rows
            },
            {
                ("opencode", "none", 1),
                ("opencode", "none", 2),
                ("opencode", "hashmarks", 1),
                ("opencode", "hashmarks", 2),
                ("codex", "none", 1),
                ("codex", "none", 2),
                ("codex", "hashmarks", 1),
                ("codex", "hashmarks", 2),
            },
        )

    def test_hashmarks_is_a_runtime_mcp_overlay_not_a_different_task_image(
        self,
    ) -> None:
        settings = HarborSettings(
            executable="harbor",
            model="provider/model",
            root=Path("/runs"),
            hashmarks_source=Path("/hashmarks"),
            passthrough_env_keys=(),
        )
        task = Path("/tasks/localize")
        jobs = Path("/runs/jobs")
        mcp = Path("/runs/hashmarks.mcp.json")

        bare = harbor_argv(
            settings=settings,
            task_path=task,
            harness="codex",
            trial_id="bare",
            jobs_root=jobs,
            credential_file=None,
            mcp_config=None,
        )
        treated = harbor_argv(
            settings=settings,
            task_path=task,
            harness="codex",
            trial_id="treated",
            jobs_root=jobs,
            credential_file=None,
            mcp_config=mcp,
        )

        self.assertEqual(
            bare[bare.index("-p") + 1],
            treated[treated.index("-p") + 1],
        )
        self.assertNotIn("--mcp-config", bare)
        self.assertEqual(
            treated[treated.index("--mcp-config") + 1],
            str(mcp),
        )

    def test_mcp_config_is_trial_scoped_stdio_with_explicit_workspace(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_mcp_config(Path(tmp) / "hashmarks.mcp.json")
            value = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            value,
            {
                "mcpServers": {
                    "hashmarks": {
                        "command": "hashmarks",
                        "args": [
                            "--workspace",
                            "/workspace",
                            "--state-dir",
                            "/tmp/hashmarks-state",
                            "mcp",
                        ],
                    }
                }
            },
        )

    def test_settings_keep_secret_values_out_of_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = root / ".env"
            env.write_text(
                "\n".join(
                    (
                        f"HASHMARKS_BENCH_SOURCE={root / 'Hashmarks'}",
                        "BENCHMARK_HARBOR_MODEL=provider/model",
                        "BENCHMARK_PASSTHROUGH_ENV_KEYS=OPENAI_API_KEY",
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            with mock.patch(
                "benchmarks.harness.harbor_backend.shutil.which",
                return_value="/usr/bin/tool",
            ):
                settings = settings_from_config(
                    BenchmarkConfig.load(
                        env,
                        host={"OPENAI_API_KEY": "secret-value", "PATH": "/bin"},
                    ),
                    load_profile("harbor-smoke"),
                )

        self.assertEqual(
            settings.passthrough_env_keys,
            ("OPENAI_API_KEY",),
        )
        self.assertNotIn(
            "secret-value",
            repr(settings),
        )

    def test_harbor_credential_file_is_private_and_replaced_on_resume(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings = HarborSettings(
                executable="harbor",
                model="provider/model",
                root=root,
                hashmarks_source=root,
                passthrough_env_keys=("OPENAI_API_KEY",),
            )
            first = credential_file(
                root, settings=settings, host={"OPENAI_API_KEY": "first"},
            )
            self.assertEqual(first.stat().st_mode & 0o777, 0o600)
            self.assertIn("first", first.read_text(encoding="utf-8"))
            second = credential_file(
                root, settings=settings, host={"OPENAI_API_KEY": "second"},
            )
            self.assertEqual(second, first)
            self.assertEqual(second.stat().st_mode & 0o777, 0o600)
            self.assertNotIn("first", second.read_text(encoding="utf-8"))

    def test_preflight_is_model_free_and_binds_hashmarks_contract(self) -> None:
        suite = load_suite(SUITE)
        settings = HarborSettings(
            executable="harbor",
            model="provider/model",
            root=Path("/runs"),
            hashmarks_source=Path("/hashmarks"),
            passthrough_env_keys=("OPENAI_API_KEY",),
        )
        matrix = load_matrix(MATRIX)
        mode = MatrixMode(
            tasks=("locate-prefix-path-enumerator",),
            attempts=1,
        )

        with (
            mock.patch(
                "benchmarks.harbor_matrix._hashmarks_identity",
                return_value={
                    "commit": "a" * 40,
                    "tree": "b" * 40,
                    "working_copy_sha256": "c" * 64,
                    "working_copy_clean": True,
                    "executable": {
                        "path": "/hashmarks/.venv/bin/hashmarks",
                        "sha256": "d" * 64,
                        "version": "hashmarks version 0.test",
                    },
                },
            ),
            mock.patch(
                "benchmarks.harbor_matrix._hashmarks_probe",
                return_value={
                    "contract_identity": "sha256:mcp",
                    "operation_contract_identity": "sha256:ops",
                    "tool_count": 8,
                },
            ),
            mock.patch(
                "benchmarks.harbor_matrix._require_command",
                side_effect=("harbor 0.test", "27.0"),
            ) as command,
        ):
            receipt = preflight(
                settings=settings,
                matrix=matrix,
                suite=suite,
                mode=mode,
                harnesses=("opencode",),
                tasks=("locate-prefix-path-enumerator",),
                host={"OPENAI_API_KEY": "secret-value"},
            )

        self.assertTrue(receipt["ready"])
        self.assertEqual(
            receipt["hashmarks"]["mcp_contract_identity"],
            "sha256:mcp",
        )
        self.assertEqual(
            receipt["hashmarks"]["executable"]["sha256"],
            "d" * 64,
        )
        self.assertEqual(
            receipt["trials"],
            2,
        )
        self.assertFalse(
            receipt["secrets_in_receipt"],
        )
        self.assertNotIn(
            "secret-value",
            json.dumps(receipt),
        )
        self.assertEqual(
            command.call_count,
            2,
        )

    def test_report_calculates_hashmarks_uplift_and_harness_spread(self) -> None:
        rows = []
        for harness, bare, treated in (
            ("opencode", (True, False), (True, True)),
            ("codex", (False, False), (True, True)),
        ):
            for subject, outcomes in (
                ("none", bare),
                ("hashmarks", treated),
            ):
                for attempt, success in enumerate(outcomes, 1):
                    rows.append(
                        {
                            "harness": harness,
                            "subject": subject,
                            "attempt": attempt,
                            "status": "COMPLETE",
                            "success": success,
                        }
                    )

        report = build_report(rows)

        self.assertEqual(
            report["schema"],
            REPORT_SCHEMA,
        )
        self.assertEqual(
            report["hashmarks_uplift"],
            {
                "codex": 1.0,
                "opencode": 0.5,
            },
        )
        self.assertEqual(
            report["harness_spread"],
            {
                "bare": 0.5,
                "hashmarks": 0.0,
                "reduction": 0.5,
                "reduction_fraction": 1.0,
            },
        )


if __name__ == "__main__":
    unittest.main()
