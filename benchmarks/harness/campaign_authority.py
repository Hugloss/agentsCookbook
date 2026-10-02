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


def claimed_definitions(results_root: Path, campaign_id: str) -> set[str]:
    directory = results_root / ".campaign" / "claims"
    if not directory.exists():
        return set()
    found = set()
    for path in directory.glob("*.json"):
        try:
            claim = json.loads(path.read_bytes())
        except (OSError, ValueError) as exc:
            raise CampaignAuthorityError(f"corrupt launch claim: {path}") from exc
        definition = path.stem
        if claim.get("campaign_id") != campaign_id or claim.get("definition_id") != definition:
            raise CampaignAuthorityError(f"launch claim identity mismatch: {path}")
        found.add(definition)
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


def admit_campaign(
    *, suite: SuiteDefinition, rows: list[dict[str, Any]], results_root: Path,
    harness_root: Path, cache_root: Path, work_root: Path,
    local_source: Path | None = None, codex_auth: Path | None = None,
    source: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Check every selected condition without inference, then freeze its authority."""
    if not rows:
        raise CampaignAuthorityError("campaign selection is empty")
    if "oracle_reviews" in suite.experiment or (suite.root / "qualification" / "oracle-reviews.json").is_file():
        validate_oracle_reviews(suite, require_complete=True)
    directory = results_root / ".campaign"
    selected = sorted(str(row["definition_id"]) for row in rows)
    representatives: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        representatives.setdefault((str(row["task_id"]), str(row["condition_id"])), row)
    with _locked(directory):
        existing = (directory / "authority.json").exists()
        if not existing and results_root.exists() and any(
            path.is_dir() and not path.name.startswith(".")
            for path in results_root.iterdir()
        ):
            raise CampaignAuthorityError("existing results have no campaign authority")
        observed: dict[str, Any] = {}
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
                if condition in observed and observed[condition] != authority:
                    raise CampaignAuthorityError(
                        f"{condition} authority differs across selected tasks"
                    )
                observed[condition] = authority
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
            "contract": "benchmark-campaign-authority.v1",
            "selected_definitions": selected,
            "conditions": observed,
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
    expected = observed["conditions"].get(str(admission.condition["id"]))
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
