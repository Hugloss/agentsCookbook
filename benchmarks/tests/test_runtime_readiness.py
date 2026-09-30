from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from benchmarks.adapters.hashmarks import HashmarksSubject
from benchmarks.harness.model import McpExposure, Observation
from benchmarks.harness.readiness import (
    _mcp_startup_diagnostic,
    check_runtime_readiness,
)
from benchmarks.harness.suite import (
    SuiteDefinition,
    SuiteError,
    load_runtime_suite,
    load_suite,
)


class FakeSubject:
    def __init__(self, name: str) -> None:
        self.name = name

    def identity(self):
        return mock.Mock(participant_id=self.name, kind="repository_intelligence")

    def mcp_exposure(self, context):
        return McpExposure(
            name=self.name,
            command=f"/tools/{self.name}",
            args=("mcp",),
            cwd=context.workspace,
            semantic_identity={"name": self.name, "transport": "stdio"},
        )


class FakeAgent:
    def __init__(self, name: str, calls: list[tuple[str, str | None]]) -> None:
        self.name = name
        self.calls = calls

    def prepare(self, context, subject):
        subject_name = None
        if subject is not None:
            subject_name = subject.identity().participant_id
            subject.mcp_exposure(context)
        self.calls.append((self.name, subject_name))
        if self.name == "opencode-native" and subject_name == "hashmarks":
            return Observation(
                {
                    "available": False,
                    "reason": "hashmarks MCP connection closed",
                },
                "",
            )
        return Observation({"available": True}, "")


def fake_suite() -> SuiteDefinition:
    return SuiteDefinition(
        root=Path("."),
        experiment={
            "conditions": [
                {
                    "id": "none-codex-native",
                    "subject": "none",
                    "agent": "codex-native",
                },
                {
                    "id": "hashmarks-codex-native",
                    "subject": "hashmarks",
                    "agent": "codex-native",
                },
                {
                    "id": "enola-codex-native",
                    "subject": "enola",
                    "agent": "codex-native",
                },
                {
                    "id": "none-opencode-native",
                    "subject": "none",
                    "agent": "opencode-native",
                },
                {
                    "id": "hashmarks-opencode-native",
                    "subject": "hashmarks",
                    "agent": "opencode-native",
                },
                {
                    "id": "enola-opencode-native",
                    "subject": "enola",
                    "agent": "opencode-native",
                },
                {
                    "id": "duplicate-hashmarks-opencode-native",
                    "subject": "hashmarks",
                    "agent": "opencode-native",
                },
            ]
        },
        tasks={},
        subjects={
            "none": {"id": "none", "adapter": "none"},
            "hashmarks": {"id": "hashmarks", "adapter": "hashmarks"},
            "enola": {"id": "enola", "adapter": "enola"},
        },
        agents={
            "codex-native": {
                "id": "codex-native",
                "adapter": "codex",
                "configuration": {"native_host": True},
            },
            "opencode-native": {
                "id": "opencode-native",
                "adapter": "opencode-native",
                "configuration": {},
            },
        },
    )


ROOT = Path(__file__).resolve().parents[2]
HELDOUT = ROOT / "benchmarks" / "suites" / "repository-intelligence" / "heldout-v1"


class RuntimeReadinessTests(unittest.TestCase):
    def test_runtime_suite_does_not_load_task_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            copied = Path(tmp) / "heldout"
            shutil.copytree(HELDOUT, copied)
            shutil.rmtree(copied / "tasks")

            runtime = load_runtime_suite(copied)
            self.assertEqual(runtime.tasks, {})
            self.assertIn("hashmarks", runtime.subjects)
            self.assertIn("codex-native", runtime.agents)

            with self.assertRaises(SuiteError):
                load_suite(copied)

    def test_readiness_has_no_trial_admission_dependencies(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "harness"
            / "readiness.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "preflight_trial",
            "materialize_repository",
            "apply_mutation",
            "build_oracle",
            "campaign_status",
            "run_trial",
        ):
            self.assertNotIn(forbidden, source)

    def test_failed_mcp_pair_surfaces_direct_child_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            control = root / "control"
            control.mkdir()
            context = mock.Mock(
                workspace=workspace,
                control_root=control,
                environment={"PATH": os.environ.get("PATH", "")},
            )
            exposure = McpExposure(
                name="hashmarks",
                command="/work/Hashmarks/.venv/bin/hashmarks",
                args=("--workspace", ".", "mcp"),
                cwd=workspace,
                semantic_identity={"name": "hashmarks", "transport": "stdio"},
            )
            process = SimpleNamespace(
                return_code=1,
                timed_out=False,
                stderr=(
                    b'Hashmarks MCP support requires the optional extra: '
                    b'pip install "hashmarks[mcp]"\n'
                ),
                stdout=b"",
            )
            with mock.patch(
                "benchmarks.harness.readiness.run_bounded",
                return_value=process,
            ) as bounded:
                detail = _mcp_startup_diagnostic(context, exposure)

            self.assertIn("direct-startup-exit=1", detail)
            self.assertIn("Hashmarks MCP support requires the optional extra", detail)
            self.assertTrue(bounded.call_args.kwargs["close_stdin"])
            self.assertEqual(
                bounded.call_args.kwargs["limits"].timeout_seconds,
                5,
            )

    def test_each_unique_runtime_pair_is_checked_once_without_retry(self) -> None:
        suite = fake_suite()
        calls: list[tuple[str, str | None]] = []

        def subject(definition):
            if definition["id"] == "hashmarks":
                return HashmarksSubject(timeout_seconds=15)
            return FakeSubject(str(definition["id"]))

        def agent(definition, *, budgets):
            self.assertEqual(budgets["timeout_seconds"], 15)
            return FakeAgent(str(definition["id"]), calls)

        observed = Observation(
            {
                "available": True,
                "version": "test",
                "executable_sha256": "a" * 64,
            },
            "test",
        )
        clean_source = (
            {
                "root": "/work/Hashmarks",
                "commit": "b" * 40,
                "tree": "c" * 40,
                "working_copy_sha256": "d" * 64,
                "working_copy_clean": True,
            },
            None,
        )

        environment = {
            "HASHMARKS_BENCH_SOURCE": "/work/Hashmarks",
            "BENCHMARK_OPENCODE_AGENT": "build",
        }
        with (
            mock.patch.dict(os.environ, environment, clear=False),
            mock.patch(
                "benchmarks.harness.readiness.build_subject",
                side_effect=subject,
            ),
            mock.patch(
                "benchmarks.harness.readiness.build_agent",
                side_effect=agent,
            ),
            mock.patch(
                "benchmarks.harness.readiness.observe_executable",
                return_value=observed,
            ),
            mock.patch.object(
                HashmarksSubject,
                "source_identity",
                return_value=clean_source,
            ),
            tempfile.TemporaryDirectory(),
        ):
            report = check_runtime_readiness(suite)

        states = {check.label: check.state for check in report.checks}
        self.assertEqual(states["hashmarks runtime"], "READY")
        self.assertEqual(states["enola runtime"], "READY")
        self.assertEqual(states["codex-native native config"], "READY")
        self.assertEqual(states["opencode-native native config"], "READY")
        self.assertEqual(
            states["codex-native -> hashmarks exposure"],
            "READY",
        )
        self.assertEqual(
            states["codex-native -> enola exposure"],
            "READY",
        )
        self.assertEqual(
            states["opencode-native -> hashmarks MCP"],
            "FAILED",
        )
        self.assertEqual(
            states["opencode-native -> enola MCP"],
            "CONNECTED",
        )
        self.assertFalse(report.ready)

        self.assertEqual(
            calls.count(("opencode-native", "hashmarks")),
            1,
        )
        self.assertEqual(
            calls.count(("opencode-native", "enola")),
            1,
        )
        self.assertEqual(
            calls.count(("codex-native", "hashmarks")),
            1,
        )
        self.assertEqual(
            calls.count(("codex-native", "enola")),
            1,
        )
        self.assertEqual(calls.count(("codex-native", None)), 1)
        self.assertEqual(calls.count(("opencode-native", None)), 1)


if __name__ == "__main__":
    unittest.main()
