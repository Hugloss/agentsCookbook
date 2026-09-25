from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from benchmarks.adapters.codex import (
    _final_message,
    _metrics,
    parse_codex_jsonl,
    seed_codex_auth,
)
from benchmarks.harness.bundle import verify_bundle
from benchmarks.harness.contamination import classify_contamination
from benchmarks.harness.model import (
    Observation,
    ParticipantIdentity,
    TrialContext,
)
from benchmarks.harness.mutation import apply_mutation
from benchmarks.harness.receipt import is_complete_receipt
from benchmarks.harness.report import ReportError, build_report
from benchmarks.harness.runner import run_trial
from benchmarks.harness.source import materialize_repository
from benchmarks.harness.suite import SuiteDefinition, load_suite
from benchmarks.harness.workspace import isolated_environment, snapshot
from scripts.agent_economics.bounded_process import ProcessLimits, run_bounded


PILOT = Path("benchmarks/suites/repository-intelligence/pilot-v1")
PINNED_COMMIT = "0841a8822f417b8fd03af61c03779df8f1cdc941"
PINNED_TREE = "65a32888329e308615647dda194f0e36c2afe2ac"


class FakeSubject:
    def identity(self) -> ParticipantIdentity:
        return ParticipantIdentity("fake-subject", "control", "1")

    def prepare(self, context: TrialContext) -> Observation:
        return Observation(
            {"available": True, "observed_identity": {"version": "1"}},
            "",
        )

    def query(self, context: TrialContext, prompt: str) -> Observation:
        return Observation({}, "")

    def post_change(
        self,
        context: TrialContext,
        changed_paths: tuple[str, ...],
    ) -> Observation:
        return Observation({"changed_paths": list(changed_paths)}, "")

    def cleanup(self, context: TrialContext) -> Observation:
        return Observation({}, "")

    def mcp_exposure(self, context: TrialContext):
        return None

    def generated_globs(self) -> tuple[str, ...]:
        return ()


class FakeAgent:
    def identity(self) -> ParticipantIdentity:
        return ParticipantIdentity("fake-agent", "coding_agent", "1")

    def prepare(self, context: TrialContext, exposed_subject) -> Observation:
        return Observation(
            {
                "available": True,
                "version": "fake-agent 1",
                "executable_sha256": "f" * 64,
                "mcp_exposure": None,
                "auth_mode": "not-applicable",
            },
            "",
        )

    def run(self, context: TrialContext, prompt: str, exposed_subject) -> Observation:
        return Observation(
            {
                "terminal_event": {"type": "turn.completed"},
                "terminal_complete": True,
                "final_message": '{"ok":true}',
                "jsonl_parse_errors": [],
                "process": {
                    "executable_missing": False,
                    "timed_out": False,
                    "stdout_truncated": False,
                    "stderr_truncated": False,
                },
            },
            '{"type":"turn.completed"}\n',
            {"duration_ms": 1.0, "mcp_calls": 0},
        )


class FakeOracle:
    def identity(self) -> ParticipantIdentity:
        return ParticipantIdentity("fake-oracle", "oracle", "1")

    def healthcheck(self, context: TrialContext) -> Observation:
        return Observation({"healthy": True}, "")

    def grade(self, context: TrialContext, observation: Observation) -> Observation:
        return Observation({"valid": True, "passed": True}, "")


class PilotExecutionTests(unittest.TestCase):
    def test_pilot_suite_freezes_nine_paired_trials(self) -> None:
        suite = load_suite(PILOT)
        self.assertEqual(len(suite.tasks), 3)
        self.assertEqual(len(suite.subjects), 3)
        self.assertEqual(len(suite.agents), 1)
        rows = suite.trial_definitions()
        self.assertEqual(len(rows), 9)
        self.assertEqual(
            {row["condition_id"] for row in rows},
            {"bare-codex", "hashmarks-codex", "enola-codex"},
        )
        self.assertTrue(all(len(row["definition_id"]) == 64 for row in rows))

    def test_codex_jsonl_separates_tool_availability_from_adoption(self) -> None:
        raw = b"\n".join(
            [
                json.dumps({"type": "thread.started", "thread_id": "t"}).encode(),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "id": "m1",
                            "type": "mcp_tool_call",
                            "server": "hashmarks",
                            "tool": "find",
                            "arguments": {"query": "owner"},
                            "result": {"content": "evidence"},
                            "error": None,
                            "status": "completed",
                        },
                    }
                ).encode(),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "id": "c1",
                            "type": "command_execution",
                            "command": "git status",
                            "aggregated_output": "",
                            "exit_code": 0,
                            "status": "completed",
                        },
                    }
                ).encode(),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "id": "a1",
                            "type": "agent_message",
                            "text": '{"path":"x","symbol":"y"}',
                        },
                    }
                ).encode(),
                json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {
                            "input_tokens": 100,
                            "cached_input_tokens": 20,
                            "output_tokens": 12,
                        },
                    }
                ).encode(),
            ]
        ) + b"\n"
        events, errors = parse_codex_jsonl(raw)
        self.assertEqual(errors, [])
        metrics = _metrics(events, subject_server="hashmarks")
        self.assertEqual(metrics["mcp_calls"], 1)
        self.assertEqual(metrics["subject_mcp_calls"], 1)
        self.assertTrue(metrics["subject_tool_invoked"])
        self.assertEqual(metrics["command_calls"], 1)
        self.assertEqual(metrics["tool_calls"], 2)
        self.assertTrue(metrics["subject_tool_configured"])
        self.assertEqual(metrics["input_tokens"], 100)
        self.assertEqual(
            _final_message(events),
            '{"path":"x","symbol":"y"}',
        )

        bare = _metrics(events, subject_server=None)
        self.assertEqual(bare["subject_mcp_calls"], 0)
        self.assertFalse(bare["subject_tool_invoked"])

    def test_codex_auth_seed_copies_only_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            control = root / "control"
            environment = isolated_environment(control)
            context = TrialContext(workspace, control, environment)
            auth = root / "auth.json"
            auth.write_text('{"token":"secret"}\n', encoding="utf-8")

            mode = seed_codex_auth(context, auth)

            target = Path(environment["CODEX_HOME"]) / "auth.json"
            self.assertEqual(mode, "seeded-auth-file")
            self.assertEqual(target.read_bytes(), auth.read_bytes())
            self.assertEqual(
                environment["BENCHMARK_CODEX_AUTH_MODE"],
                "seeded-auth-file",
            )
            self.assertNotIn(str(auth), json.dumps(environment))

    def test_contamination_allows_declared_output_but_not_source_residue(self) -> None:
        before = {
            "a.py": {"kind": "file", "size": 1, "sha256": "a"},
        }
        after = {
            "a.py": {"kind": "file", "size": 1, "sha256": "a"},
            ".benchmark-enola/facts.jsonl": {
                "kind": "file",
                "size": 2,
                "sha256": "b",
            },
            "unexpected.txt": {"kind": "file", "size": 1, "sha256": "c"},
        }
        result = classify_contamination(
            before=before,
            after=after,
            allowed_change_globs=(),
            allowed_generated_globs=(".benchmark-enola/**",),
        )
        self.assertTrue(result["contaminated"])
        self.assertEqual(result["unexpected"]["added"], ["unexpected.txt"])

    def test_pilot_mutation_is_exact_and_oracle_discriminates(self) -> None:
        suite = load_suite(PILOT)
        task = suite.tasks["repair-partial-receipt-regression"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            materialize_repository(
                repository=task["repository"],
                destination=workspace,
                cache_root=root / "cache",
                local_source=Path("."),
            )
            control = root / "control"
            context = TrialContext(
                workspace,
                control,
                isolated_environment(control),
            )
            mutation = apply_mutation(
                context,
                suite_root=suite.root,
                mutation=task["mutation"],
            )
            self.assertEqual(
                mutation.payload["changed_paths"],
                ["benchmarks/harness/receipt.py"],
            )

            environment = dict(context.environment)
            environment["PYTHONPATH"] = str(workspace)
            failed = run_bounded(
                repository_root=workspace,
                argv=(
                    sys.executable,
                    "-m",
                    "unittest",
                    "benchmarks.tests.test_foundation.FoundationTests.test_partial_or_corrupt_receipt_is_not_complete",
                ),
                environment=environment,
                limits=ProcessLimits(timeout_seconds=60),
            )
            self.assertNotEqual(failed.return_code, 0)

            subprocess.run(
                (
                    "git",
                    "checkout",
                    PINNED_COMMIT,
                    "--",
                    "benchmarks/harness/receipt.py",
                ),
                cwd=workspace,
                check=True,
                capture_output=True,
            )
            passed = run_bounded(
                repository_root=workspace,
                argv=(
                    sys.executable,
                    "-m",
                    "unittest",
                    "benchmarks.tests.test_foundation.FoundationTests.test_partial_or_corrupt_receipt_is_not_complete",
                ),
                environment=environment,
                limits=ProcessLimits(timeout_seconds=60),
            )
            self.assertEqual(
                passed.return_code,
                0,
                passed.stderr.decode("utf-8", errors="replace"),
            )

    def test_trial_lifecycle_publishes_and_reuses_verified_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            subprocess.run(("git", "init"), cwd=source, check=True, capture_output=True)
            subprocess.run(
                ("git", "config", "user.email", "bench@example.invalid"),
                cwd=source,
                check=True,
            )
            subprocess.run(
                ("git", "config", "user.name", "Bench"),
                cwd=source,
                check=True,
            )
            (source / "a.txt").write_text("a\n", encoding="utf-8")
            subprocess.run(("git", "add", "a.txt"), cwd=source, check=True)
            subprocess.run(
                ("git", "commit", "-m", "fixture"),
                cwd=source,
                check=True,
                capture_output=True,
            )
            commit = subprocess.run(
                ("git", "rev-parse", "HEAD"),
                cwd=source,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            tree = subprocess.run(
                ("git", "rev-parse", "HEAD^{tree}"),
                cwd=source,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            experiment = {
                "id": "fake-experiment",
                "version": 1,
                "suite": "fake",
                "tasks": ["task"],
                "conditions": [
                    {
                        "id": "condition",
                        "subject": "subject",
                        "agent": "agent",
                        "trials": 1,
                        "seed": 1,
                    }
                ],
                "scoring": {
                    "id": "fake",
                    "version": 1,
                    "metrics": ["task_success"],
                },
            }
            task = {
                "id": "task",
                "version": 1,
                "family": "test",
                "mode": "read_only",
                "repository": {
                    "url": str(source),
                    "commit": commit,
                    "tree": tree,
                },
                "prompt": "answer",
                "mutation": None,
                "oracle": {
                    "adapter": "fake",
                    "identity": {"id": "fake-oracle", "version": "1"},
                    "configuration": {},
                },
                "budgets": {"timeout_seconds": 30},
                "contamination": {
                    "allowed_change_globs": [],
                    "allowed_generated_globs": [],
                },
            }
            suite = SuiteDefinition(
                root=root,
                experiment=experiment,
                tasks={"task": task},
                subjects={
                    "subject": {
                        "id": "subject",
                        "kind": "control",
                        "adapter": "fake",
                        "identity": {"id": "subject", "version": "1"},
                        "capabilities": [],
                        "configuration": {},
                    }
                },
                agents={
                    "agent": {
                        "id": "agent",
                        "adapter": "fake",
                        "identity": {"id": "agent", "version": "1"},
                        "capabilities": [],
                        "configuration": {},
                    }
                },
            )

            patches = (
                mock.patch(
                    "benchmarks.harness.runner.build_subject",
                    return_value=FakeSubject(),
                ),
                mock.patch(
                    "benchmarks.harness.runner.build_agent",
                    return_value=FakeAgent(),
                ),
                mock.patch(
                    "benchmarks.harness.runner.build_oracle",
                    return_value=FakeOracle(),
                ),
                mock.patch(
                    "benchmarks.harness.runner.harness_identity",
                    return_value={
                        "repository": "fixture",
                        "commit": "1" * 40,
                        "tree": "2" * 40,
                        "contract": "test",
                    },
                ),
            )
            for patcher in patches:
                patcher.start()
                self.addCleanup(patcher.stop)

            kwargs = {
                "suite": suite,
                "task_id": "task",
                "condition_id": "condition",
                "trial_index": 0,
                "harness_root": Path("."),
                "cache_root": root / "cache",
                "results_root": root / "results",
                "work_root": root / "work",
                "local_source": source,
            }
            first = run_trial(**kwargs)
            self.assertEqual(first.status, "PASS")
            self.assertFalse(first.reused)
            self.assertTrue(is_complete_receipt(first.result_dir))
            self.assertTrue((first.result_dir / "events.jsonl").is_file())
            self.assertTrue((first.result_dir / "agent-trace.jsonl").is_file())

            second = run_trial(**kwargs)
            self.assertEqual(second.trial_id, first.trial_id)
            self.assertTrue(second.reused)
            self.assertEqual(second.status, "PASS")

            report = build_report(
                suite=suite,
                results_root=root / "results",
            )
            self.assertEqual(report["observed_trials"], 1)
            self.assertEqual(report["status_counts"], {"PASS": 1})
            self.assertFalse(report["authority"]["ranking_performed"])
            valid, reason = verify_bundle(first.result_dir)
            self.assertTrue(valid, reason)

            (first.result_dir / "undeclared.txt").write_text("tamper")
            valid, reason = verify_bundle(first.result_dir)
            self.assertFalse(valid)
            self.assertIn("undeclared", reason or "")
            with self.assertRaises(ReportError):
                build_report(
                    suite=suite,
                    results_root=root / "results",
                )

    def test_report_rejects_multiple_executions_for_one_definition(self) -> None:
        experiment = {
            "id": "report",
            "version": 1,
            "suite": "fake",
            "tasks": ["task"],
            "conditions": [
                {
                    "id": "bare",
                    "subject": "none",
                    "agent": "agent",
                    "trials": 1,
                    "seed": 7,
                }
            ],
            "scoring": {"id": "s", "version": 1, "metrics": ["task_success"]},
        }
        task = {
            "id": "task",
            "version": 1,
            "repository": {
                "url": "https://example.invalid/repo.git",
                "commit": "1" * 40,
                "tree": "2" * 40,
            },
            "prompt": "x",
            "mode": "read_only",
            "mutation": None,
            "oracle": {
                "adapter": "expected-json",
                "identity": {"id": "o", "version": "1"},
                "configuration": {"expected": {"ok": True}},
            },
            "budgets": {"timeout_seconds": 1},
            "contamination": {
                "allowed_change_globs": [],
                "allowed_generated_globs": [],
            },
        }
        suite = SuiteDefinition(
            root=Path("."),
            experiment=experiment,
            tasks={"task": task},
            subjects={
                "none": {
                    "id": "none",
                    "kind": "control",
                    "adapter": "none",
                    "identity": {"id": "none", "version": "1"},
                    "capabilities": [],
                    "configuration": {},
                }
            },
            agents={
                "agent": {
                    "id": "agent",
                    "adapter": "fake",
                    "identity": {"id": "agent", "version": "1"},
                    "capabilities": [],
                    "configuration": {},
                }
            },
        )
        definition = suite.trial_definitions()[0]["definition_id"]
        expanded = suite.expanded_condition(experiment["conditions"][0])
        base = {
            "definition_id": definition,
            "experiment": experiment,
            "task": task,
            "condition": expanded,
            "status": "PASS",
            "authority": {"subject": {"available": True}},
            "execution": {"trial_index": 0, "seed": 7},
            "measurements": {"agent": {}},
        }
        with mock.patch(
            "benchmarks.harness.report._receipts",
            return_value=[
                {**base, "trial_id": "a" * 64},
                {**base, "trial_id": "b" * 64},
            ],
        ):
            with self.assertRaises(ReportError):
                build_report(
                    suite=suite,
                    results_root=Path("/unused"),
                )


if __name__ == "__main__":
    unittest.main()
