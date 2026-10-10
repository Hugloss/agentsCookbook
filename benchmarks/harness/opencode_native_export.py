"""E253: bounded native OpenCode session discovery and export.

The session is selected using a new exact title, directory and start epoch.
An arbitrary 'latest session' or an agent-authored log is never accepted.
The native command runs with the identical isolated environment after
the trial, before any evidence is promoted. The resulting export remains
host-local observational data, not independently authenticated agent bytes.
"""

from __future__ import annotations

import json
import os
import resource
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping

from .opencode_native_session import MAX_EXPORT_BYTES

SCHEMA = "agentscookbook.native-session-export-acquisition.v1"
MAX_INDEX_BYTES = 262_144


def _limit_output(size: int) -> None:
    resource.setrlimit(resource.RLIMIT_FSIZE, (size, size))


def _run_bounded_native(
    argv: list[str], *, workspace: Path, environment: Mapping[str, str],
    max_bytes: int, timeout: int = 20,
) -> bytes:
    """Native stdout is redirected to a bounded host-owned temporary file.

    Avoid unbounded PIPE capture and never propagate provider secrets or
    arbitrary child stdout/stderr in an exception.
    """
    if (max_bytes <= 0 or max_bytes > MAX_EXPORT_BYTES
            or timeout <= 0 or timeout > 60):
        raise ValueError("invalid-native-export-limits")
    try:
        with tempfile.TemporaryFile() as capture:
            run = subprocess.run(
                argv, cwd=workspace, env=dict(environment),
                stdout=capture, stderr=subprocess.DEVNULL,
                timeout=timeout, check=False,
                preexec_fn=lambda: _limit_output(max_bytes),
            )
            if run.returncode != 0:
                raise ValueError("native-session-command-failed")
            capture.seek(0, os.SEEK_END)
            count = capture.tell()
            if not 0 < count <= max_bytes:
                raise ValueError("native-session-export-empty-or-oversized")
            capture.seek(0)
            return capture.read(max_bytes + 1)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError("native-session-command-unavailable-or-timed-out") from None


def select_native_session(index: bytes, *, exact_title: str,
                          workspace: Path, started_at_ms: int) -> str:
    if (not isinstance(index, bytes) or not 0 < len(index) <= MAX_INDEX_BYTES
            or not isinstance(exact_title, str) or not exact_title
            or type(started_at_ms) is not int or started_at_ms < 1):
        raise ValueError("invalid-native-session-selection-authority")
    try:
        listing = json.loads(index)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("invalid-native-session-index") from exc
    if not isinstance(listing, list) or len(listing) > 20:
        raise ValueError("invalid-native-session-population")
    matches = [
        item for item in listing
        if isinstance(item, dict)
        and item.get("title") == exact_title
        and item.get("directory") == str(workspace.resolve())
        and type(item.get("updated")) is int
        and item["updated"] >= started_at_ms
        and isinstance(item.get("id"), str)
        and 0 < len(item["id"]) <= 256
    ]
    if len(matches) != 1:
        raise ValueError("native-session-exact-selection-ambiguous-or-missing")
    return matches[0]["id"]


def acquire_native_export(
    executable: Path, *, workspace: Path,
    environment: Mapping[str, str], exact_title: str, started_at_ms: int,
) -> tuple[str, bytes]:
    source = _run_bounded_native(
        [str(executable), "session", "list", "--format", "json",
         "--max-count", "20"],
        workspace=workspace, environment=environment,
        max_bytes=MAX_INDEX_BYTES,
    )
    session_id = select_native_session(
        source, exact_title=exact_title, workspace=workspace,
        started_at_ms=started_at_ms,
    )
    exported = _run_bounded_native(
        [str(executable), "export", session_id],
        workspace=workspace, environment=environment,
        max_bytes=MAX_EXPORT_BYTES,
    )
    return session_id, exported
