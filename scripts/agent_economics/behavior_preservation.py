from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence

SCHEMA = "agentscookbook-behavior-preservation-evidence/v1"
POST_EDIT_SCHEMA = "agentscookbook-behavior-preservation-receipt/v1"
PRESERVED = "BEHAVIOR_PRESERVATION_VERIFIED"
POST_EDIT_EVIDENCE_REQUIRED = "POST_EDIT_EVIDENCE_REQUIRED"
READY = "READY_FOR_BEHAVIOR_PRESERVING_EDIT"
TEST_STRENGTHENING_REQUIRED = "TEST_STRENGTHENING_REQUIRED"
EVIDENCE_REQUIRED = "EVIDENCE_REQUIRED"


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _identity(payload: Mapping[str, object]) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def behavior_preservation_readiness(
    *,
    target: str,
    source_identity: str,
    boundaries: Sequence[Mapping[str, object]],
    test_references: Sequence[Mapping[str, object]],
    execution_receipt: Mapping[str, object] | None,
    repository_gates: Sequence[Mapping[str, object]],
    coverage_evidence: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Assess pre-edit evidence readiness without authorizing a refactor."""
    if not _nonempty(target) or not _nonempty(source_identity):
        raise ValueError("target and source_identity must be non-empty")
    if not boundaries:
        raise ValueError("at least one behavior/risk boundary is required")

    unresolved: list[str] = []
    strengthening: list[str] = []
    normalized_boundaries: list[dict[str, object]] = []
    for row in boundaries:
        identity = row.get("identity")
        classification = row.get("classification")
        freshness = row.get("freshness")
        provider_reference = row.get("provider_reference")
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

    normalized_tests = sorted(
        [
            {
                "path": str(row.get("path") or ""),
                "evidence_identity": str(row.get("evidence_identity") or ""),
            }
            for row in test_references
        ],
        key=lambda row: (row["path"], row["evidence_identity"]),
    )
    if not normalized_tests or any(
        not _nonempty(row["path"]) or not _nonempty(row["evidence_identity"])
        for row in normalized_tests
    ):
        unresolved.append("confirmed-test-references")

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
