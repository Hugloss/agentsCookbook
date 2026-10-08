"""Controlled Harbor component-ablation analysis.

This layer compares matched bare/full/remove/only quartets. It consumes only
immutable receipts plus observable ATIF tool evidence. It never consumes model
reasoning or upgrades a paired contrast into positive causal proof.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from benchmarks.tool_routing import matches_subject_operation

from .mechanism_attribution import (
    MechanismAttributionError,
    load_harbor_bundle_projection,
)

ABLATION_REPORT_SCHEMA = "agentscookbook.harbor-ablation-report.v1"
ABLATION_SUBJECTS = (
    "none",
    "hashmarks",
    "hashmarks-no-task-evidence",
    "hashmarks-task-evidence-only",
)


def _pair_key(receipt: Mapping[str, Any]) -> tuple[object, ...]:
    execution = receipt.get("execution")
    campaign_id = (
        execution.get("campaign_id")
        if isinstance(execution, dict)
        else None
    )
    return (
        campaign_id,
        receipt.get("task_id"),
        receipt.get("harness"),
        receipt.get("model"),
        receipt.get("replicate_id"),
    )


def _status(projection: Mapping[str, Any]) -> str:
    value = projection["receipt"].get("status")
    return str(value) if value in {"PASS", "FAIL"} else "INCOMPLETE"


def _task_evidence_invoked(projection: Mapping[str, Any]) -> bool | None:
    trace = projection.get("trace")
    if not isinstance(trace, dict) or trace.get("available") is not True:
        return None
    tools = trace.get("subject_tools")
    if not isinstance(tools, list):
        return None
    return any(
        matches_subject_operation(
            name,
            subject="hashmarks",
            operation="task_evidence",
        )
        for name in tools
    )


def _treatment(receipt: Mapping[str, Any]) -> Mapping[str, Any] | None:
    execution = receipt.get("execution")
    value = (
        execution.get("mcp_treatment")
        if isinstance(execution, dict)
        else None
    )
    return value if isinstance(value, dict) else None


def _validate_quartet_authority(
    arms: Mapping[str, Mapping[str, Any]],
) -> tuple[bool, str | None]:
    full = _treatment(arms["hashmarks"]["receipt"])
    removed = _treatment(arms["hashmarks-no-task-evidence"]["receipt"])
    only = _treatment(arms["hashmarks-task-evidence-only"]["receipt"])
    if not all(isinstance(value, Mapping) for value in (full, removed, only)):
        return False, "missing-frozen-mcp-treatment"
    assert full is not None and removed is not None and only is not None
    identities = {
        value.get("source_contract_identity")
        for value in (full, removed, only)
    }
    if len(identities) != 1 or None in identities:
        return False, "source-contract-mismatch"
    full_tools = full.get("tools")
    removed_tools = removed.get("tools")
    only_tools = only.get("tools")
    if not (
        full.get("full_contract") is True
        and isinstance(full_tools, list)
        and "task_evidence" in full_tools
    ):
        return False, "full-arm-not-canonical"
    if not (
        removed.get("full_contract") is False
        and isinstance(removed_tools, list)
        and "task_evidence" not in removed_tools
        and set(removed_tools) == set(full_tools) - {"task_evidence"}
    ):
        return False, "removal-arm-not-single-tool-ablation"
    if not (
        only.get("full_contract") is False
        and only_tools == ["task_evidence"]
    ):
        return False, "only-arm-not-task-evidence-only"
    return True, None


def _necessity(
    *,
    full_status: str,
    removed_status: str,
    full_invoked: bool | None,
) -> str:
    if full_status != "PASS":
        return "NOT_TESTABLE_FULL_DID_NOT_PASS"
    if removed_status == "PASS":
        return "NOT_NECESSARY_IN_THIS_REPLICATE"
    if removed_status != "FAIL":
        return "UNKNOWN_INCOMPLETE_REMOVAL_ARM"
    if full_invoked is True:
        return "SUPPORTED_NECESSITY_CONTRAST"
    if full_invoked is False:
        return "UNATTRIBUTABLE_FULL_NEVER_INVOKED_TASK_EVIDENCE"
    return "UNKNOWN_TASK_EVIDENCE_INVOCATION"


def _sufficiency(
    *,
    bare_status: str,
    only_status: str,
    only_invoked: bool | None,
) -> str:
    if bare_status != "FAIL":
        return (
            "NOT_TESTABLE_BARE_ALREADY_PASS"
            if bare_status == "PASS"
            else "UNKNOWN_INCOMPLETE_BARE_ARM"
        )
    if only_status == "FAIL":
        return "NOT_SUFFICIENT_IN_THIS_REPLICATE"
    if only_status != "PASS":
        return "UNKNOWN_INCOMPLETE_ONLY_ARM"
    if only_invoked is True:
        return "SUPPORTED_SUFFICIENCY_CONTRAST"
    if only_invoked is False:
        return "UNATTRIBUTABLE_ONLY_ARM_NEVER_INVOKED_TASK_EVIDENCE"
    return "UNKNOWN_TASK_EVIDENCE_INVOCATION"


def _combined(necessity: str, sufficiency: str) -> str:
    necessary = necessity == "SUPPORTED_NECESSITY_CONTRAST"
    sufficient = sufficiency == "SUPPORTED_SUFFICIENCY_CONTRAST"
    if necessary and sufficient:
        return "NECESSARY_AND_SUFFICIENT_CONTRAST"
    if necessary:
        return "NECESSITY_SIGNAL"
    if sufficient:
        return "SUFFICIENCY_SIGNAL"
    if necessity == "NOT_NECESSARY_IN_THIS_REPLICATE":
        return "REDUNDANT_OR_OTHER_HASHMARKS_PATH"
    return "NO_ISOLATED_TASK_EVIDENCE_SIGNAL"


def quartet_projection(
    arms: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    valid, authority_error = _validate_quartet_authority(arms)
    bare = arms["none"]
    full = arms["hashmarks"]
    removed = arms["hashmarks-no-task-evidence"]
    only = arms["hashmarks-task-evidence-only"]
    statuses = {
        "none": _status(bare),
        "hashmarks": _status(full),
        "hashmarks-no-task-evidence": _status(removed),
        "hashmarks-task-evidence-only": _status(only),
    }
    full_invoked = _task_evidence_invoked(full)
    only_invoked = _task_evidence_invoked(only)
    necessity = (
        _necessity(
            full_status=statuses["hashmarks"],
            removed_status=statuses["hashmarks-no-task-evidence"],
            full_invoked=full_invoked,
        )
        if valid
        else "UNQUALIFIED_TREATMENT_AUTHORITY"
    )
    sufficiency = (
        _sufficiency(
            bare_status=statuses["none"],
            only_status=statuses["hashmarks-task-evidence-only"],
            only_invoked=only_invoked,
        )
        if valid
        else "UNQUALIFIED_TREATMENT_AUTHORITY"
    )
    receipt = bare["receipt"]
    return {
        "task": receipt.get("task_id"),
        "harness": receipt.get("harness"),
        "model": receipt.get("model"),
        "replicate_id": receipt.get("replicate_id"),
        "statuses": statuses,
        "treatment_authority_valid": valid,
        "treatment_authority_error": authority_error,
        "task_evidence_invoked": {
            "full": full_invoked,
            "only": only_invoked,
        },
        "necessity": necessity,
        "sufficiency": sufficiency,
        "classification": _combined(necessity, sufficiency),
        "positive_causal_proof_claimed": False,
    }


def _rate(rows: list[Mapping[str, Any]]) -> float | None:
    outcomes = [_status(row) for row in rows]
    complete = [value for value in outcomes if value in {"PASS", "FAIL"}]
    if not complete:
        return None
    return sum(value == "PASS" for value in complete) / len(complete)


def _contrast(left: float | None, right: float | None) -> float | None:
    return None if left is None or right is None else left - right


def build_ablation_report(results_root: Path) -> dict[str, Any]:
    grouped: dict[
        tuple[object, ...],
        dict[str, list[dict[str, Any]]],
    ] = defaultdict(lambda: defaultdict(list))
    unavailable: list[dict[str, str]] = []

    if results_root.is_dir():
        for directory in sorted(results_root.iterdir()):
            if not directory.is_dir() or directory.name.startswith("."):
                continue
            try:
                projection = load_harbor_bundle_projection(directory)
            except (MechanismAttributionError, OSError, ValueError) as exc:
                unavailable.append(
                    {"directory": str(directory), "reason": str(exc)}
                )
                continue
            receipt = projection["receipt"]
            subject = str(receipt.get("subject"))
            if subject in ABLATION_SUBJECTS:
                grouped[_pair_key(receipt)][subject].append(projection)

    quartets: list[dict[str, Any]] = []
    incomplete_groups: list[dict[str, Any]] = []
    for key, arms in sorted(
        grouped.items(),
        key=lambda item: tuple(str(value) for value in item[0]),
    ):
        if any(len(arms.get(subject, [])) != 1 for subject in ABLATION_SUBJECTS):
            incomplete_groups.append(
                {
                    "pair_key": [
                        str(value) if value is not None else None for value in key
                    ],
                    "arm_counts": {
                        subject: len(arms.get(subject, []))
                        for subject in ABLATION_SUBJECTS
                    },
                }
            )
            continue
        quartets.append(
            quartet_projection(
                {subject: arms[subject][0] for subject in ABLATION_SUBJECTS}
            )
        )

    classifications = Counter(
        str(row["classification"]) for row in quartets
    )
    necessity = Counter(str(row["necessity"]) for row in quartets)
    sufficiency = Counter(str(row["sufficiency"]) for row in quartets)

    by_harness: dict[str, dict[str, Any]] = {}
    harnesses = sorted(
        {
            str(row["receipt"].get("harness"))
            for arms in grouped.values()
            for values in arms.values()
            for row in values
        }
    )
    for harness in harnesses:
        per_subject: dict[str, float | None] = {}
        for subject in ABLATION_SUBJECTS:
            selected = [
                projection
                for arms in grouped.values()
                for projection in arms.get(subject, [])
                if str(projection["receipt"].get("harness")) == harness
            ]
            per_subject[subject] = _rate(selected)
        bare = per_subject["none"]
        full = per_subject["hashmarks"]
        removed = per_subject["hashmarks-no-task-evidence"]
        only = per_subject["hashmarks-task-evidence-only"]
        by_harness[harness] = {
            "success_rate": per_subject,
            "full_uplift_vs_bare": _contrast(full, bare),
            "task_evidence_removal_drop": _contrast(full, removed),
            "task_evidence_only_uplift_vs_bare": _contrast(only, bare),
        }

    applicable = bool(grouped)
    return {
        "schema": ABLATION_REPORT_SCHEMA,
        "applicable": applicable,
        "component": "task_evidence",
        "arms": list(ABLATION_SUBJECTS),
        "quartets": quartets,
        "summary": {
            "matched_quartets": len(quartets),
            "incomplete_groups": len(incomplete_groups),
            "unavailable_bundles": len(unavailable),
            "classification": dict(sorted(classifications.items())),
            "necessity": dict(sorted(necessity.items())),
            "sufficiency": dict(sorted(sufficiency.items())),
            "positive_causal_proof_claimed": False,
        },
        "by_harness": by_harness,
        "incomplete_groups": incomplete_groups,
        "unavailable_bundles": unavailable,
        "method": {
            "design": (
                "same campaign + task + harness + model + replicate across "
                "bare/full/remove-task_evidence/task_evidence-only arms"
            ),
            "necessity_contrast": "full Hashmarks versus full minus task_evidence",
            "sufficiency_contrast": "bare versus task_evidence-only",
            "invocation_gate": (
                "positive task_evidence attribution requires observable invocation "
                "in the relevant full or only arm"
            ),
            "reasoning_content_consumed": False,
            "positive_causal_claim_policy": (
                "controlled component ablation strengthens attribution but does not "
                "by itself establish universal causal necessity or sufficiency"
            ),
        },
    }
