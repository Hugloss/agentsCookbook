"""Concrete Hashmarks repository-intelligence adapter."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from benchmarks.adapters.runtime import observe_executable
from benchmarks.harness.model import (
    McpExposure,
    Observation,
    ParticipantIdentity,
    TrialContext,
)
from scripts.agent_economics.bounded_process import ProcessLimits, run_bounded


@dataclass(frozen=True)
class HashmarksSubject:
    timeout_seconds: int = 120

    def identity(self) -> ParticipantIdentity:
        return ParticipantIdentity(
            "hashmarks",
            "repository_intelligence",
            "runtime-observed",
            {"surface": "cli+mcp", "state": "explicit-isolated"},
        )

    def _state_dir(self, context: TrialContext) -> Path:
        path = context.control_root / "hashmarks-state"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _base(self, context: TrialContext) -> tuple[str, ...]:
        return (
            "hashmarks",
            "--workspace",
            ".",
            "--state-dir",
            str(self._state_dir(context)),
        )

    def _run(self, context: TrialContext, argv: tuple[str, ...]):
        return run_bounded(
            repository_root=context.workspace,
            argv=argv,
            environment=context.environment,
            limits=ProcessLimits(
                timeout_seconds=self.timeout_seconds,
                max_stdout_bytes=10_000_000,
                max_stderr_bytes=2_000_000,
            ),
        )

    def prepare(self, context: TrialContext) -> Observation:
        executable = observe_executable(context, "hashmarks")
        if not executable.payload["available"]:
            return executable
        sync = self._run(context, (*self._base(context), "map", "sync"))
        available = (
            not sync.executable_missing
            and not sync.timed_out
            and sync.return_code == 0
            and not sync.stdout_truncated
            and not sync.stderr_truncated
        )
        return Observation(
            {
                "available": available,
                "observed_identity": {
                    "version": executable.payload["version"],
                    "executable_sha256": executable.payload["executable_sha256"],
                },
                "sync": sync.metrics(),
                "stderr": sync.stderr.decode("utf-8", errors="replace"),
            },
            sync.stdout.decode("utf-8", errors="replace"),
            {"duration_ms": sync.elapsed_ms},
        )

    def query(self, context: TrialContext, prompt: str) -> Observation:
        result = self._run(context, (*self._base(context), "find", prompt))
        return Observation(
            {
                "available": not result.executable_missing,
                "invoked": True,
                "process": result.metrics(),
                "stderr": result.stderr.decode("utf-8", errors="replace"),
            },
            result.stdout.decode("utf-8", errors="replace"),
            {"duration_ms": result.elapsed_ms, "response_bytes": len(result.stdout)},
        )

    def post_change(
        self,
        context: TrialContext,
        changed_paths: tuple[str, ...],
    ) -> Observation:
        result = self._run(context, (*self._base(context), "map", "sync"))
        return Observation(
            {
                "changed_paths": list(changed_paths),
                "process": result.metrics(),
            },
            result.stdout.decode("utf-8", errors="replace"),
            {"duration_ms": result.elapsed_ms},
        )

    def cleanup(self, context: TrialContext) -> Observation:
        return Observation({}, "")

    def mcp_exposure(self, context: TrialContext) -> McpExposure:
        return McpExposure(
            name="hashmarks",
            command="hashmarks",
            args=(
                "--workspace",
                ".",
                "--state-dir",
                str(self._state_dir(context)),
                "mcp",
            ),
            cwd=context.workspace,
            semantic_identity={
                "name": "hashmarks",
                "transport": "stdio",
                "workspace": "trial-workspace",
                "state": "isolated-explicit-state-dir",
            },
        )

    def generated_globs(self) -> tuple[str, ...]:
        return ()
