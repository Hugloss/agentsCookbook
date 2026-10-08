"""Harbor trial execution under the shared benchmark campaign authority."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
from pathlib import Path
from typing import Any, Mapping

from benchmarks.config import BenchmarkConfig
from benchmarks.harbor_matrix import (
    HarborSettings,
    build_report as build_harbor_report,
    execute_trial,
    mode_contract,
    preflight,
    prepare_task,
    write_mcp_config,
    _credential_file,
)
from benchmarks.matrix_profiles import MatrixProfile

from .bundle import verify_bundle
from .bundle_writer import BundlePublicationError, publish_bundle
from .campaign import campaign_status
from .campaign_authority import (
    campaign_suite_identity,
    claim_launch,
    launch_state,
    publish_campaign_authority,
    record_interrupted_attempt,
)
from .identity import canonical_json, digest
from .mechanism_attribution import build_mechanism_report
from .runner import TrialRunResult, reuse_completed_trial
from .suite import SuiteDefinition


class HarborBackendError(ValueError):
    pass


def settings_from_config(
    config: BenchmarkConfig,
    profile: MatrixProfile,
) -> HarborSettings:
    source = config.values.get("HASHMARKS_BENCH_SOURCE")
    model = config.values.get("BENCHMARK_HARBOR_MODEL")
    issues = [
        f"set {name} in the selected benchmark env file"
        for name, value in (
            ("HASHMARKS_BENCH_SOURCE", source),
            ("BENCHMARK_HARBOR_MODEL", model),
        )
        if not value
    ]
    executable = config.values.get("BENCHMARK_HARBOR_EXECUTABLE") or "harbor"
    if shutil.which(executable, path=config.host.get("PATH")) is None:
        issues.append(f"install Harbor CLI or set BENCHMARK_HARBOR_EXECUTABLE ({executable} unavailable)")
    if shutil.which("docker", path=config.host.get("PATH")) is None:
        issues.append("install Docker CLI and start its daemon")
    raw_keys = config.values.get("BENCHMARK_PASSTHROUGH_ENV_KEYS", "")
    keys = tuple(dict.fromkeys(key.strip() for key in raw_keys.split(",") if key.strip()))
    invalid = sorted(key for key in keys if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) is None)
    if invalid:
        issues.append("invalid BENCHMARK_PASSTHROUGH_ENV_KEYS: " + ", ".join(invalid))
    absent = sorted(key for key in keys if not config.host.get(key))
    if absent:
        issues.append("set selected provider variable(s) in the host environment: " + ", ".join(absent))
    if config.values.get("BENCHMARK_HARBOR_PASSTHROUGH_ENV_KEYS"):
        issues.append("replace BENCHMARK_HARBOR_PASSTHROUGH_ENV_KEYS with BENCHMARK_PASSTHROUGH_ENV_KEYS")
    if issues:
        raise HarborBackendError("Harbor setup needs:\n- " + "\n- ".join(issues))
    if profile.root is None:
        raise HarborBackendError("Harbor matrix has no run root")
    return HarborSettings(
        executable=executable,
        model=str(model),
        root=profile.root,
        hashmarks_source=Path(str(source)).expanduser().resolve(),
        passthrough_env_keys=keys,
    )


def _tree_identity(root: Path) -> str:
    if root.is_symlink() or not root.is_dir():
        raise HarborBackendError(f"projected Harbor task is missing or invalid: {root}")
    entries = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            entries.append((relative, "symlink", os.readlink(path)))
        elif path.is_file():
            entries.append((relative, "file", hashlib.sha256(path.read_bytes()).hexdigest()))
        elif path.is_dir():
            entries.append((relative, "directory", None))
        else:
            raise HarborBackendError(f"unsupported projected task entry: {path}")
    return digest(entries)


def observed_preflight(
    *,
    settings: HarborSettings,
    suite: SuiteDefinition,
    projection: Mapping[str, Any],
    profile: MatrixProfile,
    host: Mapping[str, str],
) -> dict[str, Any]:
    mode = mode_contract(projection, str(profile.mode))
    return preflight(
        settings=settings,
        matrix=projection,
        suite=suite,
        mode=mode,
        harnesses=tuple(str(value) for value in projection["harnesses"]),
        tasks=mode.tasks,
        host=host,
    )


def admit_harbor_run(
    staged: Path,
    *,
    suite: SuiteDefinition,
    profile: MatrixProfile,
    settings: HarborSettings,
    preflight_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    rows = suite.trial_definitions()
    if not rows or len({row["definition_id"] for row in rows}) != len(rows):
        raise HarborBackendError("Harbor matrix has empty or duplicate trial definitions")
    tasks_root = staged / "tasks"
    task_digests = {}
    for task_id in suite.experiment["tasks"]:
        task_path = tasks_root / str(task_id)
        prepare_task(
            suite=suite,
            task_id=str(task_id),
            destination=task_path,
            cache_root=staged / "cache",
            hashmarks_source=settings.hashmarks_source,
        )
        task_digests[str(task_id)] = _tree_identity(task_path)
    payload = {
        "contract": "benchmark-campaign-authority.v6",
        "backend": "harbor",
        "matrix_profile": profile.name,
        "matrix_profile_identity": profile.identity,
        "suite_identity": campaign_suite_identity(suite),
        "selected_definitions": sorted(str(row["definition_id"]) for row in rows),
        "preflight": dict(preflight_receipt),
        "task_digests": task_digests,
    }
    return publish_campaign_authority(staged / "results", payload)


def verify_harbor_run(
    run_root: Path,
    campaign: Mapping[str, Any],
    *,
    suite: SuiteDefinition,
    profile: MatrixProfile,
    preflight_receipt: Mapping[str, Any],
) -> None:
    if (
        campaign.get("backend") != "harbor"
        or campaign.get("matrix_profile") != profile.name
        or campaign.get("matrix_profile_identity") != profile.identity
        or campaign.get("suite_identity") != campaign_suite_identity(suite)
        or campaign.get("selected_definitions")
        != sorted(str(row["definition_id"]) for row in suite.trial_definitions())
        or campaign.get("preflight") != dict(preflight_receipt)
    ):
        raise HarborBackendError("saved Harbor run authority changed; start a new run")
    expected = campaign.get("task_digests")
    if not isinstance(expected, dict):
        raise HarborBackendError("saved Harbor task authority is missing")
    for task_id in suite.experiment["tasks"]:
        if expected.get(task_id) != _tree_identity(run_root / "tasks" / str(task_id)):
            raise HarborBackendError(f"projected Harbor task changed: {task_id}")


def credential_file(
    run_root: Path,
    *,
    settings: HarborSettings,
    host: Mapping[str, str],
) -> Path | None:
    return _credential_file(run_root, keys=settings.passthrough_env_keys, host=host)


def mcp_config(run_root: Path) -> Path:
    return write_mcp_config(run_root / "hashmarks.mcp.json")


def _redact(value: str, settings: HarborSettings, host: Mapping[str, str]) -> str:
    for secret in sorted((host[key] for key in settings.passthrough_env_keys), key=len, reverse=True):
        value = value.replace(secret, "[REDACTED]")
    return value


def _captured_job_artifact(
    observed: Mapping[str, Any],
    *,
    key: str,
    job_root: Path,
    label: str,
) -> bytes | None:
    value = observed.get(key)
    if value is None:
        return None
    path = Path(str(value))
    if path.is_symlink() or not path.is_file():
        raise HarborBackendError(f"Harbor {label} path is missing or invalid")
    try:
        path.resolve().relative_to(job_root)
    except ValueError as exc:
        raise HarborBackendError(
            f"Harbor {label} escaped its job directory"
        ) from exc
    return path.read_bytes()


def run_harbor_trial(
    *,
    suite: SuiteDefinition,
    row: Mapping[str, Any],
    run_root: Path,
    campaign: dict[str, Any],
    settings: HarborSettings,
    host: Mapping[str, str],
    credentials: Path | None,
    mcp: Path,
) -> TrialRunResult:
    definition = str(row["definition_id"])
    trial_id = digest({"campaign_id": campaign["campaign_id"], "definition_id": definition})
    results_root = run_root / "results"
    state = launch_state(
        results_root=results_root,
        campaign=campaign,
        definition_id=definition,
        trial_id=trial_id,
    )
    recovered = False
    if state in {"INTERRUPTED", "STALE_INTERRUPTED"}:
        record_interrupted_attempt(
            results_root=results_root,
            campaign=campaign,
            definition_id=definition,
            trial_id=None if state == "STALE_INTERRUPTED" else trial_id,
        )
        recovered = True
    elif state == "CORRUPT":
        raise HarborBackendError(f"Harbor result bundle is corrupt: {results_root / trial_id}")
    elif state == "COMPLETE":
        return reuse_completed_trial(
            results_root=results_root,
            definition_id=definition,
            trial_id=trial_id,
        )
    task_id = str(row["task_id"])
    if campaign["task_digests"].get(task_id) != _tree_identity(run_root / "tasks" / task_id):
        raise HarborBackendError(f"projected Harbor task changed: {task_id}")
    launch_attempt = claim_launch(
        results_root=results_root,
        campaign=campaign,
        definition_id=definition,
        trial_id=trial_id,
    )
    condition = next(
        value for value in suite.experiment["conditions"]
        if value["id"] == row["condition_id"]
    )
    job_name = f"h{trial_id[:24]}-a{launch_attempt:06d}"
    jobs_root = run_root / "jobs"
    if jobs_root.is_symlink() or (jobs_root / job_name).is_symlink():
        raise HarborBackendError("Harbor job directory must not be a symlink")
    observed = execute_trial(
        settings=settings,
        row={
            "task": task_id,
            "harness": condition["agent"],
            "subject": condition["subject"],
            "attempt": int(row["trial"]) + 1,
        },
        task_path=run_root / "tasks" / task_id,
        run_root=run_root,
        credential_file=credentials,
        mcp_config=mcp,
        host=host,
        job_name=job_name,
    )
    observed["stderr_tail"] = _redact(str(observed.get("stderr_tail") or ""), settings, host)
    reward_bytes = None
    trajectory_bytes = None
    answer_bytes = None
    if observed["status"] == "COMPLETE":
        if jobs_root.is_symlink() or (jobs_root / job_name).is_symlink():
            raise HarborBackendError("Harbor job directory must not be a symlink")
        job_root = (jobs_root / job_name).resolve()
        reward_bytes = _captured_job_artifact(
            observed,
            key="reward_path",
            job_root=job_root,
            label="reward",
        )
        if reward_bytes is None:
            raise HarborBackendError("Harbor reward path is missing")
        trajectory_bytes = _captured_job_artifact(
            observed,
            key="trajectory_path",
            job_root=job_root,
            label="ATIF trajectory",
        )
        answer_bytes = _captured_job_artifact(
            observed,
            key="answer_evidence_path",
            job_root=job_root,
            label="answer evidence",
        )
    status = (
        "PASS" if observed["reward"] > 0 else "FAIL"
    ) if observed["status"] == "COMPLETE" else "INCOMPLETE"
    receipt: dict[str, Any] = {
        "backend": "harbor",
        "definition_id": definition,
        "trial_id": trial_id,
        "task_id": task_id,
        "condition_id": str(row["condition_id"]),
        "trial": int(row["trial"]),
        "replicate_id": int(row["replicate_id"]),
        "harness": condition["agent"],
        "subject": condition["subject"],
        "model": settings.model,
        "status": status,
        "reason": (
            observed["stderr_tail"] or "Harbor did not produce a valid completed reward"
            if status == "INCOMPLETE"
            else None
        ),
        "diagnostic": {
            "stage": "harbor-execution" if status == "INCOMPLETE" else None,
            "reason_code": "harbor-operational-failure" if status == "INCOMPLETE" else None,
            "detail": observed["stderr_tail"] or None if status == "INCOMPLETE" else None,
        },
        "harbor": observed,
        "execution": {
            "campaign_id": campaign["campaign_id"],
            "launch_attempt": launch_attempt,
            "job_name": job_name,
        },
    }
    artifacts = {"harbor_result": ("harbor-result.json", canonical_json(observed))}
    if reward_bytes is not None:
        artifacts["reward"] = ("reward" + Path(str(observed["reward_path"])).suffix, reward_bytes)
    if trajectory_bytes is not None:
        artifacts["trajectory"] = ("trajectory.json", trajectory_bytes)
    if answer_bytes is not None:
        artifacts["answer"] = ("answer.json", answer_bytes)
    try:
        result_dir = publish_bundle(
            results_root=results_root,
            trial_id=trial_id,
            artifacts=artifacts,
            receipt=receipt,
        )
    except BundlePublicationError as exc:
        raise HarborBackendError(str(exc)) from exc
    valid, reason = verify_bundle(result_dir)
    if not valid:
        raise HarborBackendError(f"published Harbor receipt is invalid: {reason}")
    return TrialRunResult(
        trial_id=trial_id,
        definition_id=definition,
        status=status,
        result_dir=result_dir,
        reused=False,
        recovered=recovered,
        reason=observed["stderr_tail"] or None if status == "INCOMPLETE" else None,
        stage="harbor-execution" if status == "INCOMPLETE" else None,
        reason_code="harbor-operational-failure" if status == "INCOMPLETE" else None,
    )


def harbor_report(
    *,
    suite: SuiteDefinition,
    results_root: Path,
    selected_definitions: set[str],
) -> dict[str, Any]:
    status = campaign_status(
        suite=suite,
        results_root=results_root,
        selected_definitions=selected_definitions,
    )
    conditions = {value["id"]: value for value in suite.experiment["conditions"]}
    rows = []
    for item in status["rows"]:
        condition = conditions[str(item["condition_id"])]
        outcome = item["outcome"]
        rows.append({
            "task": item["task_id"],
            "harness": condition["agent"],
            "subject": condition["subject"],
            "attempt": int(item["trial"]) + 1,
            "status": "COMPLETE" if outcome in {"PASS", "FAIL"} else "INCOMPLETE",
            "success": outcome == "PASS",
        })
    report = build_harbor_report(rows)
    report.update({
        "backend": "harbor",
        "expected_trials": status["expected_trials"],
        "completed_receipts": status["complete_trials"],
        "pending_trials": status["pending_trials"],
        "interrupted_trials": status["interrupted_trials"],
        "qualified": status["qualified"],
        "mechanism_attribution": build_mechanism_report(results_root),
    })
    if not status["qualified"]:
        report["hashmarks_uplift"] = {
            harness: None for harness in report["hashmarks_uplift"]
        }
        report["harness_spread"] = {
            key: None for key in report["harness_spread"]
        }
    return report
