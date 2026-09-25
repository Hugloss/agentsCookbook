from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from benchmarks.adapters.codex import (
    CodexAgent,
    _final_message,
    _metrics,
    _render_config,
    parse_codex_jsonl,
    seed_codex_auth,
)
from benchmarks.adapters.enola import EnolaSubject
from benchmarks.adapters.hashmarks import HashmarksSubject
from benchmarks.adapters.opencode_native import (
    OpenCodeNativeAgent,
    _metrics as opencode_metrics,
    _native_environment as opencode_native_environment,
    _observed_model as opencode_observed_model,
)
from benchmarks.adapters.registry import (
    AdapterConfigurationError,
    build_agent,
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
from benchmarks.harness.selection import SelectionError, select_definitions
from benchmarks.harness.source import materialize_repository
from benchmarks.harness.suite import SuiteDefinition, SuiteError, load_suite
from benchmarks.harness.workspace import isolated_environment, snapshot
from scripts.agent_economics.bounded_process import ProcessLimits, run_bounded


PILOT = Path("benchmarks/suites/repository-intelligence/pilot-v1")
MATRIX_V2 = Path(
    "benchmarks/suites/repository-intelligence/agent-matrix-v2"
)
PINNED_COMMIT = "0841a8822f417b8fd03af61c03779df8f1cdc941"
PINNED_TREE = "65a32888329e308615647dda194f0e36c2afe2ac"
MATRIX_V2_COMMIT = "6ce8b0d9230dd9bc5369ddf495ad9404766fbbaf"
MATRIX_V2_TREE = "1e253d251f8e0a874aeca0b05358b36253a714cc"


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

    def test_agent_matrix_v2_freezes_eighteen_definitions(self) -> None:
        suite = load_suite(MATRIX_V2)
        self.assertEqual(len(suite.tasks), 3)
        self.assertEqual(len(suite.subjects), 3)
        self.assertEqual(len(suite.agents), 2)
        rows = suite.trial_definitions()
        self.assertEqual(len(rows), 18)
        self.assertEqual(len({row["definition_id"] for row in rows}), 18)
        self.assertEqual(
            {row["condition_id"] for row in rows},
            {
                "bare-sol",
                "hashmarks-sol",
                "enola-sol",
                "bare-opencode-native",
                "hashmarks-opencode-native",
                "enola-opencode-native",
            },
        )
        sol = suite.agents["codex-sol"]["configuration"]
        native = suite.agents["opencode-native"]["configuration"]
        self.assertEqual(sol["model"], "gpt-5.6-sol")
        self.assertEqual(sol["reasoning_effort"], "high")
        self.assertNotIn("model", native)
        self.assertNotIn("provider", native)
        self.assertNotIn("api_key", native)
        self.assertEqual(
            suite.agents["opencode-native"]["adapter"],
            "opencode-native",
        )

    def test_matrix_selection_includes_one_matching_bare_control(self) -> None:
        suite = load_suite(MATRIX_V2)
        selected = select_definitions(
            suite, agents=("opencode-native",), subjects=("hashmarks",)
        )
        self.assertEqual(len(selected), 6)
        self.assertEqual(
            {row["condition_id"] for row in selected},
            {"bare-opencode-native", "hashmarks-opencode-native"},
        )
        both = select_definitions(
            suite, agents=("codex-sol",), subjects=("hashmarks", "enola")
        )
        self.assertEqual(len(both), 9)
        with self.assertRaises(SelectionError):
            select_definitions(suite, agents=("unknown",))
        with self.assertRaises(SelectionError):
            select_definitions(
                suite, agents=("codex-sol",), condition="bare-sol"
            )

    def test_suite_loader_enforces_repo_owned_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            copied = Path(tmp) / "pilot"
            shutil.copytree(PILOT, copied)

            task_path = copied / "tasks" / "locate-receipt-completion-owner.json"
            task = json.loads(task_path.read_text(encoding="utf-8"))
            task.pop("mode")
            task_path.write_text(
                json.dumps(task, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(SuiteError):
                load_suite(copied)

        with tempfile.TemporaryDirectory() as tmp:
            copied = Path(tmp) / "pilot"
            shutil.copytree(PILOT, copied)

            subject_path = copied / "subjects" / "none.json"
            subject = json.loads(subject_path.read_text(encoding="utf-8"))
            subject["unexpected"] = True
            subject_path.write_text(
                json.dumps(subject, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(SuiteError):
                load_suite(copied)

    def test_participant_configuration_is_part_of_definition_identity(self) -> None:
        suite = load_suite(PILOT)
        original = next(
            row["definition_id"]
            for row in suite.trial_definitions()
            if row["task_id"] == "locate-receipt-completion-owner"
            and row["condition_id"] == "hashmarks-codex"
        )
        subjects = json.loads(json.dumps(suite.subjects))
        subjects["hashmarks"]["configuration"]["timeout_seconds"] += 1
        changed = SuiteDefinition(
            root=suite.root,
            experiment=suite.experiment,
            tasks=suite.tasks,
            subjects=subjects,
            agents=suite.agents,
        )
        altered = next(
            row["definition_id"]
            for row in changed.trial_definitions()
            if row["task_id"] == "locate-receipt-completion-owner"
            and row["condition_id"] == "hashmarks-codex"
        )
        self.assertNotEqual(original, altered)

    def test_hashmarks_adapter_uses_real_version_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            control = root / "control"
            context = TrialContext(
                workspace,
                control,
                isolated_environment(control),
            )
            unavailable = Observation({"available": False}, "")
            with mock.patch(
                "benchmarks.adapters.hashmarks.observe_executable",
                return_value=unavailable,
            ) as observed:
                HashmarksSubject().prepare(context)
            observed.assert_called_once_with(
                context,
                "hashmarks",
                version_args=("version",),
            )

    def test_enola_adapter_writes_explicit_trial_output_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            control = root / "control"
            control.mkdir()
            context = TrialContext(workspace, control, {})
            path = EnolaSubject()._config(context)
            value = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(value["repo"], str(workspace))
            self.assertEqual(value["output"]["dir"], ".benchmark-enola")
            self.assertFalse(path.is_relative_to(workspace))

    def test_agent_adapter_receives_frozen_execution_budgets(self) -> None:
        suite = load_suite(PILOT)
        task = suite.tasks["locate-receipt-completion-owner"]
        agent = build_agent(suite.agents["codex"], budgets=task["budgets"])
        self.assertEqual(
            agent.max_output_bytes,
            task["budgets"]["max_output_bytes"],
        )
        self.assertEqual(
            agent.max_tool_calls,
            task["budgets"]["max_tool_calls"],
        )
        self.assertEqual(
            agent.timeout_seconds,
            task["budgets"]["timeout_seconds"],
        )

    def test_codex_adapter_rejects_local_model_provider_config(self) -> None:
        definition = {
            "id": "forbidden",
            "adapter": "codex",
            "identity": {"id": "forbidden", "version": "1"},
            "capabilities": [],
            "configuration": {
                "model": "gemma4:12b",
                "local_provider": "ollama",
            },
        }
        with self.assertRaises(AdapterConfigurationError):
            build_agent(
                definition,
                budgets={"timeout_seconds": 60},
            )

    def test_codex_sol_freezes_reasoning_effort(self) -> None:
        config = _render_config(
            "gpt-5.6-sol",
            None,
            reasoning_effort="high",
        )
        self.assertIn('model = "gpt-5.6-sol"', config)
        self.assertIn('model_reasoning_effort = "high"', config)
        self.assertNotIn("oss_provider", config)

    def test_opencode_native_adapter_owns_no_model_provider_config(self) -> None:
        suite = load_suite(MATRIX_V2)
        task = suite.tasks["locate-receipt-completion-owner"]
        agent = build_agent(
            suite.agents["opencode-native"],
            budgets=task["budgets"],
        )
        self.assertIsInstance(agent, OpenCodeNativeAgent)

        forbidden = json.loads(
            json.dumps(suite.agents["opencode-native"])
        )
        forbidden["configuration"]["model"] = "liteLLM/gemma4"
        with self.assertRaises(AdapterConfigurationError):
            build_agent(forbidden, budgets=task["budgets"])

    def test_opencode_native_environment_preserves_native_home(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            control = root / "control"
            context = TrialContext(
                workspace,
                control,
                isolated_environment(control),
            )
            environment = opencode_native_environment(context)
            self.assertNotIn("HOME", environment)
            self.assertNotIn("XDG_CONFIG_HOME", environment)
            self.assertNotIn("XDG_DATA_HOME", environment)
            self.assertEqual(
                environment["TMPDIR"],
                context.environment["TMPDIR"],
            )
            self.assertNotIn("OPENCODE_CONFIG_CONTENT", environment)

    def test_opencode_prepare_uses_shared_runtime_inspection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            control = root / "control"
            context = TrialContext(
                workspace,
                control,
                isolated_environment(control),
            )
            executable = Observation(
                {
                    "available": True,
                    "version": "opencode 1",
                    "executable_sha256": "a" * 64,
                },
                "opencode 1",
            )
            inspection = {
                "model": "liteLLM/gemma4",
                "provider": "liteLLM",
                "config_sha256": "b" * 64,
                "mcp_shape": "flat",
                "mcp_servers": [
                    {"name": "hashmarks", "enabled": True},
                    {"name": "enola", "enabled": True},
                ],
            }
            runtime_result = mock.Mock()
            runtime_result.metrics.return_value = {"return_code": 0}
            runtime_result.stderr = b""
            runtime_result.stdout = b"{}"
            with (
                mock.patch(
                    "benchmarks.adapters.opencode_native.observe_executable",
                    return_value=executable,
                ),
                mock.patch(
                    "benchmarks.adapters.opencode_native._runtime_call",
                    return_value=(
                        {
                            "status": "completed",
                            "inspection": inspection,
                            "effective_inspection": inspection,
                            "selected_server": None,
                            "overlay_identity": {"shape": "flat"},
                        },
                        runtime_result,
                    ),
                ) as runtime_call,
            ):
                prepared = OpenCodeNativeAgent().prepare(context, None)

            self.assertTrue(prepared.payload["available"])
            self.assertEqual(prepared.payload["model"], "liteLLM/gemma4")
            self.assertEqual(
                prepared.payload["native_config_sha256"],
                "b" * 64,
            )
            runtime_call.assert_called_once()
            self.assertEqual(
                runtime_call.call_args.kwargs["args"],
                (
                    "inspect-config",
                    "--repo",
                    str(workspace),
                    "--benchmark-subject",
                    "none",
                ),
            )

    def test_opencode_assisted_prepare_reuses_native_subject_server(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            control = root / "control"
            context = TrialContext(
                workspace,
                control,
                isolated_environment(control),
            )
            executable = Observation(
                {
                    "available": True,
                    "version": "opencode 1",
                    "executable_sha256": "a" * 64,
                },
                "opencode 1",
            )
            inspection = {
                "model": "liteLLM/gemma4",
                "provider": "liteLLM",
                "config_sha256": "b" * 64,
                "mcp_shape": "flat",
                "mcp_servers": [
                    {"name": "hashmarks", "enabled": True},
                    {"name": "enola", "enabled": True},
                ],
            }
            runtime_result = mock.Mock()
            runtime_result.metrics.return_value = {"return_code": 0}
            runtime_result.stderr = b""
            runtime_result.stdout = b"{}"
            subject = HashmarksSubject()
            with (
                mock.patch(
                    "benchmarks.adapters.opencode_native.observe_executable",
                    return_value=executable,
                ),
                mock.patch(
                    "benchmarks.adapters.opencode_native._runtime_call",
                    return_value=(
                        {
                            "status": "completed",
                            "inspection": inspection,
                            "effective_inspection": inspection,
                            "selected_server": "hashmarks",
                            "workspace_binding": {
                                "verified": True,
                                "subject": "hashmarks",
                                "method": "hashmarks-explicit-workspace",
                                "workspace": str(workspace),
                                "effective_cwd": str(workspace),
                                "resolved_workspace": str(workspace),
                                "reason": None,
                            },
                            "overlay_identity": {
                                "shape": "flat",
                                "selected_subject": "hashmarks",
                                "native_server_reused": True,
                            },
                        },
                        runtime_result,
                    ),
                ) as runtime_call,
                mock.patch.object(
                    HashmarksSubject,
                    "mcp_exposure",
                    side_effect=AssertionError(
                        "native OpenCode must not request benchmark MCP exposure"
                    ),
                ),
            ):
                prepared = OpenCodeNativeAgent().prepare(context, subject)

            self.assertTrue(prepared.payload["available"])
            self.assertEqual(
                prepared.payload["mcp_exposure"]["name"],
                "hashmarks",
            )
            self.assertEqual(
                prepared.payload["mcp_exposure"]["source"],
                "native-opencode-config",
            )
            self.assertTrue(
                prepared.payload["mcp_exposure"]["native_server_reused"]
            )
            runtime_call.assert_called_once()
            self.assertEqual(
                runtime_call.call_args.kwargs["args"],
                (
                    "inspect-config",
                    "--repo",
                    str(workspace),
                    "--benchmark-subject",
                    "hashmarks",
                ),
            )
            self.assertFalse(
                (control / "opencode-benchmark-exposure.json").exists()
            )

    def test_opencode_unverified_native_workspace_binding_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            control = root / "control"
            context = TrialContext(
                workspace,
                control,
                isolated_environment(control),
            )
            executable = Observation(
                {
                    "available": True,
                    "version": "opencode 1",
                    "executable_sha256": "a" * 64,
                },
                "opencode 1",
            )
            inspection = {
                "model": "liteLLM/gemma4",
                "provider": "liteLLM",
                "config_sha256": "b" * 64,
                "mcp_shape": "flat",
                "mcp_servers": [
                    {"name": "hashmarks", "enabled": True},
                ],
            }
            runtime_result = mock.Mock()
            runtime_result.metrics.return_value = {"return_code": 0}
            runtime_result.stderr = b""
            runtime_result.stdout = b"{}"
            with (
                mock.patch(
                    "benchmarks.adapters.opencode_native.observe_executable",
                    return_value=executable,
                ),
                mock.patch(
                    "benchmarks.adapters.opencode_native._runtime_call",
                    return_value=(
                        {
                            "status": "completed",
                            "inspection": inspection,
                            "effective_inspection": inspection,
                            "selected_server": "hashmarks",
                            "workspace_binding": {
                                "verified": False,
                                "subject": "hashmarks",
                                "method": "hashmarks-explicit-workspace",
                                "workspace": str(workspace),
                                "effective_cwd": "/outside",
                                "resolved_workspace": "/outside",
                                "reason": (
                                    "native Hashmarks workspace resolves outside "
                                    "trial workspace: /outside"
                                ),
                            },
                            "overlay_identity": {
                                "shape": "flat",
                                "selected_subject": "hashmarks",
                                "native_server_reused": True,
                            },
                        },
                        runtime_result,
                    ),
                ),
            ):
                prepared = OpenCodeNativeAgent().prepare(
                    context,
                    HashmarksSubject(),
                )

            self.assertFalse(prepared.payload["available"])
            self.assertFalse(
                prepared.payload["workspace_binding"]["verified"]
            )
            self.assertIn(
                "outside trial workspace",
                prepared.payload["reason"],
            )
            self.assertEqual(
                prepared.payload["observed_identity"]["workspace_binding"],
                prepared.payload["workspace_binding"],
            )

    def test_opencode_export_observes_native_model_and_mcp_adoption(self) -> None:
        exported = {
            "messages": [
                {
                    "info": {
                        "role": "assistant",
                        "providerID": "liteLLM",
                        "modelID": "gemma4",
                        "tokens": {
                            "input": 100,
                            "output": 20,
                            "cache": {"read": 5},
                        },
                    },
                    "parts": [
                        {
                            "type": "tool",
                            "tool": "hashmarks_find",
                            "state": {"output": "evidence"},
                        },
                        {
                            "type": "tool",
                            "tool": "bash",
                            "state": {"output": ""},
                        },
                        {
                            "type": "text",
                            "text": '{"path":"x","symbol":"y"}',
                        },
                    ],
                }
            ]
        }
        model, provider = opencode_observed_model(exported)
        self.assertEqual(model, "liteLLM/gemma4")
        self.assertEqual(provider, "liteLLM")
        metrics = opencode_metrics(
            exported,
            mcp_servers=("hashmarks", "enola"),
            selected_server="hashmarks",
        )
        self.assertEqual(metrics["mcp_calls"], 1)
        self.assertEqual(metrics["subject_mcp_calls"], 1)
        self.assertTrue(metrics["subject_tool_invoked"])
        self.assertEqual(metrics["command_calls"], 1)
        self.assertEqual(metrics["input_tokens"], 100)
        self.assertEqual(metrics["output_tokens"], 20)
        self.assertEqual(metrics["cached_input_tokens"], 5)
        self.assertEqual(metrics["mcp_result_bytes"], len("evidence".encode()))

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

    def test_agent_matrix_v2_mutation_is_exact_and_oracle_discriminates(self) -> None:
        suite = load_suite(MATRIX_V2)
        task = suite.tasks["repair-partial-receipt-regression"]
        self.assertEqual(task["repository"]["commit"], MATRIX_V2_COMMIT)
        self.assertEqual(task["repository"]["tree"], MATRIX_V2_TREE)

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
                    MATRIX_V2_COMMIT,
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

    def test_report_keeps_cross_agent_rows_descriptive(self) -> None:
        suite = load_suite(MATRIX_V2)
        task_id = "locate-receipt-completion-owner"
        rows = {
            (row["task_id"], row["condition_id"]): row
            for row in suite.trial_definitions()
        }
        receipts = []
        for condition_id, status, duration in (
            ("bare-sol", "PASS", 100.0),
            ("bare-opencode-native", "FAIL", 250.0),
        ):
            row = rows[(task_id, condition_id)]
            condition = next(
                value
                for value in suite.experiment["conditions"]
                if value["id"] == condition_id
            )
            receipts.append(
                {
                    "definition_id": row["definition_id"],
                    "trial_id": (
                        "a" * 64
                        if condition_id == "bare-sol"
                        else "b" * 64
                    ),
                    "experiment": suite.experiment,
                    "task": suite.tasks[task_id],
                    "condition": suite.expanded_condition(condition),
                    "status": status,
                    "authority": {"subject": {"available": True}},
                    "execution": {"trial_index": 0, "seed": 5201},
                    "measurements": {
                        "agent": {
                            "duration_ms": duration,
                            "tool_calls": 1,
                            "command_calls": 1,
                            "mcp_calls": 0,
                            "subject_mcp_calls": 0,
                            "mcp_result_bytes": 0,
                            "input_tokens": 10,
                            "cached_input_tokens": 0,
                            "output_tokens": 2,
                            "subject_tool_invoked": False,
                        }
                    },
                }
            )

        with mock.patch(
            "benchmarks.harness.report._receipts",
            return_value=receipts,
        ):
            report = build_report(
                suite=suite,
                results_root=Path("/unused"),
                require_complete=False,
            )

        self.assertEqual(
            set(report["agent_profiles"]),
            {"codex-sol", "opencode-native"},
        )
        observations = report["cross_agent_observations"]
        self.assertEqual(len(observations), 1)
        self.assertEqual(
            set(observations[0]["agents"]),
            {"codex-sol", "opencode-native"},
        )
        self.assertNotIn("winner", observations[0])
        self.assertTrue(
            report["authority"]["cross_agent_rows_are_descriptive"]
        )

    def test_report_selection_rejects_mixed_native_runtime_authority(self) -> None:
        suite = load_suite(MATRIX_V2)
        task_id = "locate-receipt-completion-owner"
        definitions = {
            row["condition_id"]: row
            for row in suite.trial_definitions()
            if row["task_id"] == task_id
        }
        receipts = []
        for condition_id, status, model, config_hash in (
            ("bare-opencode-native", "PASS", "liteLLM/gemma4", "a" * 64),
            ("hashmarks-opencode-native", "INVALID", "liteLLM/other", "b" * 64),
        ):
            condition = next(
                row for row in suite.experiment["conditions"]
                if row["id"] == condition_id
            )
            receipts.append({
                "definition_id": definitions[condition_id]["definition_id"],
                "trial_id": ("c" if status == "PASS" else "d") * 64,
                "experiment": suite.experiment,
                "task": suite.tasks[task_id],
                "condition": suite.expanded_condition(condition),
                "status": status,
                "authority": {
                    "subject": {"available": True},
                    "agent": {"observed": {
                        "version": "opencode 1",
                        "executable_sha256": "e" * 64,
                        "auth_mode": "native-opencode",
                        "model": model,
                        "provider": "liteLLM",
                        "native_config_sha256": config_hash,
                    }},
                },
                "execution": {"trial_index": 0, "seed": 5201},
                "measurements": {"agent": {}},
            })
        with mock.patch(
            "benchmarks.harness.report._receipts", return_value=receipts,
        ):
            report = build_report(
                suite=suite,
                results_root=Path("/unused"),
                require_complete=False,
                selected_definitions={
                    definitions["bare-opencode-native"]["definition_id"]
                },
                selection={"agents": ["opencode-native"], "subjects": ["none"]},
            )
            self.assertEqual(report["observed_trials"], 1)
            self.assertEqual(report["selection"]["subjects"], ["none"])
            with self.assertRaisesRegex(ReportError, "mixed observed runtime"):
                build_report(
                    suite=suite,
                    results_root=Path("/unused"),
                    require_complete=False,
                    selected_definitions={
                        row["definition_id"] for row in definitions.values()
                    },
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

    def test_report_economics_keep_invalid_trial_costs(self) -> None:
        experiment = {
            "id": "economics",
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
        receipt = {
            "definition_id": definition,
            "trial_id": "a" * 64,
            "experiment": experiment,
            "task": task,
            "condition": suite.expanded_condition(experiment["conditions"][0]),
            "status": "INVALID",
            "authority": {"subject": {"available": True}},
            "execution": {"trial_index": 0, "seed": 7},
            "measurements": {
                "agent": {
                    "duration_ms": 1200.0,
                    "tool_calls": 4,
                    "command_calls": 3,
                    "mcp_calls": 1,
                    "subject_mcp_calls": 0,
                    "mcp_result_bytes": 32,
                    "input_tokens": 500,
                    "cached_input_tokens": 100,
                    "output_tokens": 20,
                    "source_read_observability":
                        "not-authoritatively-exposed-by-codex-jsonl",
                }
            },
        }
        with mock.patch(
            "benchmarks.harness.report._receipts",
            return_value=[receipt],
        ):
            report = build_report(
                suite=suite,
                results_root=Path("/unused"),
            )

        condition = report["conditions"]["bare"]
        self.assertEqual(condition["valid_outcomes"], 0)
        self.assertIsNone(condition["task_success_rate"])
        self.assertEqual(
            condition["metrics"]["duration_ms"]["total"],
            1200.0,
        )
        self.assertEqual(
            condition["metrics"]["tool_calls"]["total"],
            4,
        )
        self.assertEqual(
            condition["valid_outcome_metrics"]["duration_ms"]["observations"],
            0,
        )
        self.assertTrue(
            report["authority"]["economics_include_invalid_and_incomplete_trials"]
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
