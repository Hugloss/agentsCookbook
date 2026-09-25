"""Observed executable identity for benchmark participants."""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from benchmarks.harness.model import Observation, TrialContext
from scripts.agent_economics.bounded_process import ProcessLimits, run_bounded


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def observe_executable(
    context: TrialContext,
    command: str,
    *,
    version_args: tuple[str, ...] = ("--version",),
    timeout_seconds: float = 30.0,
) -> Observation:
    resolved = shutil.which(command)
    result = run_bounded(
        repository_root=context.workspace,
        argv=(command, *version_args),
        environment=context.environment,
        limits=ProcessLimits(
            timeout_seconds=timeout_seconds,
            max_stdout_bytes=200_000,
            max_stderr_bytes=200_000,
        ),
    )
    path = Path(resolved).resolve() if resolved else None
    executable_sha256 = None
    if path is not None and path.is_file():
        try:
            executable_sha256 = _sha256_file(path)
        except OSError:
            executable_sha256 = None
    available = (
        resolved is not None
        and not result.executable_missing
        and not result.timed_out
        and result.return_code == 0
        and not result.stdout_truncated
        and not result.stderr_truncated
    )
    return Observation(
        {
            "available": available,
            "command": command,
            "version": result.stdout.decode("utf-8", errors="replace").strip(),
            "executable_sha256": executable_sha256,
            "process": result.metrics(),
            "stderr": result.stderr.decode("utf-8", errors="replace"),
        },
        result.stdout.decode("utf-8", errors="replace"),
        {"duration_ms": result.elapsed_ms},
    )
