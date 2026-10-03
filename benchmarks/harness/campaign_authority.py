"""Immutable campaign admission with crash-safe, explicit launch-attempt lineage."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping

from .admission import TrialAdmission, admit_trial, harness_identity
from .bundle import verify_bundle
from .identity import canonical_json, digest, execution_id
from .oracle_reviews import (
    oracle_review_path,
    oracle_reviews_declared,
    validate_oracle_reviews,
)
from .suite import SuiteDefinition


class CampaignAuthorityError(RuntimeError):
    pass


def _agent_common(admission: TrialAdmission) -> dict[str, Any]:
    observed = admission.agent_authority["observed"]
    return {
        "declared": admission.agent_authority["declared"],
        **{
            name: observed.get(name)
            for name in (
                "version",
                "executable_sha256",
                "auth_mode",
                "model",
                "provider",
                "reasoning_effort",
                "native_config_sha256",
                "native_mcp_servers",
            )
        },
    }


def condition_authority(admission: TrialAdmission) -> dict[str, Any]:
    """Project only observed authority stable across fresh trial workspaces."""
    observed = admission.subject_authority.get("observed")
    if isinstance(observed, dict) and "native_subject_identity" in observed:
        native = observed.get("native_subject_identity") or {}
        subject_observed = {
            "subject": observed.get("subject"),
            "native_subject_identity": native,
            "mcp_semantic_identity": (observed.get("mcp_exposure") or {}).get(
                "semantic_identity"
            ),
        }
    else:
        subject_observed = observed
    exposure = admission.subject.mcp_exposure(admission.context)
    source_identity = None
    if hasattr(admission.subject, "source_identity"):
        source_identity, source_error = admission.subject.source_identity(
            admission.context
        )
        if source_error:
            raise CampaignAuthorityError(str(source_error))
    return {
        "agent": _agent_common(admission),
        "subject": {
            "declared": admission.subject_authority["declared"],
            "observed": subject_observed,
            "source_identity": source_identity,
            "mcp_exposure": (
                {
                    "name": exposure.name,
                    "command": exposure.command,
                    "semantic_identity": exposure.semantic_identity,
                }
                if exposure is not None
                else None
            ),
        },
        "harness": admission.harness_authority,
        "environment": admission.environment_authority,
    }


def _global_agent_authority(value: dict[str, Any]) -> dict[str, Any]:
    agent = value["agent"]
    return {
        "declared": agent["declared"],
        **{
            key: agent.get(key)
            for key in (
                "version",
                "executable_sha256",
                "auth_mode",
                "model",
                "provider",
                "reasoning_effort",
            )
        },
    }


def _global_subject_authority(value: dict[str, Any]) -> dict[str, Any]:
    subject = value["subject"]
    observed = subject.get("observed") or {}
    native = (
        observed.get("native_subject_identity") if isinstance(observed, dict) else None
    )
    return {
        "declared": subject["declared"],
        "source_identity": subject.get("source_identity"),
        "native_executable_sha256": (
            native.get("executable_sha256") if isinstance(native, dict) else None
        ),
    }


@contextmanager
def _locked(directory: Path) -> Iterator[None]:
    directory.mkdir(parents=True, exist_ok=True)
    fd = os.open(directory / "lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _read_manifest(directory: Path) -> dict[str, Any]:
    path = directory / "authority.json"
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise CampaignAuthorityError(
            "campaign authority receipt is missing or corrupt"
        ) from exc
    if not isinstance(value, dict) or canonical_json(value) != raw:
        raise CampaignAuthorityError("campaign authority receipt is not canonical")
    if value.get("contract") not in {
        "benchmark-campaign-authority.v1",
        "benchmark-campaign-authority.v2",
        "benchmark-campaign-authority.v3",
    }:
        raise CampaignAuthorityError("unsupported campaign authority contract")
    identity = value.get("campaign_id")
    if identity != digest(
        {key: item for key, item in value.items() if key != "campaign_id"}
    ):
        raise CampaignAuthorityError("campaign authority receipt identity mismatch")
    return value


def read_campaign(results_root: Path) -> dict[str, Any]:
    return _read_manifest(results_root / ".campaign")


def _read_launch_claim(
    path: Path,
    *,
    campaign_id: str,
    definition_id: str,
) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        claim = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise CampaignAuthorityError(f"corrupt launch claim: {path}") from exc
    if (
        not isinstance(claim, dict)
        or canonical_json(claim) != raw
        or set(claim)
        != {"campaign_id", "definition_id", "trial_id", "attempt"}
        or claim.get("campaign_id") != campaign_id
        or claim.get("definition_id") != definition_id
        or not isinstance(claim.get("trial_id"), str)
        or len(claim["trial_id"]) != 64
        or any(char not in "0123456789abcdef" for char in claim["trial_id"])
        or type(claim.get("attempt")) is not int
        or claim["attempt"] < 1
    ):
        raise CampaignAuthorityError(f"launch claim identity mismatch: {path}")
    return claim


def _fsync_directory(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _publish_once(path: Path, payload: bytes, scratch: Path) -> None:
    """Publish complete bytes without ever exposing a partial or replaced record."""
    scratch.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".record-", dir=scratch)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        _fsync_directory(path.parent)
    finally:
        Path(temporary).unlink(missing_ok=True)


def active_event_path(results_root: Path, definition_id: str, attempt: int) -> Path:
    return (
        results_root
        / ".campaign"
        / "active-events"
        / definition_id
        / f"{attempt:06d}.jsonl"
    )


def start_attempt_events(
    results_root: Path, definition_id: str, attempt: int, initial: bytes
) -> Path:
    """Move pre-launch events to a durable attempt path before model execution."""
    path = active_event_path(results_root, definition_id, attempt)
    path.parent.mkdir(parents=True, exist_ok=True)
    _fsync_directory(path.parent.parent)
    _fsync_directory(path.parent)
    _publish_once(path, initial, results_root / ".campaign" / "scratch")
    return path


def retire_completed_events(results_root: Path, definition_id: str, attempt: int) -> None:
    """Remove duplicate active events after they are sealed in a verified receipt."""
    path = active_event_path(results_root, definition_id, attempt)
    path.unlink(missing_ok=True)
    path.with_name(path.name + ".seal.json").unlink(missing_ok=True)
    if path.parent.is_dir():
        _fsync_directory(path.parent)


def read_launch_details(results_root: Path, campaign_id: str) -> dict[str, dict[str, Any]]:
    """Read launch claims with their exact trial and attempt identity."""
    directory = results_root / ".campaign" / "claims"
    if not directory.exists():
        return {}
    if directory.is_symlink() or not directory.is_dir():
        raise CampaignAuthorityError("launch claim directory is invalid")
    found: dict[str, dict[str, Any]] = {}
    for path in directory.iterdir():
        if path.suffix != ".json" or path.is_symlink() or not path.is_file():
            raise CampaignAuthorityError(f"unexpected launch claim entry: {path}")
        definition = path.stem
        claim = _read_launch_claim(
            path,
            campaign_id=campaign_id,
            definition_id=definition,
        )
        found[definition] = claim
    return found


def read_launch_claims(results_root: Path, campaign_id: str) -> dict[str, str]:
    return {
        definition: claim["trial_id"]
        for definition, claim in read_launch_details(results_root, campaign_id).items()
    }


def read_interrupted_attempts(
    results_root: Path,
    campaign_id: str,
) -> dict[str, list[dict[str, Any]]]:
    """Read immutable interruption evidence grouped by definition."""
    root = results_root / ".campaign" / "attempts"
    if not root.exists():
        return {}
    if root.is_symlink() or not root.is_dir():
        raise CampaignAuthorityError("interruption attempt directory is invalid")
    found: dict[str, list[dict[str, Any]]] = {}
    for definition_dir in sorted(root.iterdir()):
        if definition_dir.is_symlink() or not definition_dir.is_dir():
            raise CampaignAuthorityError(
                f"unexpected interruption attempt entry: {definition_dir}"
            )
        definition = definition_dir.name
        attempts: list[dict[str, Any]] = []
        for expected_attempt, path in enumerate(
            sorted(definition_dir.iterdir()),
            start=1,
        ):
            if (
                path.name != f"{expected_attempt:06d}.json"
                or path.is_symlink()
                or not path.is_file()
            ):
                raise CampaignAuthorityError(
                    f"interruption attempt sequence is invalid: {path}"
                )
            try:
                raw = path.read_bytes()
                record = json.loads(raw)
            except (OSError, ValueError) as exc:
                raise CampaignAuthorityError(
                    f"corrupt interruption attempt: {path}"
                ) from exc
            old_fields = {
                "campaign_id", "definition_id", "trial_id", "attempt", "status"
            }
            new_fields = old_fields | {"contract", "events_sha256", "events_bytes"}
            if (
                not isinstance(record, dict)
                or canonical_json(record) != raw
                or set(record) not in (old_fields, new_fields)
                or record.get("campaign_id") != campaign_id
                or record.get("definition_id") != definition
                or record.get("attempt") != expected_attempt
                or record.get("status") != "INTERRUPTED"
                or not isinstance(record.get("trial_id"), str)
                or len(record["trial_id"]) != 64
                or any(
                    char not in "0123456789abcdef"
                    for char in record["trial_id"]
                )
            ):
                raise CampaignAuthorityError(
                    f"interruption attempt identity mismatch: {path}"
                )
            if set(record) == new_fields:
                if record["contract"] != "benchmark-interruption-attempt.v2":
                    raise CampaignAuthorityError(f"unsupported interruption attempt: {path}")
                evidence_path = (
                    results_root / ".campaign" / "interrupted-events"
                    / definition / f"{expected_attempt:06d}.jsonl"
                )
                if record["events_sha256"] is None:
                    if record["events_bytes"] is not None or evidence_path.exists():
                        raise CampaignAuthorityError(f"invalid interruption events: {path}")
                else:
                    if evidence_path.is_symlink() or not evidence_path.is_file():
                        raise CampaignAuthorityError(
                            f"invalid interruption events: {evidence_path}"
                        )
                    try:
                        evidence = evidence_path.read_bytes()
                    except OSError as exc:
                        raise CampaignAuthorityError(
                            f"missing interruption events: {evidence_path}"
                        ) from exc
                    if (
                        hashlib.sha256(evidence).hexdigest() != record["events_sha256"]
                        or len(evidence) != record["events_bytes"]
                    ):
                        raise CampaignAuthorityError(
                            f"interruption events changed: {evidence_path}"
                        )
            attempts.append(record)
        found[definition] = attempts
    return found

def _write_manifest(directory: Path, value: dict[str, Any]) -> None:
    raw = canonical_json(value)
    fd, temporary = tempfile.mkstemp(prefix=".authority-", dir=directory)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if (directory / "authority.json").exists():
            raise CampaignAuthorityError("campaign authority already exists")
        os.replace(temporary, directory / "authority.json")
        parent_fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    finally:
        Path(temporary).unlink(missing_ok=True)


def audit_campaign(
    *,
    suite: SuiteDefinition,
    rows: list[dict[str, Any]],
    results_root: Path | None = None,
    harness_root: Path,
    cache_root: Path,
    work_root: Path,
    local_source: Path | None = None,
    codex_auth: Path | None = None,
    source: Mapping[str, str] | None = None,
    on_progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Observe every selected condition without inference or publishing authority.

    This is diagnostic only. It does not qualify oracle reviews or authorize run.
    """
    if not rows:
        raise CampaignAuthorityError("campaign selection is empty")
    if results_root is not None:
        directory = results_root / ".campaign"
        if (
            not (directory / "authority.json").exists()
            and results_root.exists()
            and any(
                path.is_dir() and not path.name.startswith(".")
                for path in results_root.iterdir()
            )
        ):
            raise CampaignAuthorityError("existing results have no campaign authority")
    selected = sorted(str(row["definition_id"]) for row in rows)
    representatives: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        representatives.setdefault((str(row["task_id"]), str(row["condition_id"])), row)
    if len(selected) != len(set(selected)):
        raise CampaignAuthorityError(
            "campaign selection contains duplicate definitions"
        )
    observed: dict[str, dict[str, Any]] = {}
    agents: dict[str, dict[str, Any]] = {}
    subjects: dict[str, dict[str, Any]] = {}
    task_inputs: dict[str, str] = {}

    harness_started = time.monotonic()
    campaign_harness_authority = harness_identity(harness_root)
    harness_observe_ms = int(round((time.monotonic() - harness_started) * 1000))
    if on_progress is not None:
        on_progress(
            {
                "stage": "campaign-harness-authority",
                "status": "verified",
                "duration_ms": harness_observe_ms,
            }
        )

    ordered_representatives = sorted(representatives.items())
    for index, ((task_id, condition), row) in enumerate(
        ordered_representatives, start=1
    ):
        condition_started = time.monotonic()
        if on_progress is not None:
            on_progress(
                {
                    "stage": "condition-authority",
                    "index": index,
                    "total": len(ordered_representatives),
                    "task_id": task_id,
                    "condition_id": condition,
                }
            )
        with admit_trial(
            suite=suite,
            task_id=str(row["task_id"]),
            condition_id=condition,
            trial_index=int(row["trial"]),
            harness_root=harness_root,
            cache_root=cache_root,
            work_root=work_root,
            local_source=local_source,
            codex_auth=codex_auth,
            source=source,
            harness_authority=campaign_harness_authority,
        ) as admission:
            status, reason = admission.initial_outcome()
            if status is not None:
                raise CampaignAuthorityError(
                    f"{condition} cannot enter campaign: {reason}"
                )
            authority = condition_authority(admission)
            task_authorities = observed.setdefault(task_id, {})
            if (
                condition in task_authorities
                and task_authorities[condition] != authority
            ):
                raise CampaignAuthorityError(
                    f"{task_id}/{condition} authority changed during admission"
                )
            task_authorities[condition] = authority
            agent_id = str(admission.condition["agent"])
            global_agent = _global_agent_authority(authority)
            if agent_id in agents and agents[agent_id] != global_agent:
                raise CampaignAuthorityError(
                    f"{agent_id} runtime or model differs across selected tasks"
                )
            agents[agent_id] = global_agent
            subject_id = str(admission.condition["subject"])
            global_subject = _global_subject_authority(authority)
            if subject_id in subjects:
                prior_subject = subjects[subject_id]
                if any(
                    prior_subject[key] != global_subject[key]
                    for key in ("declared", "source_identity")
                ) or (
                    prior_subject["native_executable_sha256"] is not None
                    and global_subject["native_executable_sha256"] is not None
                    and prior_subject["native_executable_sha256"]
                    != global_subject["native_executable_sha256"]
                ):
                    raise CampaignAuthorityError(
                        f"{subject_id} executable or source differs across selected tasks"
                    )
                if prior_subject["native_executable_sha256"] is None:
                    prior_subject["native_executable_sha256"] = global_subject[
                        "native_executable_sha256"
                    ]
            else:
                subjects[subject_id] = global_subject
            inputs = digest(
                {
                    "workspace": admission.admitted_state,
                    "mutation": admission.mutation_authority,
                    "prompt": admission.task["prompt"],
                    "budgets": admission.task["budgets"],
                }
            )
            if task_id in task_inputs and task_inputs[task_id] != inputs:
                raise CampaignAuthorityError(
                    f"{task_id} has unequal non-subject inputs"
                )
            task_inputs[task_id] = inputs
            admission.cleanup_subject()
            if on_progress is not None:
                timings = dict(admission.admission_timings_ms)
                full_total = int(
                    round((time.monotonic() - condition_started) * 1000)
                )
                timings["condition_authority"] = max(
                    0,
                    full_total - int(timings.get("total", 0)),
                )
                timings["total"] = full_total
                on_progress(
                    {
                        "stage": "condition-authority-complete",
                        "index": index,
                        "total": len(ordered_representatives),
                        "task_id": task_id,
                        "condition_id": condition,
                        "timings_ms": timings,
                    }
                )

    harness_recheck_started = time.monotonic()
    if harness_identity(harness_root) != campaign_harness_authority:
        raise CampaignAuthorityError(
            "harness authority changed during campaign admission"
        )
    if on_progress is not None:
        on_progress(
            {
                "stage": "campaign-harness-authority",
                "status": "revalidated",
                "duration_ms": int(
                    round((time.monotonic() - harness_recheck_started) * 1000)
                ),
            }
        )

    payload = {
        "contract": "benchmark-campaign-authority.v3",
        "selected_definitions": selected,
        "task_conditions": observed,
        "agents": agents,
        "subjects": subjects,
        "task_inputs": task_inputs,
        "suite_identity": digest(
            {
                "experiment": suite.experiment,
                "tasks": {key: suite.tasks[key] for key in suite.experiment["tasks"]},
                "agents": suite.agents,
                "subjects": suite.subjects,
            }
        ),
        "oracle_review_sha256": (
            hashlib.sha256(review_path.read_bytes()).hexdigest()
            if (review_path := oracle_review_path(suite)).is_file()
            else None
        ),
    }
    payload["campaign_id"] = digest(payload)
    if on_progress is not None:
        on_progress(
            {
                "stage": "campaign-authority",
                "status": "verified",
                "total": len(ordered_representatives),
            }
        )
    if (
        results_root is not None
        and (results_root / ".campaign" / "authority.json").exists()
    ):
        if _read_manifest(results_root / ".campaign") != payload:
            raise CampaignAuthorityError(
                "campaign selection or execution authority changed; use a new root"
            )
    return payload


def admit_campaign(
    *,
    suite: SuiteDefinition,
    rows: list[dict[str, Any]],
    results_root: Path,
    harness_root: Path,
    cache_root: Path,
    work_root: Path,
    local_source: Path | None = None,
    codex_auth: Path | None = None,
    source: Mapping[str, str] | None = None,
    on_progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Check every selected condition without inference, then freeze its authority."""
    if oracle_reviews_declared(suite):
        if on_progress is not None:
            on_progress({"stage": "oracle-review", "status": "checking"})
        validate_oracle_reviews(suite, require_complete=True)
    directory = results_root / ".campaign"
    with _locked(directory):
        existing = (directory / "authority.json").exists()
        if (
            not existing
            and results_root.exists()
            and any(
                path.is_dir() and not path.name.startswith(".")
                for path in results_root.iterdir()
            )
        ):
            raise CampaignAuthorityError("existing results have no campaign authority")
        payload = audit_campaign(
            suite=suite,
            rows=rows,
            results_root=results_root,
            harness_root=harness_root,
            cache_root=cache_root,
            work_root=work_root,
            local_source=local_source,
            codex_auth=codex_auth,
            source=source,
            on_progress=on_progress,
        )
        if existing:
            if _read_manifest(directory) != payload:
                raise CampaignAuthorityError(
                    "campaign selection or execution authority changed; use a new root"
                )
        else:
            _write_manifest(directory, payload)
        if on_progress is not None:
            on_progress(
                {
                    "stage": "campaign-authority",
                    "status": "reused" if existing else "published",
                }
            )
        return payload


def campaign_trial_id(
    *,
    campaign: dict[str, Any],
    admission: TrialAdmission,
) -> str:
    """Derive durable trial identity only from frozen campaign authority."""
    expected = (
        campaign.get("task_conditions", {})
        .get(str(admission.task["id"]), {})
        .get(str(admission.condition["id"]))
    )
    if not isinstance(expected, dict):
        raise CampaignAuthorityError(
            "trial is outside frozen campaign condition authority"
        )
    return execution_id(
        definition=admission.definition_id,
        subject_identity=expected["subject"],
        agent_identity=expected["agent"],
        oracle_identity=admission.oracle_authority,
        harness_identity=expected["harness"],
        environment_identity=expected["environment"],
        mutation_identity=admission.mutation_authority,
    )


def verify_trial_authority(
    *,
    results_root: Path,
    campaign: dict[str, Any],
    admission: TrialAdmission,
) -> None:
    observed = _read_manifest(results_root / ".campaign")
    if observed != campaign:
        raise CampaignAuthorityError("campaign authority receipt changed")
    review_path = oracle_review_path(admission.suite)
    try:
        review_digest = (
            hashlib.sha256(review_path.read_bytes()).hexdigest()
            if review_path.is_file()
            else None
        )
    except OSError as exc:
        raise CampaignAuthorityError("oracle review evidence disappeared") from exc
    if review_digest != observed.get("oracle_review_sha256"):
        raise CampaignAuthorityError("oracle review authority changed before inference")
    if admission.definition_id not in observed["selected_definitions"]:
        raise CampaignAuthorityError("trial is outside frozen campaign selection")
    expected = (
        observed["task_conditions"]
        .get(str(admission.task["id"]), {})
        .get(str(admission.condition["id"]))
    )
    if expected != condition_authority(admission):
        raise CampaignAuthorityError(
            "observed trial authority drifted before inference"
        )
    inputs = digest(
        {
            "workspace": admission.admitted_state,
            "mutation": admission.mutation_authority,
            "prompt": admission.task["prompt"],
            "budgets": admission.task["budgets"],
        }
    )
    if observed["task_inputs"].get(str(admission.task["id"])) != inputs:
        raise CampaignAuthorityError("trial inputs differ from admitted campaign")


def claim_launch(
    *,
    results_root: Path,
    campaign: dict[str, Any],
    definition_id: str,
    trial_id: str,
) -> int:
    """Create the next durable launch attempt before invoking a model."""
    campaign_dir = results_root / ".campaign"
    with _locked(campaign_dir):
        if _read_manifest(campaign_dir) != campaign:
            raise CampaignAuthorityError("campaign authority receipt changed")
        directory = campaign_dir / "claims"
        directory.mkdir(parents=True, exist_ok=True)
        _fsync_directory(campaign_dir)
        path = directory / f"{definition_id}.json"
        if path.exists():
            raise CampaignAuthorityError(
                f"trial launch already claimed: {definition_id}"
            )
        attempts = read_interrupted_attempts(
            results_root,
            campaign["campaign_id"],
        ).get(definition_id, [])
        attempt = len(attempts) + 1
        payload = canonical_json(
            {
                "campaign_id": campaign["campaign_id"],
                "definition_id": definition_id,
                "trial_id": trial_id,
                "attempt": attempt,
            }
        )
        try:
            _publish_once(path, payload, campaign_dir / "scratch")
        except FileExistsError as exc:
            raise CampaignAuthorityError(f"trial launch already claimed: {definition_id}") from exc
        return attempt


def record_interrupted_attempt(
    *,
    results_root: Path,
    campaign: dict[str, Any],
    definition_id: str,
    trial_id: str,
) -> int:
    """Retire one crashed active launch into immutable interruption evidence."""
    campaign_dir = results_root / ".campaign"
    with _locked(campaign_dir):
        if _read_manifest(campaign_dir) != campaign:
            raise CampaignAuthorityError("campaign authority receipt changed")
        claim_path = campaign_dir / "claims" / f"{definition_id}.json"
        if not claim_path.is_file():
            raise CampaignAuthorityError(
                f"interrupted trial has no active launch claim: {definition_id}"
            )
        claim = _read_launch_claim(
            claim_path,
            campaign_id=campaign["campaign_id"],
            definition_id=definition_id,
        )
        if claim["trial_id"] != trial_id:
            raise CampaignAuthorityError("trial launch claim identity mismatch")
        final_dir = results_root / trial_id
        if final_dir.exists():
            raise CampaignAuthorityError(
                "existing trial bundle cannot be retired as interrupted"
            )

        attempt = int(claim["attempt"])
        directory = campaign_dir / "attempts" / definition_id
        directory.mkdir(parents=True, exist_ok=True)
        _fsync_directory(directory.parent)
        _fsync_directory(campaign_dir)
        path = directory / f"{attempt:06d}.json"
        active_path = active_event_path(results_root, definition_id, attempt)
        events_sha256: str | None = None
        events_bytes: int | None = None
        if active_path.exists():
            if active_path.is_symlink() or not active_path.is_file():
                raise CampaignAuthorityError(f"invalid active event stream: {active_path}")
            events = active_path.read_bytes()
            events_sha256 = hashlib.sha256(events).hexdigest()
            events_bytes = len(events)
            evidence_dir = campaign_dir / "interrupted-events" / definition_id
            evidence_dir.mkdir(parents=True, exist_ok=True)
            _fsync_directory(evidence_dir.parent)
            evidence_path = evidence_dir / f"{attempt:06d}.jsonl"
            if evidence_path.exists():
                if evidence_path.read_bytes() != events:
                    raise CampaignAuthorityError(
                        f"interruption events conflict with prior evidence: {evidence_path}"
                    )
            else:
                _publish_once(evidence_path, events, campaign_dir / "scratch")
        payload = canonical_json(
            {
                "contract": "benchmark-interruption-attempt.v2",
                "campaign_id": campaign["campaign_id"],
                "definition_id": definition_id,
                "trial_id": trial_id,
                "attempt": attempt,
                "status": "INTERRUPTED",
                "events_sha256": events_sha256,
                "events_bytes": events_bytes,
            }
        )
        if path.exists():
            if path.read_bytes() != payload:
                raise CampaignAuthorityError(
                    f"interruption attempt conflicts with prior evidence: {path}"
                )
        else:
            _publish_once(path, payload, campaign_dir / "scratch")

        claim_path.unlink()
        _fsync_directory(claim_path.parent)
        return attempt


def launch_state(
    *,
    results_root: Path,
    campaign: dict[str, Any],
    definition_id: str,
    trial_id: str,
) -> str:
    path = results_root / ".campaign" / "claims" / f"{definition_id}.json"
    if not path.exists():
        return "UNCLAIMED"
    claim = _read_launch_claim(
        path,
        campaign_id=campaign["campaign_id"],
        definition_id=definition_id,
    )
    if claim["trial_id"] != trial_id:
        raise CampaignAuthorityError("trial launch claim identity mismatch")
    final_dir = results_root / trial_id
    if final_dir.exists():
        valid, _reason = verify_bundle(final_dir)
        return "COMPLETE" if valid else "CORRUPT"
    return "INTERRUPTED"
