"""Observable contracts for the thin Make benchmark entrypoints."""

from __future__ import annotations

import subprocess
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from benchmarks.__main__ import (
    _assert_saved_run_agents,
    _assert_saved_run_selection,
    _guard_automatic_start,
    main,
)
from benchmarks.harness.runner import TrialRunResult, TrialRunnerError
from benchmarks.harness.run_store import RunStoreError, SavedRun
from benchmarks.harness.selection import select_definitions
from benchmarks.harness.suite import load_suite

ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = ROOT / "Makefile"
ENV_EXAMPLE = ROOT / ".env.example"


class BenchmarkMakeEntrypointTests(unittest.TestCase):
    def test_local_campaign_example_is_durable_and_ignored(self) -> None:
        env_example = ENV_EXAMPLE.read_text(encoding="utf-8")
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8-sig")
        self.assertIn(
            "BENCHMARK_CAMPAIGN_ROOT=.benchmark-runs/heldout-v1",
            env_example,
        )
        self.assertIn(
            "BENCHMARK_SCORE_OUTPUT_PATH=score.json",
            env_example,
        )
        self.assertIn(".benchmark-runs/", gitignore)
        self.assertNotIn(
            "BENCHMARK_CAMPAIGN_ROOT=/tmp/agentscookbook-heldout-v1",
            env_example,
        )

    def test_make_delegates_configuration_to_cli(self) -> None:
        makefile = MAKEFILE.read_text(encoding="utf-8")
        self.assertNotIn("-include .env", makefile)
        self.assertNotIn("awk -F=", makefile)
        for target, command in (
            ("benchmark", "run --auto"),
            ("benchmark-check", "check"),
            ("benchmark-check-all", "preflight"),
            ("benchmark-new", "run --new"),
            ("benchmark-resume", "run --resume"),
            ("benchmark-status", "status"),
            ("benchmark-report", "report"),
            ("benchmark-reports", "reports"),
            ("benchmark-score", "score"),
        ):
            with self.subTest(target=target):
                self.assertIn(
                    f"{target}:\n\t@uv run --no-project python -m benchmarks {command} --env-file .env",
                    makefile,
                )
        self.assertIn("benchmark-oracle-review:", makefile)
        self.assertIn(
            "python -m benchmarks oracle-review \\\n"
            "\t\t--suite benchmarks/suites/repository-intelligence/heldout-v1 \\\n"
            "\t\t--execute",
            makefile,
        )
        self.assertIn("benchmark-qualify-localization:", makefile)
        self.assertIn(
            "mktemp -d .benchmark-runs/heldout-v1/qualification.XXXXXX",
            makefile,
        )
        self.assertIn('--root "$$qualification_root" --require-qualified', makefile)
        self.assertIn("--subject none --subject hashmarks --subject enola", makefile)
        self.assertIn("--task locate-repository-content-identity", makefile)
        self.assertIn("--task locate-terminal-run-check", makefile)
        self.assertNotIn("release-check:", makefile)
        self.assertIn("BENCHMARK_AGENT=\n", ENV_EXAMPLE.read_text(encoding="utf-8"))

    def test_score_agent_selection_must_match_frozen_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            saved = SavedRun("000001", Path(tmp) / "runs/000001")
            with mock.patch(
                "benchmarks.__main__.read_campaign",
                return_value={
                    "selected_definitions": [],
                    "agents": {"opencode-native": {}},
                },
            ):
                with self.assertRaisesRegex(
                    RunStoreError,
                    "agent selection does not match BENCHMARK_AGENT",
                ):
                    _assert_saved_run_agents(saved, ["codex-native"])

    def test_score_dispatches_exact_frozen_definition_selection(self) -> None:
        suite = ROOT / "benchmarks/suites/repository-intelligence/heldout-v1"
        score_script = suite / "score.py"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            saved = SavedRun("000001", root / "runs/000001")
            output = root / "score.json"
            config = mock.Mock()
            config.runtime_environment.return_value = {}
            manifest = {
                "selected_definitions": ["b" * 64, "a" * 64],
                "agents": {"opencode-native": {}},
            }

            with (
                mock.patch("benchmarks.__main__._resolve_config", return_value=config),
                mock.patch("benchmarks.__main__.select_saved_run", return_value=saved),
                mock.patch(
                    "benchmarks.__main__._assert_saved_run_agents",
                    return_value=manifest,
                ),
                mock.patch(
                    "benchmarks.__main__.verify_campaign_suite_authority"
                ) as verify_suite,
                mock.patch("benchmarks.__main__.subprocess.run") as run,
            ):
                run.return_value.returncode = 0
                run.return_value.stdout = (
                    "--results --output --agent --definition-id"
                )
                run.return_value.stderr = ""
                self.assertEqual(
                    main(
                        [
                            "score",
                            "--env-file",
                            str(root / "unused.env"),
                            "--suite",
                            str(suite),
                            "--root",
                            str(root),
                            "--score-script",
                            str(score_script),
                            "--output",
                            str(output),
                            "--agent",
                            "opencode-native",
                        ]
                    ),
                    0,
                )

            verify_suite.assert_called_once()
            self.assertIs(verify_suite.call_args.kwargs["campaign"], manifest)
            invocation = run.call_args.args[0]
            observed = [
                invocation[index + 1]
                for index, value in enumerate(invocation)
                if value == "--definition-id"
            ]
            self.assertEqual(observed, ["a" * 64, "b" * 64])

    def test_resume_selection_must_match_frozen_agents_before_admission(self) -> None:
        suite = load_suite(
            ROOT / "benchmarks/suites/repository-intelligence/heldout-v1"
        )
        rows = select_definitions(
            suite,
            tasks=("locate-prefix-path-enumerator",),
            agents=("opencode-native",),
        )
        with tempfile.TemporaryDirectory() as tmp:
            saved = SavedRun("000001", Path(tmp) / "runs/000001")
            with mock.patch(
                "benchmarks.__main__.read_campaign",
                return_value={
                    "selected_definitions": ["different"],
                    "agents": {"codex-native": {}},
                },
            ):
                with self.assertRaisesRegex(
                    RunStoreError,
                    "agent selection does not match BENCHMARK_AGENT",
                ):
                    _assert_saved_run_selection(
                        saved,
                        suite=suite,
                        rows=rows,
                    )

    def test_plain_benchmark_requires_explicit_choice_for_unfinished_match(self) -> None:
        suite = load_suite(
            ROOT / "benchmarks/suites/repository-intelligence/heldout-v1"
        )
        rows = select_definitions(
            suite,
            tasks=("locate-prefix-path-enumerator",),
            agents=("opencode-native",),
        )
        selected = [str(row["definition_id"]) for row in rows]
        with tempfile.TemporaryDirectory() as tmp:
            saved = SavedRun("000001", Path(tmp) / "runs/000001")
            with (
                mock.patch(
                    "benchmarks.__main__.list_saved_runs",
                    return_value=[saved],
                ),
                mock.patch(
                    "benchmarks.__main__.read_campaign",
                    return_value={
                        "selected_definitions": selected,
                        "agents": {"opencode-native": {}},
                    },
                ),
                mock.patch(
                    "benchmarks.__main__.campaign_status",
                    return_value={
                        "complete": False,
                        "complete_trials": 17,
                        "expected_trials": len(rows),
                        "pending_trials": len(rows) - 17,
                        "interrupted_trials": 0,
                    },
                ),
            ):
                with self.assertRaisesRegex(
                    RunStoreError,
                    "choose explicitly: make benchmark-resume or make benchmark-new",
                ):
                    _guard_automatic_start(Path(tmp), suite=suite, rows=rows)

    def test_plain_benchmark_starts_new_when_latest_selection_differs(self) -> None:
        suite = load_suite(
            ROOT / "benchmarks/suites/repository-intelligence/heldout-v1"
        )
        rows = select_definitions(
            suite,
            tasks=("locate-prefix-path-enumerator",),
            agents=("opencode-native",),
        )
        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(io.StringIO()):
            saved = SavedRun("000001", Path(tmp) / "runs/000001")
            with (
                mock.patch(
                    "benchmarks.__main__.list_saved_runs",
                    return_value=[saved],
                ),
                mock.patch(
                    "benchmarks.__main__.read_campaign",
                    return_value={
                        "selected_definitions": ["different"],
                        "agents": {"codex-native": {}},
                    },
                ),
            ):
                _guard_automatic_start(Path(tmp), suite=suite, rows=rows)

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
                main(["run", "--resume", "--env-file", str(file)])
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_status_and_report_are_persisted_in_shareable_reports_dir(self) -> None:
        suite_path = ROOT / "benchmarks/suites/repository-intelligence/heldout-v1"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_root = root / "runs/000001"
            results = run_root / "results"
            results.mkdir(parents=True)
            (results / "receipt").write_text("present", encoding="utf-8")
            saved = SavedRun("000001", run_root)

            status_payload = {
                "rows": [],
                "complete_trials": 108,
                "pending_trials": 0,
                "interrupted_trials": 0,
                "conflicting_trials": [],
                "corrupt_bundles": [],
                "foreign_bundles": [],
                "qualified": True,
            }
            with (
                mock.patch("benchmarks.__main__.select_saved_run", return_value=saved),
                mock.patch(
                    "benchmarks.__main__.campaign_status",
                    return_value=dict(status_payload),
                ),
                mock.patch(
                    "benchmarks.__main__._canonical_campaign_persistence_gap",
                    return_value=None,
                ),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(
                    main(["status", "--suite", str(suite_path), "--root", str(root)]),
                    0,
                )

            status_file = run_root / "reports/status.json"
            self.assertTrue(status_file.is_file())
            stored_status = json.loads(status_file.read_text(encoding="utf-8"))
            self.assertEqual(stored_status["run_id"], "000001")
            self.assertEqual(
                stored_status["paths"]["reports"],
                str(run_root / "reports"),
            )

            with (
                mock.patch("benchmarks.__main__.select_saved_run", return_value=saved),
                mock.patch(
                    "benchmarks.__main__.build_report",
                    return_value={"schema": {"version": 7}, "expected_trials": 108},
                ),
                mock.patch(
                    "benchmarks.__main__.build_trace_diagnostics",
                    return_value={"schema": "agents-cookbook-trace-diagnostics.v1", "trials": []},
                ),
                mock.patch(
                    "benchmarks.__main__._canonical_campaign_persistence_gap",
                    return_value=None,
                ),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(
                    main([
                        "report",
                        "--suite",
                        str(suite_path),
                        "--root",
                        str(root),
                        "--agent",
                        "opencode-native",
                    ]),
                    0,
                )

            report_file = run_root / "reports/report.json"
            self.assertTrue(report_file.is_file())
            stored_report = json.loads(report_file.read_text(encoding="utf-8"))
            self.assertEqual(stored_report["run_id"], "000001")
            self.assertEqual(
                stored_report["reports_dir"],
                str(run_root / "reports"),
            )
            decision_file = run_root / "reports/decision-evidence.json"
            self.assertTrue(decision_file.is_file())
            stored_decision = json.loads(
                decision_file.read_text(encoding="utf-8")
            )
            self.assertEqual(
                stored_decision["schema"],
                "agents-cookbook-benchmark-decision-evidence.v2",
            )
            self.assertEqual(stored_decision["run_id"], "000001")
            self.assertTrue(stored_decision["authority"]["derived_only"])
            trace_file = run_root / "reports/trace-diagnostics.json"
            self.assertTrue(trace_file.is_file())

    def test_status_can_require_qualified_campaign(self) -> None:
        suite = ROOT / "benchmarks/suites/repository-intelligence/heldout-v1"
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()):
            args = ["status", "--suite", str(suite), "--results", tmp]
            self.assertEqual(main(args), 0)
            self.assertEqual(main([*args, "--require-qualified"]), 2)

    def test_run_keeps_stdout_json_and_prints_verified_summary(self) -> None:
        suite_path = ROOT / "benchmarks/suites/repository-intelligence/heldout-v1"
        suite = load_suite(suite_path)
        rows = select_definitions(
            suite,
            tasks=("locate-prefix-path-enumerator",),
            agents=("opencode-native",),
            condition="hashmarks-opencode-native",
        )
        initial = {
            "rows": [
                {"definition_id": row["definition_id"], "state": "PENDING"}
                for row in rows
            ],
            "complete_trials": 0,
            "pending_trials": len(rows),
            "interrupted_trials": 0,
            "qualified": False,
            "outcomes": {},
        }
        final = {
            **initial,
            "complete_trials": len(rows),
            "pending_trials": 0,
            "qualified": True,
            "outcomes": {"PASS": len(rows)},
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = mock.Mock()
            config.runtime_environment.return_value = {}

            def fake_run(**kwargs):
                row = next(item for item in rows if item["trial"] == kwargs["trial_index"])
                result_dir = root / "results" / (str(row["trial"]) * 64)
                result_dir.mkdir(parents=True)
                (result_dir / "result.json").write_text(
                    json.dumps({"definition_id": row["definition_id"], "status": "PASS"}),
                    encoding="utf-8",
                )
                kwargs["on_progress"]("publication")
                return TrialRunResult(
                    trial_id=result_dir.name,
                    definition_id=str(row["definition_id"]),
                    status="PASS",
                    result_dir=result_dir,
                    reused=False,
                )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                mock.patch("benchmarks.__main__._resolve_config", return_value=config),
                mock.patch(
                    "benchmarks.__main__._validate_reporting_contract",
                    return_value=(suite_path / "score.py", Path("score.json")),
                ),
                mock.patch("benchmarks.__main__.select_saved_run", return_value=SavedRun("000001", root)),
                mock.patch("benchmarks.__main__._assert_saved_run_selection"),
                mock.patch("benchmarks.__main__.verify_saved_campaign", return_value={"campaign_id": "c" * 64}),
                mock.patch("benchmarks.__main__.campaign_status", side_effect=[initial, final]),
                mock.patch("benchmarks.__main__.run_trial", side_effect=fake_run),
                mock.patch(
                    "benchmarks.__main__._persist_completed_run_reports",
                    return_value={
                        "status": root / "reports/status.json",
                        "report": root / "reports/report.json",
                        "decision_evidence": root / "reports/decision-evidence.json",
                        "score": root / "reports/score.json",
                    },
                ) as persist_reports,
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                exit_code = main([
                    "run", "--resume", "--env-file", str(root / "unused.env"),
                    "--suite", str(suite_path), "--root", str(root),
                    "--harness-root", str(ROOT), "--task", "locate-prefix-path-enumerator",
                    "--agent", "opencode-native", "--condition", "hashmarks-opencode-native",
                ])
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(json.loads(stdout.getvalue())), 3)
        self.assertIn("RUN SUMMARY processed 3/3 | verified 3/3", stderr.getvalue())
        self.assertIn("qualified True", stderr.getvalue())
        self.assertIn("REPORTS saved", stderr.getvalue())
        persist_reports.assert_called_once()

    def test_completed_nonqualified_run_is_not_a_shell_failure(self) -> None:
        suite_path = ROOT / "benchmarks/suites/repository-intelligence/heldout-v1"
        suite = load_suite(suite_path)
        rows = select_definitions(
            suite,
            tasks=("locate-prefix-path-enumerator",),
            agents=("opencode-native",),
            condition="hashmarks-opencode-native",
        )
        initial = {
            "rows": [
                {"definition_id": row["definition_id"], "state": "PENDING"}
                for row in rows
            ],
            "complete_trials": 0,
            "pending_trials": len(rows),
            "interrupted_trials": 0,
            "qualified": False,
            "outcomes": {},
        }
        final = {
            **initial,
            "complete_trials": len(rows),
            "pending_trials": 0,
            "unresolved_outcome_trials": 1,
            "qualified": False,
            "outcomes": {"PASS": len(rows) - 1, "INCOMPLETE": 1},
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = mock.Mock()
            config.runtime_environment.return_value = {}

            def fake_run(**kwargs):
                row = next(item for item in rows if item["trial"] == kwargs["trial_index"])
                status = "INCOMPLETE" if row["trial"] == 1 else "PASS"
                result_dir = root / "results" / (str(row["trial"]) * 64)
                result_dir.mkdir(parents=True)
                (result_dir / "result.json").write_text(
                    json.dumps({"definition_id": row["definition_id"], "status": status}),
                    encoding="utf-8",
                )
                kwargs["on_progress"]("publication")
                return TrialRunResult(
                    trial_id=result_dir.name,
                    definition_id=str(row["definition_id"]),
                    status=status,
                    result_dir=result_dir,
                    reused=False,
                )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                mock.patch("benchmarks.__main__._resolve_config", return_value=config),
                mock.patch(
                    "benchmarks.__main__._validate_reporting_contract",
                    return_value=(suite_path / "score.py", Path("score.json")),
                ),
                mock.patch(
                    "benchmarks.__main__.select_saved_run",
                    return_value=SavedRun("000001", root),
                ),
                mock.patch("benchmarks.__main__._assert_saved_run_selection"),
                mock.patch(
                    "benchmarks.__main__.verify_saved_campaign",
                    return_value={"campaign_id": "c" * 64},
                ),
                mock.patch(
                    "benchmarks.__main__.campaign_status",
                    side_effect=[initial, final],
                ),
                mock.patch("benchmarks.__main__.run_trial", side_effect=fake_run),
                mock.patch(
                    "benchmarks.__main__._persist_completed_run_reports",
                    return_value={
                        "status": root / "reports/status.json",
                        "report": root / "reports/report.json",
                        "decision_evidence": root / "reports/decision-evidence.json",
                        "score": root / "reports/score.json",
                    },
                ) as persist_reports,
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                exit_code = main([
                    "run", "--resume", "--env-file", str(root / "unused.env"),
                    "--suite", str(suite_path), "--root", str(root),
                    "--harness-root", str(ROOT), "--task", "locate-prefix-path-enumerator",
                    "--agent", "opencode-native", "--condition", "hashmarks-opencode-native",
                ])

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(json.loads(stdout.getvalue())), 3)
        self.assertIn("qualified False", stderr.getvalue())
        self.assertIn("NOT QUALIFIED: non-outcome receipts 1", stderr.getvalue())
        self.assertIn("REPORTS saved", stderr.getvalue())
        persist_reports.assert_called_once()

    def test_run_abort_reports_active_trial_without_stdout_result(self) -> None:
        suite_path = ROOT / "benchmarks/suites/repository-intelligence/heldout-v1"
        suite = load_suite(suite_path)
        rows = select_definitions(
            suite,
            tasks=("locate-prefix-path-enumerator",),
            agents=("opencode-native",),
            condition="hashmarks-opencode-native",
        )
        status = {
            "rows": [{"definition_id": row["definition_id"], "state": "PENDING"} for row in rows],
            "complete_trials": 0,
            "pending_trials": len(rows),
            "interrupted_trials": 0,
            "qualified": False,
            "outcomes": {},
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = mock.Mock()
            config.runtime_environment.return_value = {}
            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                mock.patch("benchmarks.__main__._resolve_config", return_value=config),
                mock.patch(
                    "benchmarks.__main__._validate_reporting_contract",
                    return_value=(suite_path / "score.py", Path("score.json")),
                ),
                mock.patch("benchmarks.__main__.select_saved_run", return_value=SavedRun("000001", root)),
                mock.patch("benchmarks.__main__._assert_saved_run_selection"),
                mock.patch("benchmarks.__main__.verify_saved_campaign", return_value={"campaign_id": "c" * 64}),
                mock.patch("benchmarks.__main__.campaign_status", side_effect=[status, status]),
                mock.patch("benchmarks.__main__.run_trial", side_effect=TrialRunnerError("launch claim changed")),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                exit_code = main([
                    "run", "--resume", "--env-file", str(root / "unused.env"),
                    "--suite", str(suite_path), "--root", str(root),
                    "--harness-root", str(ROOT), "--task", "locate-prefix-path-enumerator",
                    "--agent", "opencode-native", "--condition", "hashmarks-opencode-native",
                ])
        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("ABORT locate-prefix-path-enumerator", stderr.getvalue())
        self.assertIn("stage admission", stderr.getvalue())
        self.assertIn("CAMPAIGN verified 0/3", stderr.getvalue())

    def test_regrade_score_dispatches_without_runtime_config(self) -> None:
        suite = ROOT / "benchmarks/suites/repository-intelligence/heldout-v1"
        with (
            tempfile.TemporaryDirectory() as tmp,
            mock.patch("benchmarks.__main__.subprocess.run") as run,
        ):
            run.return_value.returncode = 0
            self.assertEqual(
                main(
                    [
                        "regrade-score",
                        "--suite",
                        str(suite),
                        "--source-results",
                        tmp,
                        "--agent",
                        "opencode-native",
                        "--output",
                        str(Path(tmp).parent / "score.json"),
                    ]
                ),
                0,
            )
            self.assertIn("--regrade-source-results", run.call_args.args[0])

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
                main(["run", "--resume", "--env-file", str(file), "--agent", "codex-native"])
