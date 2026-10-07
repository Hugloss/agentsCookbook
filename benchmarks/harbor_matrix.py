"""Harbor-backed cross-harness benchmark projection.

agentsCookbook owns experiment semantics; Harbor is execution infrastructure.
Only read-only repository-location tasks are projected by this v1 bridge.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from benchmarks.config import load_env_values
from benchmarks.harness.source import materialize_repository
from benchmarks.harness.suite import SuiteDefinition, load_suite

MATRIX_SCHEMA = "agentscookbook.harbor-harness-matrix.v1"
RESULT_SCHEMA = "agentscookbook.harbor-harness-trial.v1"
REPORT_SCHEMA = "agentscookbook.harbor-harness-report.v1"
HARBOR_ENV_KEYS = frozenset(
    {
        "HASHMARKS_BENCH_SOURCE",
        "BENCHMARK_HARBOR_EXECUTABLE",
        "BENCHMARK_HARBOR_MODEL",
        "BENCHMARK_HARBOR_ROOT",
        "BENCHMARK_HARBOR_PASSTHROUGH_ENV_KEYS",
    }
)


class HarborMatrixError(ValueError):
    pass


@dataclass(frozen=True)
class HarborSettings:
    executable: str
    model: str
    root: Path
    hashmarks_source: Path
    passthrough_env_keys: tuple[str, ...]


@dataclass(frozen=True)
class MatrixMode:
    tasks: tuple[str, ...]
    attempts: int


def _csv(raw: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(part.strip() for part in raw.split(",") if part.strip())
    )


def load_settings(
    env_file: Path,
    *,
    host: Mapping[str, str] | None = None,
) -> HarborSettings:
    host = os.environ if host is None else host
    values = load_env_values(env_file, allowed_keys=HARBOR_ENV_KEYS)
    source = values.get("HASHMARKS_BENCH_SOURCE")
    model = values.get("BENCHMARK_HARBOR_MODEL")
    if not source:
        raise HarborMatrixError("HASHMARKS_BENCH_SOURCE is required")
    if not model:
        raise HarborMatrixError("BENCHMARK_HARBOR_MODEL is required")
    passthrough = _csv(
        values.get("BENCHMARK_HARBOR_PASSTHROUGH_ENV_KEYS", "")
    )
    missing = sorted(key for key in passthrough if not host.get(key))
    if missing:
        raise HarborMatrixError(
            "missing host environment value(s) selected for Harbor: "
            + ", ".join(missing)
        )
    return HarborSettings(
        executable=values.get("BENCHMARK_HARBOR_EXECUTABLE") or "harbor",
        model=model,
        root=Path(
            values.get("BENCHMARK_HARBOR_ROOT")
            or ".benchmark-runs/harbor-harness-v1"
        ),
        hashmarks_source=Path(source).expanduser().resolve(),
        passthrough_env_keys=passthrough,
    )


def load_matrix(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HarborMatrixError(
            f"cannot load Harbor matrix {path}: {exc}"
        ) from exc
    if not isinstance(value, dict) or value.get("schema") != MATRIX_SCHEMA:
        raise HarborMatrixError(
            f"invalid Harbor matrix schema in {path}"
        )
    if not isinstance(value.get("harnesses"), list) or not value["harnesses"]:
        raise HarborMatrixError(
            "Harbor matrix needs non-empty harnesses"
        )
    if not all(
        isinstance(item, str) and item
        for item in value["harnesses"]
    ):
        raise HarborMatrixError(
            "Harbor matrix harness ids must be non-empty strings"
        )
    if value.get("subjects") != ["none", "hashmarks"]:
        raise HarborMatrixError(
            "Harbor matrix subjects must be exactly none, hashmarks"
        )
    if not isinstance(value.get("modes"), dict) or not value["modes"]:
        raise HarborMatrixError(
            "Harbor matrix needs at least one mode"
        )
    return value


def mode_contract(
    matrix: Mapping[str, Any],
    name: str,
) -> MatrixMode:
    raw = matrix.get("modes", {}).get(name)
    if not isinstance(raw, dict):
        raise HarborMatrixError(
            f"unknown Harbor matrix mode: {name}"
        )
    tasks = raw.get("tasks")
    attempts = raw.get("attempts")
    if (
        not isinstance(tasks, list)
        or not tasks
        or not all(
            isinstance(item, str) and item
            for item in tasks
        )
    ):
        raise HarborMatrixError(
            f"Harbor mode {name} needs non-empty tasks"
        )
    if (
        isinstance(attempts, bool)
        or not isinstance(attempts, int)
        or attempts < 1
    ):
        raise HarborMatrixError(
            f"Harbor mode {name} attempts must be >= 1"
        )
    return MatrixMode(
        tuple(tasks),
        attempts,
    )


def _select(
    available: Iterable[str],
    requested: Iterable[str],
    *,
    label: str,
) -> tuple[str, ...]:
    available_tuple = tuple(available)
    selected = tuple(
        dict.fromkeys(requested)
    ) or available_tuple
    unknown = sorted(
        set(selected)
        - set(available_tuple)
    )
    if unknown:
        raise HarborMatrixError(
            f"unknown Harbor {label}(s): "
            + ", ".join(unknown)
        )
    return selected


def _task_expected(
    task: Mapping[str, Any],
) -> dict[str, str]:
    if (
        task.get("mode") != "read_only"
        or task.get("mutation") is not None
    ):
        raise HarborMatrixError(
            "Harbor v1 bridge only admits read-only "
            f"unmutated tasks: {task.get('id')}"
        )
    oracle = task.get("oracle")
    if (
        not isinstance(oracle, dict)
        or oracle.get("adapter")
        != "repository-location-json"
    ):
        raise HarborMatrixError(
            "Harbor v1 bridge requires "
            "repository-location-json oracle: "
            f"{task.get('id')}"
        )
    config = oracle.get("configuration")
    expected = (
        config.get("expected")
        if isinstance(config, dict)
        else None
    )
    if (
        not isinstance(expected, dict)
        or set(expected) != {"path", "symbol"}
        or not all(
            isinstance(expected.get(key), str)
            and expected[key]
            for key in expected
        )
    ):
        raise HarborMatrixError(
            "invalid repository-location oracle: "
            f"{task.get('id')}"
        )
    return {
        "path": str(expected["path"]),
        "symbol": str(expected["symbol"]),
    }


def validate_projection(
    *,
    matrix: Mapping[str, Any],
    suite: SuiteDefinition,
    mode: MatrixMode,
    harnesses: tuple[str, ...],
    tasks: tuple[str, ...],
) -> None:
    if (
        Path(str(matrix["suite"])).resolve()
        != suite.root
    ):
        raise HarborMatrixError(
            "matrix suite path does not match loaded suite"
        )
    for task_id in tasks:
        task = suite.tasks.get(task_id)
        if not isinstance(task, dict):
            raise HarborMatrixError(
                f"unknown suite task: {task_id}"
            )
        _task_expected(task)
    if not harnesses or mode.attempts < 1:
        raise HarborMatrixError(
            "Harbor projection is empty"
        )


def plan_rows(
    *,
    harnesses: tuple[str, ...],
    tasks: tuple[str, ...],
    attempts: int,
) -> list[dict[str, object]]:
    return [
        {
            "task": task,
            "harness": harness,
            "subject": subject,
            "attempt": attempt,
        }
        for task in tasks
        for harness in harnesses
        for subject in (
            "none",
            "hashmarks",
        )
        for attempt in range(
            1,
            attempts + 1,
        )
    ]


def _run(
    argv: list[str],
    *,
    env: Mapping[str, str] | None = None,
    timeout: float = 60,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            argv,
            env=None if env is None else dict(env),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except (
        OSError,
        subprocess.TimeoutExpired,
    ) as exc:
        raise HarborMatrixError(
            "command failed to start: "
            f"{argv[0]}: {exc}"
        ) from exc


def _require_command(
    argv: list[str],
    *,
    label: str,
) -> str:
    result = _run(argv)
    if result.returncode:
        detail = (
            result.stderr
            or result.stdout
        ).strip()[-1200:]
        raise HarborMatrixError(
            f"{label} unavailable: "
            f"{detail or 'non-zero exit'}"
        )
    return (
        result.stdout
        or result.stderr
    ).strip()


def _git_clean_identity(
    source: Path,
) -> dict[str, str]:
    if not source.is_dir():
        raise HarborMatrixError(
            "Hashmarks source does not exist: "
            f"{source}"
        )

    def git(
        *args: str,
    ) -> str:
        result = _run(
            [
                "git",
                "-C",
                str(source),
                *args,
            ],
            timeout=30,
        )
        if result.returncode:
            raise HarborMatrixError(
                "cannot establish Hashmarks "
                "source identity: "
                + result.stderr.strip()
            )
        return result.stdout.strip()

    if git(
        "status",
        "--porcelain=v1",
        "--untracked-files=normal",
    ):
        raise HarborMatrixError(
            "Hashmarks Harbor subject source "
            "must be a clean committed checkout"
        )
    return {
        "commit": git(
            "rev-parse",
            "HEAD",
        ),
        "tree": git(
            "rev-parse",
            "HEAD^{tree}",
        ),
    }


def _hashmarks_probe(
    settings: HarborSettings,
    host: Mapping[str, str],
) -> dict[str, Any]:
    executable = (
        settings.hashmarks_source
        / ".venv"
        / "bin"
        / "hashmarks"
    )
    if not executable.is_file():
        raise HarborMatrixError(
            "Hashmarks executable does not exist: "
            f"{executable}"
        )
    result = _run(
        [
            str(executable),
            "--workspace",
            str(settings.hashmarks_source),
            "doctor",
            "--mcp",
        ],
        env=host,
        timeout=60,
    )
    if result.returncode:
        detail = (
            result.stderr
            or result.stdout
        ).strip()[-1600:]
        raise HarborMatrixError(
            "Hashmarks MCP readiness failed: "
            f"{detail}"
        )
    try:
        payload = json.loads(
            result.stdout
        )
    except json.JSONDecodeError as exc:
        raise HarborMatrixError(
            "Hashmarks doctor --mcp "
            "did not emit JSON"
        ) from exc
    mcp = (
        payload.get("mcp")
        if isinstance(payload, dict)
        else None
    )
    if not (
        isinstance(mcp, dict)
        and mcp.get("schema")
        == "hashmarks.mcp-readiness.v1"
        and mcp.get("ready") is True
        and mcp.get("authority")
        == "diagnostic-only"
        and mcp.get(
            "consumer_verification_required"
        )
        is True
    ):
        raise HarborMatrixError(
            "Hashmarks doctor --mcp did not "
            "prove local MCP readiness"
        )
    return mcp


def preflight(
    *,
    settings: HarborSettings,
    matrix: Mapping[str, Any],
    suite: SuiteDefinition,
    mode: MatrixMode,
    harnesses: tuple[str, ...],
    tasks: tuple[str, ...],
    host: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    host = (
        os.environ
        if host is None
        else host
    )
    validate_projection(
        matrix=matrix,
        suite=suite,
        mode=mode,
        harnesses=harnesses,
        tasks=tasks,
    )
    source_identity = _git_clean_identity(
        settings.hashmarks_source
    )
    mcp = _hashmarks_probe(
        settings,
        host,
    )
    harbor_version = _require_command(
        [
            settings.executable,
            "--version",
        ],
        label="Harbor",
    )
    docker_version = _require_command(
        [
            "docker",
            "version",
            "--format",
            "{{.Server.Version}}",
        ],
        label="Docker",
    )
    return {
        "schema": MATRIX_SCHEMA,
        "ready": True,
        "model": settings.model,
        "harnesses": list(harnesses),
        "tasks": list(tasks),
        "attempts": mode.attempts,
        "trials": len(
            plan_rows(
                harnesses=harnesses,
                tasks=tasks,
                attempts=mode.attempts,
            )
        ),
        "harbor": {
            "executable": settings.executable,
            "version": harbor_version,
        },
        "docker": {
            "server_version": docker_version,
        },
        "hashmarks": {
            **source_identity,
            "mcp_contract_identity": mcp.get(
                "contract_identity"
            ),
            "operation_contract_identity": mcp.get(
                "operation_contract_identity"
            ),
            "tool_count": mcp.get(
                "tool_count"
            ),
        },
        "passthrough_env_keys": list(
            settings.passthrough_env_keys
        ),
        "secrets_in_receipt": False,
    }


def _copy_tracked_tree(
    source: Path,
    destination: Path,
) -> None:
    result = _run(
        [
            "git",
            "-C",
            str(source),
            "ls-files",
            "-z",
        ],
        timeout=30,
    )
    if result.returncode:
        raise HarborMatrixError(
            "cannot enumerate Hashmarks source: "
            + result.stderr.strip()
        )
    destination.mkdir(
        parents=True,
        exist_ok=True,
    )
    for raw in result.stdout.split("\0"):
        if not raw:
            continue
        relative = Path(raw)
        src = source / raw
        dst = destination / relative
        dst.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        if src.is_symlink():
            dst.symlink_to(
                os.readlink(src)
            )
        elif src.is_file():
            shutil.copy2(
                src,
                dst,
            )
        else:
            raise HarborMatrixError(
                "unsupported tracked "
                "Hashmarks entry: "
                f"{relative}"
            )


def _dockerfile() -> str:
    return """FROM python:3.13-bookworm
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl ca-certificates nodejs npm ripgrep \
    && rm -rf /var/lib/apt/lists/*
COPY workspace /workspace
COPY hashmarks-source /opt/hashmarks-source
RUN python -m pip install --no-cache-dir "/opt/hashmarks-source[mcp]"
WORKDIR /workspace
"""


def _task_toml(
    task: Mapping[str, Any],
) -> str:
    timeout = float(
        task.get(
            "budgets",
            {},
        ).get(
            "timeout_seconds",
            600,
        )
    )
    return (
        'version = "1.0"\n\n'
        "[metadata]\n"
        'category = "repository-intelligence"\n'
        f'tags = ["agentscookbook", "harbor", "{task["family"]}"]\n\n'
        "[verifier]\n"
        "timeout_sec = 60.0\n\n"
        "[agent]\n"
        f"timeout_sec = {timeout:.1f}\n\n"
        "[environment]\n"
        'network_mode = "public"\n'
        "build_timeout_sec = 600.0\n"
        "cpus = 2\n"
        "memory_mb = 4096\n"
        "storage_mb = 10240\n"
    )


def _instruction(
    task: Mapping[str, Any],
) -> str:
    return (
        str(task["prompt"]).rstrip()
        + "\n\n"
        + "For this Harbor evaluation, also write "
        + "that exact JSON object to "
        + "/workspace/.agentscookbook-answer.json. "
        + "Do not modify tracked repository files.\n"
    )


def _verifier(
    expected: Mapping[str, str],
) -> str:
    expected_json = json.dumps(
        dict(expected),
        sort_keys=True,
    )
    return f"""#!/bin/sh
set -eu
mkdir -p /logs/verifier
reward=0
if git -C /workspace diff --quiet -- . && git -C /workspace diff --cached --quiet -- .; then
  if python3 - <<'PY'
import json
from pathlib import Path
expected = {expected_json}
path = Path("/workspace/.agentscookbook-answer.json")
if not path.is_file():
    raise SystemExit(1)
try:
    observed = json.loads(path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    raise SystemExit(1)
raise SystemExit(0 if observed == expected else 1)
PY
  then
    reward=1
  fi
fi
printf '%s\\n' "$reward" > /logs/verifier/reward.txt
exit 0
"""


def prepare_task(
    *,
    suite: SuiteDefinition,
    task_id: str,
    destination: Path,
    cache_root: Path,
    hashmarks_source: Path,
) -> Path:
    task = suite.tasks[task_id]
    expected = _task_expected(
        task
    )
    if destination.exists():
        shutil.rmtree(
            destination
        )
    environment = (
        destination
        / "environment"
    )
    tests = (
        destination
        / "tests"
    )
    environment.mkdir(
        parents=True,
    )
    tests.mkdir(
        parents=True,
    )
    materialize_repository(
        repository=task["repository"],
        destination=(
            environment
            / "workspace"
        ),
        cache_root=cache_root,
    )
    _copy_tracked_tree(
        hashmarks_source,
        environment
        / "hashmarks-source",
    )
    (
        environment
        / "Dockerfile"
    ).write_text(
        _dockerfile(),
        encoding="utf-8",
    )
    (
        destination
        / "instruction.md"
    ).write_text(
        _instruction(task),
        encoding="utf-8",
    )
    (
        destination
        / "task.toml"
    ).write_text(
        _task_toml(task),
        encoding="utf-8",
    )
    verifier = (
        tests
        / "test.sh"
    )
    verifier.write_text(
        _verifier(expected),
        encoding="utf-8",
    )
    verifier.chmod(
        0o755
    )
    return destination


def write_mcp_config(
    path: Path,
) -> Path:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    payload = {
        "mcpServers": {
            "hashmarks": {
                "command": "hashmarks",
                "args": [
                    "--workspace",
                    "/workspace",
                    "--state-dir",
                    "/tmp/hashmarks-state",
                    "mcp",
                ],
            }
        }
    }
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _credential_file(
    run_root: Path,
    *,
    keys: tuple[str, ...],
    host: Mapping[str, str],
) -> Path | None:
    if not keys:
        return None
    path = (
        run_root
        / ".harbor-env"
    )
    with path.open(
        "w",
        encoding="utf-8",
    ) as stream:
        for key in keys:
            value = (
                host[key]
                .replace(
                    "\\",
                    "\\\\",
                )
                .replace(
                    "\n",
                    "\\n",
                )
            )
            stream.write(
                f"{key}={value}\n"
            )
    path.chmod(
        0o600
    )
    return path


def harbor_argv(
    *,
    settings: HarborSettings,
    task_path: Path,
    harness: str,
    trial_id: str,
    jobs_root: Path,
    credential_file: Path | None,
    mcp_config: Path | None,
) -> list[str]:
    argv = [
        settings.executable,
        "run",
        "-p",
        str(task_path),
        "-a",
        harness,
        "-m",
        settings.model,
        "-o",
        str(jobs_root),
        "--job-name",
        trial_id,
        "--n-concurrent",
        "1",
        "--n-attempts",
        "1",
        "-y",
    ]
    if credential_file is not None:
        argv.extend(
            (
                "--env-file",
                str(credential_file),
            )
        )
    if mcp_config is not None:
        argv.extend(
            (
                "--mcp-config",
                str(mcp_config),
            )
        )
    return argv


def _reward(
    path: Path,
) -> float | None:
    try:
        if path.name == "reward.txt":
            return float(
                path.read_text(
                    encoding="utf-8",
                ).strip()
            )
        value = json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
    ):
        return None
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
    ):
        return float(value)
    if isinstance(value, dict):
        nested = value.get(
            "reward"
        )
        if (
            isinstance(
                nested,
                (int, float),
            )
            and not isinstance(
                nested,
                bool,
            )
        ):
            return float(
                nested
            )
    return None


def find_reward(
    job_root: Path,
) -> tuple[float | None, str | None]:
    candidates = (
        sorted(
            job_root.rglob(
                "reward.txt"
            )
        )
        + sorted(
            job_root.rglob(
                "reward.json"
            )
        )
    )
    observed = [
        (
            value,
            path,
        )
        for path in candidates
        if (
            value := _reward(path)
        )
        is not None
    ]
    if (
        len(observed) == 1
        or (
            observed
            and len(
                {
                    value
                    for value, _path
                    in observed
                }
            )
            == 1
        )
    ):
        value, path = observed[-1]
        return (
            value,
            str(path),
        )
    return (
        None,
        None,
    )


def _trial_id(
    row: Mapping[str, object],
) -> str:
    return (
        f'{row["task"]}--{row["harness"]}--{row["subject"]}'
        f'--{int(row["attempt"]):02d}'
    )


def execute_trial(
    *,
    settings: HarborSettings,
    row: Mapping[str, object],
    task_path: Path,
    run_root: Path,
    credential_file: Path | None,
    mcp_config: Path,
    host: Mapping[str, str],
) -> dict[str, Any]:
    trial_id = _trial_id(
        row
    )
    jobs_root = (
        run_root
        / "jobs"
    )
    jobs_root.mkdir(
        parents=True,
        exist_ok=True,
    )
    selected_mcp = (
        mcp_config
        if row["subject"]
        == "hashmarks"
        else None
    )
    argv = harbor_argv(
        settings=settings,
        task_path=task_path,
        harness=str(
            row["harness"]
        ),
        trial_id=trial_id,
        jobs_root=jobs_root,
        credential_file=credential_file,
        mcp_config=selected_mcp,
    )
    started = time.monotonic()
    try:
        result = _run(
            argv,
            env=host,
            timeout=1800,
        )
        return_code = (
            result.returncode
        )
        stderr = (
            result.stderr
            .strip()[-4000:]
        )
    except HarborMatrixError as exc:
        return_code = 127
        stderr = str(exc)
    reward, reward_path = find_reward(
        jobs_root
        / trial_id
    )
    status = (
        "COMPLETE"
        if reward is not None
        else "INCOMPLETE"
    )
    return {
        "schema": RESULT_SCHEMA,
        "trial_id": trial_id,
        **{
            key: row[key]
            for key in (
                "task",
                "harness",
                "subject",
                "attempt",
            )
        },
        "model": settings.model,
        "status": status,
        "success": (
            reward is not None
            and reward > 0
        ),
        "reward": reward,
        "duration_ms": int(
            round(
                (
                    time.monotonic()
                    - started
                )
                * 1000
            )
        ),
        "harbor_return_code": return_code,
        "harbor_job_root": str(
            jobs_root
            / trial_id
        ),
        "reward_path": reward_path,
        "mcp_exposed": (
            selected_mcp
            is not None
        ),
        "stderr_tail": (
            stderr
            if status
            == "INCOMPLETE"
            else ""
        ),
    }


def _new_run_root(
    root: Path,
) -> Path:
    stem = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    candidate = (
        root
        / "runs"
        / stem
    )
    suffix = 1
    while candidate.exists():
        suffix += 1
        candidate = (
            root
            / "runs"
            / f"{stem}-{suffix}"
        )
    candidate.mkdir(
        parents=True,
    )
    return candidate


def _latest_run(
    root: Path,
) -> Path:
    runs = (
        root
        / "runs"
    )
    candidates = (
        sorted(
            path
            for path in runs.iterdir()
            if path.is_dir()
        )
        if runs.is_dir()
        else []
    )
    if not candidates:
        raise HarborMatrixError(
            f"no Harbor runs under {runs}"
        )
    return candidates[-1]


def _rate(
    rows: list[Mapping[str, Any]],
) -> float | None:
    completed = [
        row
        for row in rows
        if row.get("status")
        == "COMPLETE"
    ]
    return (
        sum(
            bool(
                row.get("success")
            )
            for row in completed
        )
        / len(completed)
        if completed
        else None
    )


def build_report(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    groups: dict[
        tuple[str, str],
        list[dict[str, Any]],
    ] = defaultdict(list)
    for row in rows:
        groups[
            (
                str(row["harness"]),
                str(row["subject"]),
            )
        ].append(row)
    harnesses = sorted(
        {
            harness
            for harness, _subject
            in groups
        }
    )
    summaries = []
    for harness in harnesses:
        for subject in (
            "none",
            "hashmarks",
        ):
            selected = groups.get(
                (
                    harness,
                    subject,
                ),
                [],
            )
            summaries.append(
                {
                    "harness": harness,
                    "subject": subject,
                    "trials": len(
                        selected
                    ),
                    "complete": sum(
                        row.get("status")
                        == "COMPLETE"
                        for row in selected
                    ),
                    "successes": sum(
                        bool(
                            row.get(
                                "success"
                            )
                        )
                        for row in selected
                        if row.get(
                            "status"
                        )
                        == "COMPLETE"
                    ),
                    "success_rate": _rate(
                        selected
                    ),
                }
            )
    uplift = {}
    for harness in harnesses:
        bare = _rate(
            groups.get(
                (
                    harness,
                    "none",
                ),
                [],
            )
        )
        treated = _rate(
            groups.get(
                (
                    harness,
                    "hashmarks",
                ),
                [],
            )
        )
        uplift[harness] = (
            None
            if (
                bare is None
                or treated is None
            )
            else treated - bare
        )

    def spread(
        subject: str,
    ) -> float | None:
        values = [
            rate
            for harness in harnesses
            if (
                rate := _rate(
                    groups.get(
                        (
                            harness,
                            subject,
                        ),
                        [],
                    )
                )
            )
            is not None
        ]
        return (
            max(values)
            - min(values)
            if len(values) >= 2
            else None
        )

    bare_spread = spread(
        "none"
    )
    treated_spread = spread(
        "hashmarks"
    )
    reduction = (
        None
        if (
            bare_spread is None
            or treated_spread is None
        )
        else bare_spread
        - treated_spread
    )
    return {
        "schema": REPORT_SCHEMA,
        "trials": len(rows),
        "complete": sum(
            row.get("status")
            == "COMPLETE"
            for row in rows
        ),
        "incomplete": sum(
            row.get("status")
            != "COMPLETE"
            for row in rows
        ),
        "groups": summaries,
        "hashmarks_uplift": uplift,
        "harness_spread": {
            "bare": bare_spread,
            "hashmarks": treated_spread,
            "reduction": reduction,
            "reduction_fraction": (
                None
                if (
                    reduction is None
                    or bare_spread
                    in (
                        None,
                        0,
                    )
                )
                else reduction
                / bare_spread
            ),
        },
    }


def _load_rows(
    run_root: Path,
) -> list[dict[str, Any]]:
    directory = (
        run_root
        / "trials"
    )
    paths = (
        sorted(
            directory.glob(
                "*.json"
            )
        )
        if directory.is_dir()
        else []
    )
    rows = [
        json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
        for path in paths
    ]
    if (
        not rows
        or any(
            not isinstance(
                row,
                dict,
            )
            or row.get(
                "schema"
            )
            != RESULT_SCHEMA
            for row in rows
        )
    ):
        raise HarborMatrixError(
            "no valid Harbor trial receipts under "
            f"{directory}"
        )
    return rows


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=(
            "python -m "
            "benchmarks.harbor_matrix"
        )
    )
    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )
    for name in (
        "check",
        "run",
        "report",
    ):
        command = sub.add_parser(
            name
        )
        command.add_argument(
            "--env-file",
            type=Path,
            default=Path(".env"),
        )
        command.add_argument(
            "--matrix",
            type=Path,
            default=Path(
                "benchmarks/harbor/"
                "repository-intelligence-v1.json"
            ),
        )
        command.add_argument(
            "--mode",
            default="smoke",
        )
        command.add_argument(
            "--harness",
            action="append",
            default=[],
        )
        command.add_argument(
            "--task",
            action="append",
            default=[],
        )
        if name == "report":
            command.add_argument(
                "--run",
                type=Path,
            )
    return parser


def _selection(
    args: argparse.Namespace,
) -> tuple[
    HarborSettings,
    dict[str, Any],
    SuiteDefinition,
    MatrixMode,
    tuple[str, ...],
    tuple[str, ...],
]:
    settings = load_settings(
        args.env_file
    )
    matrix = load_matrix(
        args.matrix
    )
    suite = load_suite(
        Path(
            str(
                matrix["suite"]
            )
        )
    )
    mode = mode_contract(
        matrix,
        args.mode,
    )
    harnesses = _select(
        matrix["harnesses"],
        args.harness,
        label="harness",
    )
    tasks = _select(
        mode.tasks,
        args.task,
        label="task",
    )
    validate_projection(
        matrix=matrix,
        suite=suite,
        mode=mode,
        harnesses=harnesses,
        tasks=tasks,
    )
    return (
        settings,
        matrix,
        suite,
        mode,
        harnesses,
        tasks,
    )


def main(
    argv: list[str] | None = None,
) -> int:
    args = _parser().parse_args(
        argv
    )
    try:
        (
            settings,
            matrix,
            suite,
            mode,
            harnesses,
            tasks,
        ) = _selection(
            args
        )
        if args.command == "check":
            print(
                json.dumps(
                    preflight(
                        settings=settings,
                        matrix=matrix,
                        suite=suite,
                        mode=mode,
                        harnesses=harnesses,
                        tasks=tasks,
                    ),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "report":
            run_root = (
                args.run
                or _latest_run(
                    settings.root
                )
            )
            report = {
                **build_report(
                    _load_rows(
                        run_root
                    )
                ),
                "run_root": str(
                    run_root
                ),
            }
            (
                run_root
                / "report.json"
            ).write_text(
                json.dumps(
                    report,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            print(
                json.dumps(
                    report,
                    indent=2,
                    sort_keys=True,
                )
            )
            return (
                0
                if report[
                    "incomplete"
                ]
                == 0
                else 2
            )

        preflight_receipt = preflight(
            settings=settings,
            matrix=matrix,
            suite=suite,
            mode=mode,
            harnesses=harnesses,
            tasks=tasks,
        )
        run_root = _new_run_root(
            settings.root
        )
        (
            run_root
            / "preflight.json"
        ).write_text(
            json.dumps(
                preflight_receipt,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        task_root = (
            run_root
            / "tasks"
        )
        cache_root = (
            settings.root
            / "cache"
        )
        for task_id in tasks:
            prepare_task(
                suite=suite,
                task_id=task_id,
                destination=(
                    task_root
                    / task_id
                ),
                cache_root=cache_root,
                hashmarks_source=(
                    settings.hashmarks_source
                ),
            )
        mcp_config = write_mcp_config(
            run_root
            / "hashmarks.mcp.json"
        )
        credential_file = _credential_file(
            run_root,
            keys=(
                settings.passthrough_env_keys
            ),
            host=os.environ,
        )
        rows = plan_rows(
            harnesses=harnesses,
            tasks=tasks,
            attempts=mode.attempts,
        )
        trials_dir = (
            run_root
            / "trials"
        )
        trials_dir.mkdir()
        results = []
        for index, row in enumerate(
            rows,
            1,
        ):
            print(
                "HARBOR "
                f"{index}/{len(rows)} | "
                f"{row['task']} | "
                f"{row['harness']} | "
                f"{row['subject']} | "
                f"attempt {row['attempt']}",
                file=sys.stderr,
                flush=True,
            )
            result = execute_trial(
                settings=settings,
                row=row,
                task_path=(
                    task_root
                    / str(
                        row["task"]
                    )
                ),
                run_root=run_root,
                credential_file=(
                    credential_file
                ),
                mcp_config=mcp_config,
                host=os.environ,
            )
            results.append(
                result
            )
            (
                trials_dir
                / (
                    f"{result['trial_id']}"
                    ".json"
                )
            ).write_text(
                json.dumps(
                    result,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        report = {
            **build_report(
                results
            ),
            "run_root": str(
                run_root
            ),
        }
        (
            run_root
            / "report.json"
        ).write_text(
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
            )
        )
        return (
            0
            if report[
                "incomplete"
            ]
            == 0
            else 2
        )
    except (
        HarborMatrixError,
        ValueError,
        OSError,
    ) as exc:
        raise SystemExit(
            "Harbor harness benchmark unavailable: "
            f"{exc}"
        ) from exc


if __name__ == "__main__":
    raise SystemExit(main())
