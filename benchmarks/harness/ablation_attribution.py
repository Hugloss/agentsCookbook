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

ABLATION_REPORT_SCHEMA = "agentscookbook.harbor-ablation-report.v2"
ABLATION_ROLES = ("bare", "full", "remove", "only")
LEGACY_TASK_EVIDENCE_CONTRACT = {
    "component": "task_evidence",
    "arms": {
        "bare": "none",
        "full": "hashmarks",
        "remove": "hashmarks-no-task-evidence",
        "only": "hashmarks-task-evidence-only",
    },
}


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


def _normalize_ablation_contract(value: object) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    component = value.get("component")
    arms = value.get("arms")
    if (
        not isinstance(component, str)
        or not component
        or not isinstance(arms, Mapping)
        or set(arms) != set(ABLATION_ROLES)
    ):
        return None
    normalized_arms = {
        role: str(arms[role])
        for role in ABLATION_ROLES
        if isinstance(arms.get(role), str) and arms.get(role)
    }
    if (
        len(normalized_arms) != len(ABLATION_ROLES)
        or len(set(normalized_arms.values())) != len(ABLATION_ROLES)
    ):
        return None
    return {
        "component": component,
        "arms": normalized_arms,
    }


def _receipt_ablation_contract(
    receipt: Mapping[str, Any],
) -> dict[str, Any] | None:
    execution = receipt.get("execution")
    value = execution.get("ablation") if isinstance(execution, Mapping) else None
    return _normalize_ablation_contract(value)


def _component_invoked(
    projection: Mapping[str, Any],
    *,
    component: str,
) -> bool | None:
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
            operation=component,
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
    return value if isinstance(value, Mapping) else None


def _validate_quartet_authority(
    arms: Mapping[str, Mapping[str, Any]],
    *,
    contract: Mapping[str, Any],
) -> tuple[bool, str | None]:
    if set(arms) != set(ABLATION_ROLES):
        return False, "missing-ablation-arm"
    component = str(contract["component"])
    full = _treatment(arms["full"]["receipt"])
    removed = _treatment(arms["remove"]["receipt"])
    only = _treatment(arms["only"]["receipt"])
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
        and component in full_tools
    ):
        return False, "full-arm-not-canonical"
    if not (
        removed.get("full_contract") is False
        and isinstance(removed_tools, list)
        and component not in removed_tools
        and set(removed_tools) == set(full_tools) - {component}
    ):
        return False, "removal-arm-not-single-tool-ablation"
    if not (
        only.get("full_contract") is False
        and only_tools == [component]
    ):
        return False, "only-arm-not-component-only"
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
                raw,
                subject="hashmarks",
                operation=operation,
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
    full = _treatment(arms["full"]["receipt"])
    canonical_tools = (
        full.get("tools")
        if isinstance(full, Mapping)
        else None
    )
    if not isinstance(canonical_tools, list):
        canonical_tools = []
    return {
        role: _observed_tool_projection(
            arms[role],
            canonical_tools=canonical_tools,
        )
        for role in ABLATION_ROLES
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
        return "UNATTRIBUTABLE_FULL_NEVER_INVOKED_COMPONENT"
    return "UNKNOWN_COMPONENT_INVOCATION"


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
        return "UNATTRIBUTABLE_ONLY_ARM_NEVER_INVOKED_COMPONENT"
    return "UNKNOWN_COMPONENT_INVOCATION"


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
    return "NO_ISOLATED_COMPONENT_SIGNAL"


def quartet_projection(
    arms: Mapping[str, Mapping[str, Any]],
    *,
    contract: Mapping[str, Any] | None = None,
    contract_source: str = "receipt",
) -> dict[str, Any]:
    normalized = (
        _normalize_ablation_contract(contract)
        if contract is not None
        else dict(LEGACY_TASK_EVIDENCE_CONTRACT)
    )
    if normalized is None:
        raise MechanismAttributionError("invalid component-ablation contract")
    component = str(normalized["component"])
    valid, authority_error = _validate_quartet_authority(
        arms,
        contract=normalized,
    )
    call_audits = _quartet_call_audits(arms)
    if valid:
        for role in ABLATION_ROLES:
            if call_audits[role]["status"] != "NO_DISALLOWED_CALL_OBSERVED":
                valid = False
                authority_error = (
                    "observed-mcp-call-not-qualified:"
                    + role
                    + ":"
                    + str(call_audits[role]["status"])
                )
                break
    statuses = {
        role: _status(arms[role])
        for role in ABLATION_ROLES
    }
    full_invoked = _component_invoked(
        arms["full"],
        component=component,
    )
    only_invoked = _component_invoked(
        arms["only"],
        component=component,
    )
    necessity = (
        _necessity(
            full_status=statuses["full"],
            removed_status=statuses["remove"],
            full_invoked=full_invoked,
        )
        if valid
        else "UNQUALIFIED_TREATMENT_AUTHORITY"
    )
    sufficiency = (
        _sufficiency(
            bare_status=statuses["bare"],
            only_status=statuses["only"],
            only_invoked=only_invoked,
        )
        if valid
        else "UNQUALIFIED_TREATMENT_AUTHORITY"
    )
    receipt = arms["bare"]["receipt"]
    return {
        "task": receipt.get("task_id"),
        "harness": receipt.get("harness"),
        "model": receipt.get("model"),
        "replicate_id": receipt.get("replicate_id"),
        "component": component,
        "subjects": dict(normalized["arms"]),
        "contract_source": contract_source,
        "statuses": statuses,
        "treatment_authority_valid": valid,
        "treatment_authority_error": authority_error,
        "observed_call_projection": call_audits,
        "observed_catalog_advertisement_proven": False,
        "component_invoked": {
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


def _rate(rows: list[Mapping[str, Any]]) -> float | None:
    outcomes = [_status(row) for row in rows]
    complete = [value for value in outcomes if value in {"PASS", "FAIL"}]
    if not complete:
        return None
    return sum(value == "PASS" for value in complete) / len(complete)


def _contrast(left: float | None, right: float | None) -> float | None:
    return None if left is None or right is None else left - right


def _legacy_contract_needed(
    projections: list[dict[str, Any]],
) -> bool:
    legacy_specific = {
        LEGACY_TASK_EVIDENCE_CONTRACT["arms"]["remove"],
        LEGACY_TASK_EVIDENCE_CONTRACT["arms"]["only"],
    }
    return any(
        _receipt_ablation_contract(projection["receipt"]) is None
        and str(projection["receipt"].get("subject")) in legacy_specific
        for projection in projections
    )


def build_ablation_report(results_root: Path) -> dict[str, Any]:
    projections: list[dict[str, Any]] = []
    unavailable: list[dict[str, str]] = []
    if results_root.is_dir():
        for directory in sorted(results_root.iterdir()):
            if not directory.is_dir() or directory.name.startswith("."):
                continue
            try:
                projections.append(load_harbor_bundle_projection(directory))
            except (MechanismAttributionError, OSError, ValueError) as exc:
                unavailable.append(
                    {"directory": str(directory), "reason": str(exc)}
                )

    legacy_enabled = _legacy_contract_needed(projections)
    grouped: dict[
        tuple[object, ...],
        dict[str, list[dict[str, Any]]],
    ] = defaultdict(lambda: defaultdict(list))
    contracts: dict[tuple[object, ...], dict[str, Any]] = {}
    contract_sources: dict[tuple[object, ...], set[str]] = defaultdict(set)
    eligible: list[tuple[dict[str, Any], dict[str, Any], str]] = []

    for projection in projections:
        receipt = projection["receipt"]
        contract = _receipt_ablation_contract(receipt)
        source = "receipt"
        if contract is None and legacy_enabled:
            subject = str(receipt.get("subject"))
            if subject in LEGACY_TASK_EVIDENCE_CONTRACT["arms"].values():
                contract = dict(LEGACY_TASK_EVIDENCE_CONTRACT)
                source = "legacy-task-evidence-subjects"
        if contract is None:
            continue
        subject = str(receipt.get("subject"))
        role = next(
            (
                role_name
                for role_name, role_subject in contract["arms"].items()
                if role_subject == subject
            ),
            None,
        )
        if role is None:
            continue
        key = (
            *_pair_key(receipt),
            contract["component"],
            tuple(
                (role_name, contract["arms"][role_name])
                for role_name in ABLATION_ROLES
            ),
        )
        grouped[key][role].append(projection)
        contracts[key] = contract
        contract_sources[key].add(source)
        eligible.append((projection, contract, role))

    components = {
        str(contract["component"])
        for contract in contracts.values()
    }
    if len(components) > 1:
        raise MechanismAttributionError(
            "mixed component-ablation contracts in one Harbor result set"
        )

    quartets: list[dict[str, Any]] = []
    incomplete_groups: list[dict[str, Any]] = []
    for key, arms in sorted(
        grouped.items(),
        key=lambda item: tuple(str(value) for value in item[0]),
    ):
        contract = contracts[key]
        if any(len(arms.get(role, [])) != 1 for role in ABLATION_ROLES):
            incomplete_groups.append(
                {
                    "pair_key": [
                        str(value) if value is not None else None
                        for value in key[:5]
                    ],
                    "component": contract["component"],
                    "arm_counts": {
                        role: len(arms.get(role, []))
                        for role in ABLATION_ROLES
                    },
                }
            )
            continue
        sources = contract_sources[key]
        quartets.append(
            quartet_projection(
                {role: arms[role][0] for role in ABLATION_ROLES},
                contract=contract,
                contract_source=(
                    next(iter(sources))
                    if len(sources) == 1
                    else "mixed-compatible"
                ),
            )
        )

    classifications = Counter(
        str(row["classification"])
        for row in quartets
    )
    necessity = Counter(str(row["necessity"]) for row in quartets)
    sufficiency = Counter(str(row["sufficiency"]) for row in quartets)

    component = next(iter(components)) if components else None
    arms = (
        dict(next(iter(contracts.values()))["arms"])
        if contracts
        else {}
    )
    by_harness: dict[str, dict[str, Any]] = {}
    harnesses = sorted(
        {
            str(projection["receipt"].get("harness"))
            for projection, _contract, _role in eligible
        }
    )
    for harness in harnesses:
        per_role: dict[str, float | None] = {}
        for role in ABLATION_ROLES:
            selected = [
                projection
                for projection, _contract, observed_role in eligible
                if observed_role == role
                and str(projection["receipt"].get("harness")) == harness
            ]
            per_role[role] = _rate(selected)
        bare = per_role["bare"]
        full = per_role["full"]
        removed = per_role["remove"]
        only = per_role["only"]
        by_harness[harness] = {
            "subjects": arms,
            "success_rate": per_role,
            "contrasts": {
                "full_uplift_vs_bare": _contrast(full, bare),
                "removal_drop": _contrast(full, removed),
                "only_uplift_vs_bare": _contrast(only, bare),
            },
        }

    applicable = bool(contracts)
    return {
        "schema": ABLATION_REPORT_SCHEMA,
        "applicable": applicable,
        "component": component,
        "arms": arms,
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
                "bare/full/remove-component/component-only arms"
            ),
            "necessity_contrast": (
                "full Hashmarks versus full Hashmarks minus the declared component"
            ),
            "sufficiency_contrast": (
                "bare versus the declared component as the only Hashmarks tool"
            ),
            "invocation_gate": (
                "positive component attribution requires observable invocation "
                "in the relevant full or only arm"
            ),
            "call_projection_limit": (
                "ATIF invocation records can disqualify observed calls outside "
                "a frozen MCP projection, but cannot attest to the entire tool "
                "catalog actually advertised by a model host"
            ),
            "reasoning_content_consumed": False,
            "positive_causal_claim_policy": (
                "controlled component ablation strengthens attribution but does not "
                "by itself establish universal causal necessity or sufficiency"
            ),
        },
    }
