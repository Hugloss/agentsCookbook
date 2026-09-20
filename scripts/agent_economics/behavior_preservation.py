from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence

SCHEMA = "agentscookbook-behavior-preservation-evidence/v2"
TARGET_TEST_OWNERSHIP_SCHEMA = "agentscookbook-target-test-ownership-evidence/v1"
POST_EDIT_SCHEMA = "agentscookbook-behavior-preservation-receipt/v1"
PRESERVED = "BEHAVIOR_PRESERVATION_VERIFIED"
POST_EDIT_EVIDENCE_REQUIRED = "POST_EDIT_EVIDENCE_REQUIRED"
DEBT_DELTA_SCHEMA = "agentscookbook-behavior-preservation-debt-delta/v1"
DEBT_VERIFIED = "VERIFIED"
DEBT_REDISTRIBUTED = "DEBT_REDISTRIBUTED"
TARGET_DEBT_NOT_REDUCED = "TARGET_DEBT_NOT_REDUCED"
MEASUREMENT_NOT_COMPARABLE = "MEASUREMENT_NOT_COMPARABLE"
READY = "READY_FOR_BEHAVIOR_PRESERVING_EDIT"
TEST_STRENGTHENING_REQUIRED = "TEST_STRENGTHENING_REQUIRED"
EVIDENCE_REQUIRED = "EVIDENCE_REQUIRED"


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _identity(payload: Mapping[str, object]) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _normalize_test_references(
    test_references: Sequence[Mapping[str, object]],
) -> list[dict[str, str]]:
    return sorted(
        [
            {
                "path": str(row.get("path") or ""),
                "evidence_identity": str(row.get("evidence_identity") or ""),
            }
            for row in test_references
        ],
        key=lambda row: (row["path"], row["evidence_identity"]),
    )


def target_test_ownership_evidence(
    *,
    target: str,
    source_identity: str,
    test_references: Sequence[Mapping[str, object]],
    provider: str,
    provider_evidence_identity: str,
) -> dict[str, object]:
    """Bind confirmed tests to one exact target/source state.

    This is evidence correlation only. It does not prove semantic test adequacy or
    authorize an edit.
    """
    if not _nonempty(target) or not _nonempty(source_identity):
        raise ValueError("target and source_identity must be non-empty")
    if not _nonempty(provider) or not _nonempty(provider_evidence_identity):
        raise ValueError("provider and provider_evidence_identity must be non-empty")
    normalized_tests = _normalize_test_references(test_references)
    if not normalized_tests or any(
        not _nonempty(row["path"]) or not _nonempty(row["evidence_identity"])
        for row in normalized_tests
    ):
        raise ValueError("test_references must contain identified tests")
    semantic = {
        "schema": TARGET_TEST_OWNERSHIP_SCHEMA,
        "target": target,
        "source_identity": source_identity,
        "confirmed_test_references": normalized_tests,
        "provider": provider,
        "provider_evidence_identity": provider_evidence_identity,
    }
    return {**semantic, "evidence_identity": _identity(semantic)}


def _normalize_target_test_ownership(
    evidence: Mapping[str, object] | None,
) -> dict[str, object] | None:
    if not isinstance(evidence, Mapping):
        return None
    raw_tests = evidence.get("confirmed_test_references")
    tests = (
        _normalize_test_references(
            [row for row in raw_tests if isinstance(row, Mapping)]
        )
        if isinstance(raw_tests, Sequence)
        and not isinstance(raw_tests, (str, bytes, bytearray))
        else []
    )
    return {
        "schema": evidence.get("schema"),
        "target": evidence.get("target"),
        "source_identity": evidence.get("source_identity"),
        "confirmed_test_references": tests,
        "provider": evidence.get("provider"),
        "provider_evidence_identity": evidence.get("provider_evidence_identity"),
        "evidence_identity": evidence.get("evidence_identity"),
    }


def _target_test_ownership_matches(
    evidence: Mapping[str, object] | None,
    *,
    target: str,
    source_identity: str,
    normalized_tests: Sequence[Mapping[str, str]],
) -> tuple[bool, dict[str, object] | None]:
    normalized = _normalize_target_test_ownership(evidence)
    if normalized is None:
        return False, None
    semantic = {
        key: normalized[key]
        for key in (
            "schema",
            "target",
            "source_identity",
            "confirmed_test_references",
            "provider",
            "provider_evidence_identity",
        )
    }
    valid = (
        normalized["schema"] == TARGET_TEST_OWNERSHIP_SCHEMA
        and normalized["target"] == target
        and normalized["source_identity"] == source_identity
        and normalized["confirmed_test_references"] == list(normalized_tests)
        and _nonempty(normalized["provider"])
        and _nonempty(normalized["provider_evidence_identity"])
        and normalized["evidence_identity"] == _identity(semantic)
    )
    return valid, normalized


def behavior_preservation_readiness(
    *,
    target: str,
    source_identity: str,
    boundaries: Sequence[Mapping[str, object]],
    test_references: Sequence[Mapping[str, object]],
    execution_receipt: Mapping[str, object] | None,
    repository_gates: Sequence[Mapping[str, object]],
    test_ownership_evidence: Mapping[str, object] | None = None,
    coverage_evidence: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Assess pre-edit evidence readiness without authorizing a refactor."""
    if not _nonempty(target) or not _nonempty(source_identity):
        raise ValueError("target and source_identity must be non-empty")
    if not boundaries:
        raise ValueError("at least one behavior/risk boundary is required")

    unresolved: list[str] = []
    strengthening: list[str] = []
    normalized_tests = _normalize_test_references(test_references)
    if not normalized_tests or any(
        not _nonempty(row["path"]) or not _nonempty(row["evidence_identity"])
        for row in normalized_tests
    ):
        unresolved.append("confirmed-test-references")
    selected_test_ids = {
        row["evidence_identity"]
        for row in normalized_tests
        if _nonempty(row["evidence_identity"])
    }

    normalized_boundaries: list[dict[str, object]] = []
    for row in boundaries:
        identity = row.get("identity")
        classification = row.get("classification")
        freshness = row.get("freshness")
        provider_reference = row.get("provider_reference")
        raw_boundary_test_ids = row.get("test_evidence_identities")
        boundary_test_ids = (
            sorted({str(item) for item in raw_boundary_test_ids})
            if isinstance(raw_boundary_test_ids, Sequence)
            and not isinstance(raw_boundary_test_ids, (str, bytes, bytearray))
            else []
        )
        if not _nonempty(identity):
            unresolved.append("<invalid-boundary>")
            continue
        identity = str(identity)
        normalized_boundaries.append(
            {
                "identity": identity,
                "classification": classification,
                "freshness": freshness,
                "provider_reference": provider_reference,
                "test_evidence_identities": boundary_test_ids,
            }
        )
        if classification not in {"direct", "indirect"}:
            unresolved.append(identity)
        elif freshness not in {"fresh", "stale"}:
            unresolved.append(identity)
        elif freshness == "stale":
            unresolved.append(identity)
        elif classification != "direct":
            strengthening.append(identity)
        if not isinstance(provider_reference, Mapping):
            unresolved.append(identity)
        elif not _nonempty(provider_reference.get("provider")) or not _nonempty(
            provider_reference.get("evidence_identity")
        ):
            unresolved.append(identity)
        if (
            not boundary_test_ids
            or any(not _nonempty(test_id) for test_id in boundary_test_ids)
            or any(test_id not in selected_test_ids for test_id in boundary_test_ids)
        ):
            unresolved.append(f"{identity}:boundary-test-binding")

    ownership_ok, normalized_ownership = _target_test_ownership_matches(
        test_ownership_evidence,
        target=target,
        source_identity=source_identity,
        normalized_tests=normalized_tests,
    )
    if not ownership_ok:
        unresolved.append("target-bound-test-ownership")

    receipt_ok = False
    normalized_receipt: dict[str, object] | None = None
    if isinstance(execution_receipt, Mapping):
        receipt_source = execution_receipt.get("source_identity")
        receipt_status = execution_receipt.get("status")
        receipt_tests = execution_receipt.get("test_evidence_identities")
        normalized_receipt = {
            "source_identity": receipt_source,
            "status": receipt_status,
            "test_evidence_identities": sorted(str(item) for item in receipt_tests)
            if isinstance(receipt_tests, Sequence)
            and not isinstance(receipt_tests, (str, bytes, bytearray))
            else None,
            "execution_identity": execution_receipt.get("execution_identity"),
        }
        expected_tests = sorted(row["evidence_identity"] for row in normalized_tests)
        receipt_ok = (
            receipt_source == source_identity
            and receipt_status == "PASS"
            and normalized_receipt["test_evidence_identities"] == expected_tests
            and _nonempty(normalized_receipt["execution_identity"])
        )
    if not receipt_ok:
        unresolved.append("bound-pre-edit-test-execution")

    normalized_gates = sorted(
        [
            {
                "name": str(row.get("name") or ""),
                "command": str(row.get("command") or ""),
            }
            for row in repository_gates
        ],
        key=lambda row: (row["name"], row["command"]),
    )
    if not normalized_gates or any(
        not _nonempty(row["name"]) or not _nonempty(row["command"])
        for row in normalized_gates
    ):
        unresolved.append("broader-repository-gates")

    unresolved = sorted(set(unresolved))
    strengthening = sorted(set(strengthening))
    if unresolved:
        status = EVIDENCE_REQUIRED
    elif strengthening:
        status = TEST_STRENGTHENING_REQUIRED
    else:
        status = READY

    semantic = {
        "schema": SCHEMA,
        "target": target,
        "source_identity": source_identity,
        "boundaries": sorted(normalized_boundaries, key=lambda row: str(row["identity"])),
        "test_references": normalized_tests,
        "test_ownership_evidence": normalized_ownership,
        "execution_receipt": normalized_receipt,
        "repository_gates": normalized_gates,
        "coverage_evidence": dict(coverage_evidence) if coverage_evidence is not None else None,
        "status": status,
        "unresolved_evidence": unresolved,
        "boundaries_requiring_test_strengthening": strengthening,
    }
    return {
        **semantic,
        "evidence_identity": _identity(semantic),
        "authority": {
            "edit_authorized": False,
            "refactor_safety_proven": False,
            "repository_policy_owned": False,
        },
        "required_next_evidence": (
            [{"kind": "resolve_pre_edit_evidence", "items": unresolved}]
            if unresolved
            else (
                [{"kind": "strengthen_behavioral_tests", "boundaries": strengthening}]
                if strengthening
                else []
            )
        ),
        "post_edit_requirements": [
            "rerun-bound-focused-tests",
            "run-affected-component-verification",
            "run-repository-gates",
            "remeasure-current-debt",
        ],
    }


def behavior_preservation_receipt(
    *,
    pre_edit_evidence: Mapping[str, object],
    post_edit_source_identity: str,
    post_edit_test_references: Sequence[Mapping[str, object]],
    post_edit_execution_receipt: Mapping[str, object] | None,
    repository_gate_receipts: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Bind post-edit verification to frozen pre-edit behavior evidence."""
    unresolved: list[str] = []
    if pre_edit_evidence.get("schema") != SCHEMA or pre_edit_evidence.get("status") != READY:
        unresolved.append("ready-pre-edit-evidence")
    pre_edit_evidence_identity = pre_edit_evidence.get("evidence_identity")
    pre_edit_source_identity = pre_edit_evidence.get("source_identity")
    if not _nonempty(pre_edit_evidence_identity) or not _nonempty(pre_edit_source_identity):
        unresolved.append("identified-pre-edit-evidence")
    if not _nonempty(post_edit_source_identity):
        unresolved.append("post-edit-source-identity")

    frozen_tests = sorted(
        [
            {
                "path": str(row.get("path") or ""),
                "evidence_identity": str(row.get("evidence_identity") or ""),
            }
            for row in pre_edit_evidence.get("test_references", [])
            if isinstance(row, Mapping)
        ],
        key=lambda row: (row["path"], row["evidence_identity"]),
    )
    post_tests = sorted(
        [
            {
                "path": str(row.get("path") or ""),
                "evidence_identity": str(row.get("evidence_identity") or ""),
            }
            for row in post_edit_test_references
        ],
        key=lambda row: (row["path"], row["evidence_identity"]),
    )
    if not frozen_tests or post_tests != frozen_tests:
        unresolved.append("frozen-test-identities")

    normalized_execution: dict[str, object] | None = None
    execution_ok = False
    if isinstance(post_edit_execution_receipt, Mapping):
        receipt_tests = post_edit_execution_receipt.get("test_evidence_identities")
        normalized_execution = {
            "source_identity": post_edit_execution_receipt.get("source_identity"),
            "status": post_edit_execution_receipt.get("status"),
            "test_evidence_identities": sorted(str(item) for item in receipt_tests)
            if isinstance(receipt_tests, Sequence)
            and not isinstance(receipt_tests, (str, bytes, bytearray))
            else None,
            "execution_identity": post_edit_execution_receipt.get("execution_identity"),
        }
        execution_ok = (
            normalized_execution["source_identity"] == post_edit_source_identity
            and normalized_execution["status"] == "PASS"
            and normalized_execution["test_evidence_identities"]
            == sorted(row["evidence_identity"] for row in frozen_tests)
            and _nonempty(normalized_execution["execution_identity"])
        )
    if not execution_ok:
        unresolved.append("bound-post-edit-test-execution")

    expected_gates = sorted(
        (str(row.get("name") or ""), str(row.get("command") or ""))
        for row in pre_edit_evidence.get("repository_gates", [])
        if isinstance(row, Mapping)
    )
    normalized_gate_receipts = sorted(
        [
            {
                "name": str(row.get("name") or ""),
                "command": str(row.get("command") or ""),
                "status": str(row.get("status") or ""),
                "execution_identity": str(row.get("execution_identity") or ""),
            }
            for row in repository_gate_receipts
        ],
        key=lambda row: (row["name"], row["command"]),
    )
    actual_gates = [(row["name"], row["command"]) for row in normalized_gate_receipts]
    gates_ok = (
        bool(expected_gates)
        and actual_gates == expected_gates
        and all(row["status"] == "PASS" and _nonempty(row["execution_identity"]) for row in normalized_gate_receipts)
    )
    if not gates_ok:
        unresolved.append("bound-repository-gate-execution")

    unresolved = sorted(set(unresolved))
    status = PRESERVED if not unresolved else POST_EDIT_EVIDENCE_REQUIRED
    semantic = {
        "schema": POST_EDIT_SCHEMA,
        "pre_edit_evidence_identity": pre_edit_evidence_identity,
        "pre_edit_source_identity": pre_edit_source_identity,
        "post_edit_source_identity": post_edit_source_identity,
        "frozen_test_references": frozen_tests,
        "post_edit_execution_receipt": normalized_execution,
        "repository_gate_receipts": normalized_gate_receipts,
        "status": status,
        "unresolved_evidence": unresolved,
    }
    return {
        **semantic,
        "evidence_identity": _identity(semantic),
        "authority": {
            "merge_authorized": False,
            "architectural_improvement_proven": False,
            "repository_policy_owned": False,
        },
        "claims": {
            "frozen_behavioral_evidence_preserved": status == PRESERVED,
            "debt_reduction_proves_preservation": False,
        },
        "required_next_evidence": (
            [{"kind": "resolve_post_edit_evidence", "items": unresolved}] if unresolved else []
        ),
    }


def behavior_preservation_debt_delta(
    *,
    target: str,
    pre_measurement_identity: str,
    post_measurement_identity: str,
    measurement_configuration_identity: str,
    post_measurement_configuration_identity: str,
    pre_repository_excess: int,
    post_repository_excess: int,
    pre_target_excess: int,
    post_target_excess: int,
    preservation_receipt: Mapping[str, object],
) -> dict[str, object]:
    """Prove that measured cleanup debt was removed from the selected target, not moved."""
    if not _nonempty(target):
        raise ValueError("target must be non-empty")
    identities = (
        pre_measurement_identity,
        post_measurement_identity,
        measurement_configuration_identity,
        post_measurement_configuration_identity,
    )
    if any(not _nonempty(value) for value in identities):
        raise ValueError("measurement identities must be non-empty")
    values = (
        pre_repository_excess,
        post_repository_excess,
        pre_target_excess,
        post_target_excess,
    )
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in values):
        raise ValueError("debt excess values must be non-negative integers")

    repository_reduction = pre_repository_excess - post_repository_excess
    target_reduction = pre_target_excess - post_target_excess
    outside_target_delta = (
        post_repository_excess - post_target_excess
    ) - (
        pre_repository_excess - pre_target_excess
    )
    preservation_verified = preservation_receipt.get("status") == PRESERVED
    comparable = (
        measurement_configuration_identity
        == post_measurement_configuration_identity
        and pre_measurement_identity != post_measurement_identity
    )

    if not preservation_verified:
        status = POST_EDIT_EVIDENCE_REQUIRED
    elif not comparable:
        status = MEASUREMENT_NOT_COMPARABLE
    elif target_reduction <= 0:
        status = TARGET_DEBT_NOT_REDUCED
    elif outside_target_delta > 0:
        status = DEBT_REDISTRIBUTED
    else:
        status = DEBT_VERIFIED

    semantic = {
        "schema": DEBT_DELTA_SCHEMA,
        "target": target,
        "pre_measurement_identity": pre_measurement_identity,
        "post_measurement_identity": post_measurement_identity,
        "measurement_configuration_identity": measurement_configuration_identity,
        "post_measurement_configuration_identity": post_measurement_configuration_identity,
        "pre_repository_excess": pre_repository_excess,
        "post_repository_excess": post_repository_excess,
        "pre_target_excess": pre_target_excess,
        "post_target_excess": post_target_excess,
        "repository_reduction": repository_reduction,
        "target_reduction": target_reduction,
        "outside_target_delta": outside_target_delta,
        "preservation_evidence_identity": preservation_receipt.get("evidence_identity"),
        "status": status,
    }
    return {
        **semantic,
        "evidence_identity": _identity(semantic),
        "claims": {
            "behavior_preservation_verified": preservation_verified,
            "measurement_comparable": comparable,
            "target_debt_reduced": target_reduction > 0,
            "debt_not_redistributed": outside_target_delta <= 0,
        },
    }
