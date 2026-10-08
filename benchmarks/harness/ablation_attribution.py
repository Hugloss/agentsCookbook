"""Controlled Harbor component-ablation analysis.

This layer compares matched bare/full/remove/only quartets. It consumes only
immutable receipts plus observable ATIF tool evidence. It never consumes model
reasoning or upgrades a paired contrast into positive causal proof.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from benchmarks.tool_routing import is_subject_tool, matches_subject_operation

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


def _observed_tool_projection(
    arm: Mapping[str, Any],
    *,
    canonical_tools: list[str],
) -> dict[str, Any]:
    """Conservatively check ATIF calls against the frozen arm catalog.

    ATIF records invocations, not the advertised MCP catalog. Missing or
    unrecognized calls must never be promoted to proof of exposed tools.
    """
    receipt = arm["receipt"]
    trace = arm.get("trace")
    treatment = _treatment(receipt)
    allowed = treatment.get("tools") if isinstance(treatment, Mapping) else []
    subject_tools = trace.get("subject_tools") if isinstance(trace, Mapping) else None
    if (
        not isinstance(trace, Mapping)
        or trace.get("available") is not True
        or trace.get("tool_order_complete") is not True
        or not isinstance(subject_tools, list)
    ):
        return {
            "status": "UNQUALIFIED_TRACE_INCOMPLETE",
            "observed_subject_calls": None,
            "disallowed_calls": [],
            "unresolved_calls": [],
            "catalog_advertisement_proven": False,
        }
    if not isinstance(allowed, list) or any(
        not isinstance(name, str) for name in allowed
    ):
        allowed = []
    disallowed: list[str] = []
    unresolved: list[str] = []
    observed = 0
    for raw in subject_tools:
        if not is_subject_tool(raw, "hashmarks"):
            unresolved.append(str(raw))
            continue
        observed += 1
        candidates = [
            operation
            for operation in canonical_tools
            if matches_subject_operation(
                raw, subject="hashmarks", operation=operation
            )
        ]
        if len(candidates) != 1:
            unresolved.append(str(raw))
        elif candidates[0] not in allowed:
            disallowed.append(str(raw))
    status = (
        "UNQUALIFIED_DISALLOWED_CALL"
        if disallowed
        else "UNQUALIFIED_UNRESOLVED_CALL"
        if unresolved
        else "NO_DISALLOWED_CALL_OBSERVED"
    )
    return {
        "status": status,
        "observed_subject_calls": observed,
        "disallowed_calls": disallowed,
        "unresolved_calls": unresolved,
        "catalog_advertisement_proven": False,
    }


def _quartet_call_audits(
    arms: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    full = _treatment(arms["hashmarks"]["receipt"])
    canonical_tools = (
        full.get("tools") if isinstance(full, Mapping) else None
    )
    if not isinstance(canonical_tools, list):
        canonical_tools = []
    return {
        subject: _observed_tool_projection(
            arms[subject], canonical_tools=canonical_tools
        )
        for subject in ABLATION_SUBJECTS
    }


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
    call_audits = _quartet_call_audits(arms)
    if valid:
        for subject in ABLATION_SUBJECTS:
            if call_audits[subject]["status"] != "NO_DISALLOWED_CALL_OBSERVED":
                valid = False
                authority_error = (
                    "observed-mcp-call-not-qualified:"
                    + subject
                    + ":"
                    + str(call_audits[subject]["status"])
                )
                break
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
        "observed_call_projection": call_audits,
        "observed_catalog_advertisement_proven": False,
        "task_evidence_invoked": {
            "full": full_invoked,
            "only": only_invoked,
        },
        "necessity": necessity,
        "sufficiency": sufficiency,
        "classification": (
            _combined(necessity, sufficiency)
            if valid
            else "UNQUALIFIED_TREATMENT_AUTHORITY"
        ),
        "positive_causal_proof_claimed": False,
    }


def _qualified_complete_quartet(quartet: Mapping[str, Any]) -> bool:
    """Only qualified, fully observed quartets support component contrasts."""
    statuses = quartet.get("statuses")
    return (
        quartet.get("treatment_authority_valid") is True
        and isinstance(statuses, Mapping)
        and all(statuses.get(subject) in {"PASS", "FAIL"} for subject in ABLATION_SUBJECTS)
    )


def _qualified_rate(quartets: list[dict[str, Any]], subject: str) -> float | None:
    if not quartets:
        return None
    return sum(row["statuses"][subject] == "PASS" for row in quartets) / len(quartets)


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

    qualified = [row for row in quartets if _qualified_complete_quartet(row)]
    invalid_treatment = sum(
        row["treatment_authority_valid"] is not True for row in quartets
    )
    incomplete_outcomes = len(quartets) - len(qualified) - invalid_treatment
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
        matched_count = sum(row["harness"] == harness for row in quartets)
        selected = [row for row in qualified if row["harness"] == harness]
        per_subject = {
            subject: _qualified_rate(selected, subject)
            for subject in ABLATION_SUBJECTS
        }
        bare = per_subject["none"]
        full = per_subject["hashmarks"]
        removed = per_subject["hashmarks-no-task-evidence"]
        only = per_subject["hashmarks-task-evidence-only"]
        by_harness[harness] = {
            "matched_quartets": matched_count,
            "qualified_complete_quartets": len(selected),
            "excluded_matched_quartets": matched_count - len(selected),
            "success_rate": per_subject,
            "full_uplift_vs_bare": _contrast(full, bare),
            "task_evidence_removal_drop": _contrast(full, removed),
            "task_evidence_only_uplift_vs_bare": _contrast(only, bare),
        }

    applicable = any(
        subject in {
            "hashmarks-no-task-evidence",
            "hashmarks-task-evidence-only",
        }
        for arms in grouped.values()
        for subject in arms
    )
    return {
        "schema": ABLATION_REPORT_SCHEMA,
        "applicable": applicable,
        "component": "task_evidence",
        "arms": list(ABLATION_SUBJECTS),
        "quartets": quartets,
        "summary": {
            "matched_quartets": len(quartets),
            "qualified_complete_quartets": len(qualified),
            "treatment_unqualified_quartets": invalid_treatment,
            "incomplete_outcome_quartets": incomplete_outcomes,
            "excluded_matched_quartets": len(quartets) - len(qualified),
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
            "call_projection_limit": (
                "ATIF invocation records can disqualify observed calls outside "
                "a frozen MCP projection, but cannot attest to the entire tool "
                "catalog actually advertised by a model host"
            ),
            "aggregate_denominator": (
                "qualified complete matched quartets only; treatment-unqualified "
                "or incomplete outcomes are excluded, never scored as failures or "
                "mixed into per-harness component contrasts"
            ),
            "reasoning_content_consumed": False,
            "positive_causal_claim_policy": (
                "controlled component ablation strengthens attribution but does not "
                "by itself establish universal causal necessity or sufficiency"
            ),
        },
    }
