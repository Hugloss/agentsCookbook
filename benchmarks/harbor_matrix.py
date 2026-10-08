"""Harbor-backed cross-harness benchmark projection.

agentsCookbook owns experiment semantics; Harbor is execution infrastructure.
Only read-only repository-location tasks are projected by this v1 bridge.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from benchmarks.adapters.hashmarks import HashmarksSubject
from benchmarks.adapters.runtime import observe_executable
from benchmarks.harness.model import TrialContext
from benchmarks.harness.source import materialize_repository
from benchmarks.harness.suite import SuiteDefinition, load_suite

MATRIX_SCHEMA = "agentscookbook.harbor-harness-matrix.v1"
RESULT_SCHEMA = "agentscookbook.harbor-harness-trial.v1"
REPORT_SCHEMA = "agentscookbook.harbor-harness-report.v1"


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


def _hashmarks_identity(
    settings: HarborSettings,
    host: Mapping[str, str],
) -> dict[str, Any]:
    """Reuse the canonical subject adapter to bind source and executable identity."""
    with tempfile.TemporaryDirectory(
        prefix="agentscookbook-harbor-hashmarks-"
    ) as tmp:
        control_root = Path(tmp).resolve()
        environment = dict(host)
        environment["HASHMARKS_BENCH_SOURCE"] = str(
            settings.hashmarks_source
        )
        context = TrialContext(
            workspace=settings.hashmarks_source,
            control_root=control_root,
            environment=environment,
        )
        subject = HashmarksSubject()
        source_identity, error = subject.source_identity(context)
        if error or not source_identity:
            raise HarborMatrixError(
                error or "cannot establish Hashmarks source identity"
            )
        exposure = subject.mcp_exposure(context)
        observed = observe_executable(
            context,
            exposure.command,
            version_args=("version",),
            environment=environment,
        )
        if observed.payload.get("available") is not True:
            reason = observed.payload.get("reason")
            stderr = observed.payload.get("stderr")
            detail = (
                str(reason)
                if reason
                else str(stderr).strip()
                if stderr
                else "executable identity probe failed"
            )
            raise HarborMatrixError(
                f"Hashmarks executable identity unavailable: {detail}"
            )
        resolved_path = observed.payload.get("resolved_path")
        executable_sha256 = observed.payload.get("executable_sha256")
        version = observed.payload.get("version")
        if not (
            isinstance(resolved_path, str)
            and resolved_path
            and isinstance(executable_sha256, str)
            and executable_sha256
            and isinstance(version, str)
            and version
        ):
            raise HarborMatrixError(
                "Hashmarks executable identity probe was incomplete"
            )
        return {
            **source_identity,
            "executable": {
                "path": resolved_path,
                "sha256": executable_sha256,
                "version": version,
            },
        }


def _hashmarks_probe(
    settings: HarborSettings,
    host: Mapping[str, str],
    *,
    executable: str,
) -> dict[str, Any]:
    result = _run(
        [
            executable,
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
    harbor_version = _require_command(
        [settings.executable, "--version"],
        label="Harbor",
    )
    docker_version = _require_command(
        ["docker", "version", "--format", "{{.Server.Version}}"],
        label="Docker",
    )
    hashmarks_identity = _hashmarks_identity(
        settings,
        host,
    )
    executable = hashmarks_identity.get("executable")
    if not isinstance(executable, dict):
        raise HarborMatrixError(
            "Hashmarks executable identity is missing"
        )
    executable_path = executable.get("path")
    if not isinstance(executable_path, str) or not executable_path:
        raise HarborMatrixError(
            "Hashmarks executable path is missing"
        )
    mcp = _hashmarks_probe(
        settings,
        host,
        executable=executable_path,
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
            **hashmarks_identity,
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
        'schema_version = "1.4"\n\n'
        "[task]\n"
        f'name = "agentscookbook/{task["id"]}"\n'
        'version = "1.0.0"\n'
        'description = "Read-only repository localization projection"\n\n'
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
clean=0
if git -C /workspace diff --quiet -- . && git -C /workspace diff --cached --quiet -- .; then
  clean=1
fi
export clean
python3 - <<'PY'
import json
import os
from pathlib import Path

expected = {expected_json}
source = Path("/workspace/.agentscookbook-answer.json")
observed = None
error = None
try:
    if source.is_file():
        value = json.loads(source.read_text(encoding="utf-8"))
        if isinstance(value, dict):
            observed = value
        else:
            error = "answer-not-object"
    else:
        error = "answer-missing"
except (OSError, json.JSONDecodeError):
    error = "answer-invalid-json"

tracked_clean = os.environ.get("clean") == "1"
match = observed == expected
evidence = {{
    "schema": "agentscookbook.harbor-answer-evidence.v1",
    "observed": observed,
    "expected": expected,
    "match": match,
    "tracked_clean": tracked_clean,
    "error": error,
}}
Path("/logs/verifier/answer.json").write_text(
    json.dumps(evidence, sort_keys=True) + "\\n",
    encoding="utf-8",
)
Path("/logs/verifier/reward.txt").write_text(
    "1\\n" if match and tracked_clean else "0\\n",
    encoding="utf-8",
)
PY
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
    fd, temporary = tempfile.mkstemp(prefix=".harbor-env-", dir=run_root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            for key in keys:
                value = (
                    host[key]
                    .replace("\\", "\\\\")
                    .replace("\n", "\\n")
                )
                stream.write(f"{key}={value}\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
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
            value = float(path.read_text(encoding="utf-8").strip())
            return value if math.isfinite(value) and 0 <= value <= 1 else None
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
        return float(value) if math.isfinite(value) and 0 <= value <= 1 else None
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
            return float(nested) if math.isfinite(nested) and 0 <= nested <= 1 else None
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


def _single_job_artifact(
    job_root: Path,
    *,
    name: str,
    parent: str,
) -> str | None:
    candidates = sorted(
        path
        for path in job_root.rglob(name)
        if path.is_file() and not path.is_symlink()
    )
    preferred = [
        path for path in candidates if path.parent.name == parent
    ]
    if len(preferred) == 1:
        return str(preferred[0])
    return str(candidates[0]) if len(candidates) == 1 else None


def execute_trial(
    *,
    settings: HarborSettings,
    row: Mapping[str, object],
    task_path: Path,
    run_root: Path,
    credential_file: Path | None,
    mcp_config: Path,
    host: Mapping[str, str],
    job_name: str,
) -> dict[str, Any]:
    trial_id = job_name
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
    job_root = jobs_root / trial_id
    reward, reward_path = find_reward(
        job_root
    )
    trajectory_path = _single_job_artifact(
        job_root,
        name="trajectory.json",
        parent="agent",
    )
    answer_evidence_path = _single_job_artifact(
        job_root,
        name="answer.json",
        parent="verifier",
    )
    status = (
        "COMPLETE"
        if reward is not None and return_code == 0
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
        "success": status == "COMPLETE" and reward > 0,
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
        "trajectory_path": trajectory_path,
        "answer_evidence_path": answer_evidence_path,
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
