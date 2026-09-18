from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Iterable

from .bounded_process import ProcessLimits, run_bounded
from .command_manifest import CommandManifestError, CommandSpec, load_command_manifest


class CommandRunnerError(ValueError):
    pass


def _tracked_state(root: Path) -> tuple[str | None, set[str]]:
    result = run_bounded(
        repository_root=root,
        argv=("git", "status", "--porcelain=v1", "-z", "--untracked-files=no"),
        limits=ProcessLimits(timeout_seconds=5.0, max_stdout_bytes=2_000_000, max_stderr_bytes=100_000),
    )
    if result.executable_missing or result.return_code != 0 or result.stdout_truncated:
        return None, set()
    raw = result.stdout
    identity = "sha256:" + hashlib.sha256(raw).hexdigest()
    paths: set[str] = set()
    for token in raw.split(b"\0"):
        if not token:
            continue
        text = token.decode("utf-8", errors="replace")
        if len(text) >= 4:
            paths.add(text[3:].replace("\\", "/"))
    return identity, paths


def _allowed(path: str, patterns: tuple[str, ...]) -> bool:
    from .refactor_focus_discovery import is_excluded_repo_path
    return any(is_excluded_repo_path(path, (pattern,)) for pattern in patterns)


def classify_result(*, return_code: int | None, timed_out: bool, executable_missing: bool, stdout: str, stderr: str, policy_violation: bool) -> str:
    if policy_violation:
        return "policy_mutation_violation"
    if executable_missing:
        return "executable_missing"
    if timed_out:
        return "timeout"
    if return_code == 0:
        return "pass"
    text = (stdout + "\n" + stderr).lower()
    if "syntaxerror" in text or "syntax error" in text:
        return "syntax_compile_failure"
    if "importerror" in text or "modulenotfounderror" in text or "error collecting" in text:
        return "collection_import_failure"
    if "assertionerror" in text or " failed" in text or "failure" in text:
        return "assertion_test_failure"
    if "mypy" in text or "type error" in text:
        return "type_check_failure"
    if "ruff" in text or "lint" in text:
        return "lint_static_failure"
    if "network" in text or "connection" in text or "tls" in text:
        return "infrastructure_network_failure"
    return "unknown_failure"


def run_named_command(
    *,
    repository_root: Path,
    manifest_path: Path,
    name: str,
    selected_paths: Iterable[str] = (),
    timeout_seconds: float = 60.0,
    max_stdout_bytes: int = 1_000_000,
    max_stderr_bytes: int = 1_000_000,
) -> dict[str, object]:
    root = repository_root.resolve()
    target = manifest_path if manifest_path.is_absolute() else root / manifest_path
    try:
        manifest = load_command_manifest(target)
    except (OSError, CommandManifestError) as exc:
        raise CommandRunnerError(f"cannot load command manifest: {type(exc).__name__}") from exc
    if name not in manifest.commands:
        raise CommandRunnerError(f"unknown command: {name}")
    spec = manifest.commands[name]
    argv = list(spec.argv)
    selected = []
    for raw in selected_paths:
        p = Path(raw.replace("\\", "/"))
        if p.is_absolute() or ".." in p.parts:
            raise CommandRunnerError(f"selected path must be repository-relative: {raw}")
        selected.append(p.as_posix())
    if selected and not spec.append_selected_tests:
        raise CommandRunnerError(f"command {name!r} does not admit selected path arguments")
    argv.extend(selected)

    before_identity, before_dirty = _tracked_state(root)
    result = run_bounded(
        repository_root=root,
        argv=argv,
        cwd=spec.cwd,
        limits=ProcessLimits(
            timeout_seconds=timeout_seconds,
            max_stdout_bytes=max_stdout_bytes,
            max_stderr_bytes=max_stderr_bytes,
        ),
    )
    after_identity, after_dirty = _tracked_state(root)
    changed = sorted((before_dirty ^ after_dirty) | (after_dirty - before_dirty))
    unexpected = [p for p in changed if not _allowed(p, spec.allowed_mutation_paths)]
    policy_violation = bool(spec.must_not_modify_tracked_files and unexpected)
    stdout_text = result.stdout.decode("utf-8", errors="replace")
    stderr_text = result.stderr.decode("utf-8", errors="replace")
    classification = classify_result(
        return_code=result.return_code,
        timed_out=result.timed_out,
        executable_missing=result.executable_missing,
        stdout=stdout_text,
        stderr=stderr_text,
        policy_violation=policy_violation,
    )
    semantic = {
        "manifest_identity": manifest.identity,
        "command_identity": result.command_identity,
        "stage": spec.stage,
        "classification": classification,
        "return_code": result.return_code,
        "signal": result.signal,
        "timed_out": result.timed_out,
        "executable_missing": result.executable_missing,
        "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
        "unexpected_tracked_mutations": unexpected,
    }
    failure_identity = "sha256:" + hashlib.sha256(
        json.dumps(semantic, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "schema": {"name": "agent-economics-command-result", "version": 1},
        "command": {"name": name, "argv": argv, "cwd": spec.cwd, "stage": spec.stage, "identity": result.command_identity},
        "manifest_identity": manifest.identity,
        "status": "PASS" if classification == "pass" else "FAIL",
        "classification": classification,
        "failure_identity": failure_identity,
        "execution": result.metrics(),
        "stdout": stdout_text,
        "stderr": stderr_text,
        "workspace": {
            "before_identity": before_identity,
            "after_identity": after_identity,
            "unexpected_tracked_mutations": unexpected,
        },
        "authority": {
            "repair_performed": False,
            "ci_status": "NOT_RUN",
            "network_isolation_enforced": False,
            "sandbox_isolation_enforced": False,
        },
    }


def main(argv: list[str] | None = None) -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Run one declared repository command with hard bounds.")
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--selected-path", action="append", default=[])
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--max-stdout-bytes", type=int, default=1_000_000)
    parser.add_argument("--max-stderr-bytes", type=int, default=1_000_000)
    parser.add_argument("--artifact", type=Path)
    args = parser.parse_args(argv)
    payload = run_named_command(
        repository_root=args.repository_root,
        manifest_path=args.manifest,
        name=args.name,
        selected_paths=args.selected_path,
        timeout_seconds=args.timeout_seconds,
        max_stdout_bytes=args.max_stdout_bytes,
        max_stderr_bytes=args.max_stderr_bytes,
    )
    rendered = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if args.artifact:
        target = args.artifact if args.artifact.is_absolute() else args.repository_root / args.artifact
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
