"""Concrete Hashmarks repository-intelligence adapter."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
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
    require_source: bool = False

    def _source_root(self, context: TrialContext) -> Path | None:
        source = context.environment.get("HASHMARKS_BENCH_SOURCE")
        return Path(source).resolve() if source else None

    def _executable(self, context: TrialContext) -> str:
        root = self._source_root(context)
        if root is not None:
            return str((root / ".venv" / "bin" / "hashmarks").resolve())
        resolved = shutil.which("hashmarks", path=context.environment.get("PATH"))
        return str(Path(resolved).resolve()) if resolved else "hashmarks"

    def _source_identity(
        self, context: TrialContext
    ) -> tuple[dict[str, object] | None, str | None]:
        root = self._source_root(context)
        if root is None:
            return None, "HASHMARKS_BENCH_SOURCE is required for scored native runs"
        expected = Path(self._executable(context))
        if not expected.is_file():
            return None, f"Hashmarks benchmark executable does not exist: {expected}"
        try:
            values = []
            for args in (
                ("rev-parse", "HEAD"),
                ("rev-parse", "HEAD^{tree}"),
                ("diff", "--binary", "HEAD"),
                ("ls-files", "--others", "--exclude-standard", "-z"),
            ):
                result = subprocess.run(
                    ("git", "-C", str(root), *args),
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
                if result.returncode != 0:
                    return None, "cannot establish Hashmarks source identity"
                values.append(result.stdout)
            fingerprint = hashlib.sha256(values[2])
            untracked = [path for path in values[3].split(b"\0") if path]
            for path in untracked:
                fingerprint.update(path)
                fingerprint.update((root / os.fsdecode(path)).read_bytes())
        except (OSError, subprocess.TimeoutExpired):
            return None, "cannot fingerprint Hashmarks source checkout"
        return {
            "root": str(root),
            "commit": values[0].decode().strip(),
            "tree": values[1].decode().strip(),
            "working_copy_sha256": fingerprint.hexdigest(),
            "working_copy_clean": not values[2] and not untracked,
        }, None

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
            self._executable(context),
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
        executable = observe_executable(
            context,
            self._executable(context),
            version_args=("version",),
        )
        if not executable.payload["available"]:
            return executable
        source_identity, source_error = (
            self._source_identity(context) if self.require_source else (None, None)
        )
        if source_error:
            return Observation({"available": False, "reason": source_error}, "")
        sync = self._run(context, (*self._base(context), "map", "sync"))
        available = (
            not sync.executable_missing
            and not sync.timed_out
            and sync.return_code == 0
            and not sync.stdout_truncated
            and not sync.stderr_truncated
        )
        stderr = sync.stderr.decode("utf-8", errors="replace")
        detail = stderr.strip().splitlines()[-1] if stderr.strip() else ""
        reason = (
            None
            if available
            else (
                f"Hashmarks map sync failed (exit {sync.return_code})"
                + (f": {detail[:300]}" if detail else "")
            )
        )
        return Observation(
            {
                "available": available,
                "reason": reason,
                "observed_identity": {
                    "version": executable.payload["version"],
                    "executable_sha256": executable.payload["executable_sha256"],
                    "source": source_identity,
                },
                "sync": sync.metrics(),
                "stderr": stderr,
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
            command=self._executable(context),
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
        return (".hashmarks/**",)
