from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


class BoundedProcessError(ValueError):
    pass


@dataclass(frozen=True)
class ProcessLimits:
    timeout_seconds: float = 30.0
    max_stdout_bytes: int = 1_000_000
    max_stderr_bytes: int = 1_000_000

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise BoundedProcessError("timeout_seconds must be > 0")
        if self.max_stdout_bytes < 1 or self.max_stderr_bytes < 1:
            raise BoundedProcessError("stdout/stderr byte bounds must be >= 1")


@dataclass(frozen=True)
class ProcessResult:
    argv: tuple[str, ...]
    cwd: str
    command_identity: str
    return_code: int | None
    signal: int | None
    timed_out: bool
    executable_missing: bool
    stdout: bytes
    stderr: bytes
    stdout_truncated: bool
    stderr_truncated: bool
    elapsed_ms: float
    process_tree_termination: str

    def metrics(self) -> dict[str, object]:
        return {
            "command_identity": self.command_identity,
            "return_code": self.return_code,
            "signal": self.signal,
            "timed_out": self.timed_out,
            "executable_missing": self.executable_missing,
            "stdout_bytes": len(self.stdout),
            "stderr_bytes": len(self.stderr),
            "stdout_truncated": self.stdout_truncated,
            "stderr_truncated": self.stderr_truncated,
            "elapsed_ms": self.elapsed_ms,
            "process_tree_termination": self.process_tree_termination,
        }


def process_tree_capability() -> dict[str, object]:
    if os.name != "nt":
        return {"available": True, "mechanism": "posix-process-group"}
    taskkill = shutil.which("taskkill")
    return {
        "available": taskkill is not None,
        "mechanism": "windows-taskkill-tree" if taskkill else None,
        "reason": None if taskkill else "taskkill executable unavailable",
    }


def _identity(argv: Sequence[str], cwd_relative: str) -> str:
    raw = json.dumps({"argv": list(argv), "cwd": cwd_relative}, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def safe_cwd(repository_root: Path, cwd: Path | str = ".") -> tuple[Path, str]:
    root = repository_root.resolve()
    candidate = Path(cwd)
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise BoundedProcessError(f"command cwd escapes repository root: {cwd}") from exc
    if not resolved.is_dir():
        raise BoundedProcessError(f"command cwd does not exist: {relative.as_posix()}")
    return resolved, relative.as_posix() if relative != Path(".") else "."


def _terminate_tree(process: subprocess.Popen[bytes]) -> str:
    if process.poll() is not None:
        return "already-exited"
    if os.name == "nt":
        taskkill = shutil.which("taskkill")
        if taskkill is None:
            process.kill()
            return "parent-only-fallback"
        try:
            subprocess.run(
                [taskkill, "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
            return "windows-taskkill-tree"
        except (OSError, subprocess.SubprocessError):
            process.kill()
            return "parent-only-fallback"
    try:
        os.killpg(process.pid, signal.SIGKILL)
        return "posix-process-group"
    except (OSError, ProcessLookupError):
        try:
            process.kill()
        except OSError:
            pass
        return "parent-only-fallback"


def run_bounded(
    *,
    repository_root: Path,
    argv: Sequence[str],
    cwd: Path | str = ".",
    limits: ProcessLimits = ProcessLimits(),
) -> ProcessResult:
    if not argv or not all(isinstance(item, str) and item for item in argv):
        raise BoundedProcessError("argv must contain non-empty strings")
    resolved_cwd, cwd_relative = safe_cwd(repository_root, cwd)
    command_identity = _identity(argv, cwd_relative)
    started = time.perf_counter()
    popen_kwargs: dict[str, object] = {
        "cwd": resolved_cwd, "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "shell": False,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True
    try:
        process = subprocess.Popen(list(argv), **popen_kwargs)
    except FileNotFoundError:
        return ProcessResult(
            argv=tuple(argv), cwd=cwd_relative, command_identity=command_identity,
            return_code=None, signal=None, timed_out=False, executable_missing=True,
            stdout=b"", stderr=b"", stdout_truncated=False, stderr_truncated=False,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 3),
            process_tree_termination="not-needed",
        )
    except OSError as exc:
        raise BoundedProcessError(f"command failed to start: {type(exc).__name__}") from exc

    stdout, stderr = bytearray(), bytearray()
    stdout_truncated, stderr_truncated = threading.Event(), threading.Event()
    termination = {"value": "not-needed"}
    termination_lock = threading.Lock()

    def terminate() -> None:
        with termination_lock:
            if process.poll() is None:
                termination["value"] = _terminate_tree(process)

    def drain(stream: object, sink: bytearray, maximum: int, truncated: threading.Event) -> None:
        while True:
            chunk = stream.read(65536)  # type: ignore[attr-defined]
            if not chunk:
                return
            remaining = maximum - len(sink)
            if remaining > 0:
                sink.extend(chunk[:remaining])
            if len(chunk) > max(remaining, 0):
                truncated.set()
                terminate()
                return

    assert process.stdout is not None and process.stderr is not None
    threads = [
        threading.Thread(target=drain, args=(process.stdout, stdout, limits.max_stdout_bytes, stdout_truncated), daemon=True),
        threading.Thread(target=drain, args=(process.stderr, stderr, limits.max_stderr_bytes, stderr_truncated), daemon=True),
    ]
    for thread in threads:
        thread.start()
    timed_out = threading.Event()

    def timeout_kill() -> None:
        timed_out.set()
        terminate()

    timer = threading.Timer(limits.timeout_seconds, timeout_kill)
    timer.daemon = True
    timer.start()
    try:
        return_code = process.wait()
    finally:
        timer.cancel()
        for thread in threads:
            thread.join(timeout=1.0)
    sig = -return_code if return_code < 0 else None
    return ProcessResult(
        argv=tuple(argv), cwd=cwd_relative, command_identity=command_identity,
        return_code=return_code, signal=sig, timed_out=timed_out.is_set(),
        executable_missing=False, stdout=bytes(stdout), stderr=bytes(stderr),
        stdout_truncated=stdout_truncated.is_set(), stderr_truncated=stderr_truncated.is_set(),
        elapsed_ms=round((time.perf_counter() - started) * 1000, 3),
        process_tree_termination=termination["value"],
    )
