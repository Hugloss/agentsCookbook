"""Immutable campaign admission and one-launch-per-definition claims."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping

from .admission import TrialAdmission, admit_trial
from .bundle import verify_bundle
from .identity import canonical_json, digest
from .oracle_reviews import validate_oracle_reviews
from .suite import SuiteDefinition


class CampaignAuthorityError(RuntimeError):
    pass


def _agent_common(admission: TrialAdmission) -> dict[str, Any]:
    observed = admission.agent_authority["observed"]
    return {
        "declared": admission.agent_authority["declared"],
        **{name: observed.get(name) for name in (
            "version", "executable_sha256", "auth_mode", "model", "provider",
            "reasoning_effort", "native_config_sha256", "native_mcp_servers",
        )},
    }


def condition_authority(admission: TrialAdmission) -> dict[str, Any]:
    """Project only observed authority stable across fresh trial workspaces."""
    observed = admission.subject_authority.get("observed")
    if isinstance(observed, dict) and "native_subject_identity" in observed:
        native = observed.get("native_subject_identity") or {}
        subject_observed = {
            "subject": observed.get("subject"),
            "native_subject_identity": native,
            "mcp_semantic_identity": (
                observed.get("mcp_exposure") or {}
            ).get("semantic_identity"),
        }
    else:
        subject_observed = observed
    exposure = admission.subject.mcp_exposure(admission.context)
    source_identity = None
    if hasattr(admission.subject, "source_identity"):
        source_identity, source_error = admission.subject.source_identity(admission.context)
        if source_error:
            raise CampaignAuthorityError(str(source_error))
    return {
        "agent": _agent_common(admission),
        "subject": {
            "declared": admission.subject_authority["declared"],
            "observed": subject_observed,
            "source_identity": source_identity,
            "mcp_exposure": (
                {"name": exposure.name, "command": exposure.command,
                 "semantic_identity": exposure.semantic_identity}
                if exposure is not None else None
            ),
        },
        "harness": admission.harness_authority,
        "environment": admission.environment_authority,
    }


def _global_agent_authority(value: dict[str, Any]) -> dict[str, Any]:
    agent = value["agent"]
    return {
        "declared": agent["declared"],
        **{key: agent.get(key) for key in (
            "version", "executable_sha256", "auth_mode", "model", "provider",
            "reasoning_effort",
        )},
    }


def _global_subject_authority(value: dict[str, Any]) -> dict[str, Any]:
    subject = value["subject"]
    observed = subject.get("observed") or {}
    native = observed.get("native_subject_identity") if isinstance(observed, dict) else None
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
        raise CampaignAuthorityError("campaign authority receipt is missing or corrupt") from exc
    if not isinstance(value, dict) or canonical_json(value) != raw:
        raise CampaignAuthorityError("campaign authority receipt is not canonical")
    identity = value.get("campaign_id")
    if identity != digest({key: item for key, item in value.items() if key != "campaign_id"}):
        raise CampaignAuthorityError("campaign authority receipt identity mismatch")
    return value


def read_campaign(results_root: Path) -> dict[str, Any]:
    return _read_manifest(results_root / ".campaign")


def read_launch_claims(results_root: Path, campaign_id: str) -> dict[str, str]:
    """Read every durable launch claim and bind definition to exact trial ID."""
    directory = results_root / ".campaign" / "claims"
    if not directory.exists():
        return {}
    if directory.is_symlink() or not directory.is_dir():
        raise CampaignAuthorityError("launch claim directory is invalid")
    found: dict[str, str] = {}
    for path in directory.iterdir():
        if path.suffix != ".json" or path.is_symlink() or not path.is_file():
            raise CampaignAuthorityError(f"unexpected launch claim entry: {path}")
        try:
            raw = path.read_bytes()
            claim = json.loads(raw)
        except (OSError, ValueError) as exc:
            raise CampaignAuthorityError(f"corrupt launch claim: {path}") from exc
        definition = path.stem
        if (
            not isinstance(claim, dict)
            or canonical_json(claim) != raw
            or set(claim) != {"campaign_id", "definition_id", "trial_id"}
            or claim.get("campaign_id") != campaign_id
            or claim.get("definition_id") != definition
            or not isinstance(claim.get("trial_id"), str)
            or len(claim["trial_id"]) != 64
            or any(char not in "0123456789abcdef" for char in claim["trial_id"])
        ):
            raise CampaignAuthorityError(f"launch claim identity mismatch: {path}")
        found[definition] = claim["trial_id"]
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
    *, suite: SuiteDefinition, rows: list[dict[str, Any]],
    harness_root: Path, cache_root: Path, work_root: Path,
    local_source: Path | None = None, codex_auth: Path | None = None,
    source: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Observe every selected condition without inference or publishing authority.

    This is diagnostic only. It does not qualify oracle reviews or authorize run.
    """
    if not rows:
        raise CampaignAuthorityError("campaign selection is empty")
    selected = sorted(str(row["definition_id"]) for row in rows)
    representatives: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        representatives.setdefault((str(row["task_id"]), str(row["condition_id"])), row)
    if len(selected) != len(set(selected)):
        raise CampaignAuthorityError("campaign selection contains duplicate definitions")
    observed: dict[str, dict[str, Any]] = {}
    agents: dict[str, dict[str, Any]] = {}
    subjects: dict[str, dict[str, Any]] = {}
    task_inputs: dict[str, str] = {}
    for (task_id, condition), row in sorted(representatives.items()):
        with admit_trial(
            suite=suite, task_id=str(row["task_id"]),
            condition_id=condition, trial_index=int(row["trial"]),
            harness_root=harness_root, cache_root=cache_root,
            work_root=work_root, local_source=local_source,
            codex_auth=codex_auth, source=source,
        ) as admission:
            status, reason = admission.initial_outcome()
            if status is not None:
                raise CampaignAuthorityError(
                    f"{condition} cannot enter campaign: {reason}"
                )
            authority = condition_authority(admission)
            task_authorities = observed.setdefault(task_id, {})
            if condition in task_authorities and task_authorities[condition] != authority:
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
            inputs = digest({
                "workspace": admission.admitted_state,
                "mutation": admission.mutation_authority,
                "prompt": admission.task["prompt"],
                "budgets": admission.task["budgets"],
            })
            if task_id in task_inputs and task_inputs[task_id] != inputs:
                raise CampaignAuthorityError(
                    f"{task_id} has unequal non-subject inputs"
                )
            task_inputs[task_id] = inputs
            admission.cleanup_subject()
    payload = {
        "contract": "benchmark-campaign-authority.v2",
        "selected_definitions": selected,
        "task_conditions": observed,
        "agents": agents,
        "subjects": subjects,
        "task_inputs": task_inputs,
        "suite_identity": digest({
            "experiment": suite.experiment,
            "tasks": {key: suite.tasks[key] for key in suite.experiment["tasks"]},
            "agents": suite.agents, "subjects": suite.subjects,
        }),
        "oracle_review_sha256": (
            hashlib.sha256((suite.root / suite.experiment["oracle_reviews"]).read_bytes()).hexdigest()
            if "oracle_reviews" in suite.experiment else None
        ),
    }
    payload["campaign_id"] = digest(payload)
    return payload


def admit_campaign(
    *, suite: SuiteDefinition, rows: list[dict[str, Any]], results_root: Path,
    harness_root: Path, cache_root: Path, work_root: Path,
    local_source: Path | None = None, codex_auth: Path | None = None,
    source: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Check every selected condition without inference, then freeze its authority."""
    if "oracle_reviews" in suite.experiment or (suite.root / "qualification" / "oracle-reviews.json").is_file():
        validate_oracle_reviews(suite, require_complete=True)
    directory = results_root / ".campaign"
    with _locked(directory):
        existing = (directory / "authority.json").exists()
        if not existing and results_root.exists() and any(
            path.is_dir() and not path.name.startswith(".")
            for path in results_root.iterdir()
        ):
            raise CampaignAuthorityError("existing results have no campaign authority")
        payload = audit_campaign(
            suite=suite, rows=rows, harness_root=harness_root,
            cache_root=cache_root, work_root=work_root,
            local_source=local_source, codex_auth=codex_auth, source=source,
        )
        if existing:
            if _read_manifest(directory) != payload:
                raise CampaignAuthorityError(
                    "campaign selection or execution authority changed; use a new root"
                )
        else:
            _write_manifest(directory, payload)
        return payload


def verify_trial_authority(
    *, results_root: Path, campaign: dict[str, Any], admission: TrialAdmission,
) -> None:
    observed = _read_manifest(results_root / ".campaign")
    if observed != campaign:
        raise CampaignAuthorityError("campaign authority receipt changed")
    if "oracle_reviews" in admission.suite.experiment:
        review_path = admission.suite.root / admission.suite.experiment["oracle_reviews"]
        try:
            review_digest = hashlib.sha256(review_path.read_bytes()).hexdigest()
        except OSError as exc:
            raise CampaignAuthorityError("oracle review evidence disappeared") from exc
        if review_digest != observed.get("oracle_review_sha256"):
            raise CampaignAuthorityError("oracle review authority changed before inference")
    if admission.definition_id not in observed["selected_definitions"]:
        raise CampaignAuthorityError("trial is outside frozen campaign selection")
    expected = observed["task_conditions"].get(str(admission.task["id"]), {}).get(
        str(admission.condition["id"])
    )
    if expected != condition_authority(admission):
        raise CampaignAuthorityError("observed trial authority drifted before inference")
    inputs = digest({
        "workspace": admission.admitted_state,
        "mutation": admission.mutation_authority,
        "prompt": admission.task["prompt"],
        "budgets": admission.task["budgets"],
    })
    if observed["task_inputs"].get(str(admission.task["id"])) != inputs:
        raise CampaignAuthorityError("trial inputs differ from admitted campaign")


def claim_launch(
    *, results_root: Path, campaign: dict[str, Any],
    definition_id: str, trial_id: str,
) -> None:
    """Create a durable claim before invoking a model; never replace one."""
    directory = results_root / ".campaign" / "claims"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{definition_id}.json"
    payload = canonical_json({
        "campaign_id": campaign["campaign_id"],
        "definition_id": definition_id,
        "trial_id": trial_id,
    })
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise CampaignAuthorityError(
            f"trial launch already claimed: {definition_id}"
        ) from exc
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    directory_fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def launch_state(
    *, results_root: Path, campaign: dict[str, Any],
    definition_id: str, trial_id: str,
) -> str:
    path = results_root / ".campaign" / "claims" / f"{definition_id}.json"
    if not path.exists():
        return "UNCLAIMED"
    try:
        claim = json.loads(path.read_bytes())
    except (OSError, ValueError) as exc:
        raise CampaignAuthorityError("trial launch claim is corrupt") from exc
    if claim != {
        "campaign_id": campaign["campaign_id"],
        "definition_id": definition_id,
        "trial_id": trial_id,
    }:
        raise CampaignAuthorityError("trial launch claim identity mismatch")
    valid, _reason = verify_bundle(results_root / trial_id)
    return "COMPLETE" if valid else "INTERRUPTED"
