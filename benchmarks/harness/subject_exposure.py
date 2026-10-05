"""Mandatory subject-exposure qualification for benchmark campaigns."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable

from benchmarks.harness.suite import SuiteDefinition


def subject_exposure_qualification(
    *,
    suite: SuiteDefinition,
    expected_rows: Iterable[dict[str, Any]],
    receipts: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Require every selected non-control condition to prove subject exposure.

    This check is intentionally subject-agnostic. It relies only on the frozen
    condition/subject definitions plus canonical agent measurements, so future
    MCP subjects inherit the same qualification rule without benchmark code
    changes.
    """

    experiment = getattr(suite, "experiment", None)
    subjects = getattr(suite, "subjects", None)
    if not isinstance(experiment, dict) or not isinstance(subjects, dict):
        return {
            "status": "NOT_APPLICABLE",
            "qualified": True,
            "policy": "non-control conditions must prove observable subject use",
            "conditions": [],
            "failed_conditions": 0,
            "pending_conditions": 0,
        }

    conditions = {
        str(condition["id"]): condition
        for condition in experiment["conditions"]
    }
    expected_counts = Counter(
        str(row["condition_id"])
        for row in expected_rows
    )
    by_condition: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for receipt in receipts:
        condition = receipt.get("condition", {}).get("id")
        if isinstance(condition, str):
            by_condition[condition].append(receipt)

    rows: list[dict[str, Any]] = []
    for condition_id in sorted(expected_counts):
        condition = conditions.get(condition_id)
        if not isinstance(condition, dict):
            continue
        subject_id = str(condition["subject"])
        subject = subjects[subject_id]
        if subject.get("kind") == "control":
            continue

        expected = int(expected_counts[condition_id])
        observed_receipts = by_condition.get(condition_id, [])
        available = sum(
            receipt.get("authority", {}).get("subject", {}).get("available") is True
            for receipt in observed_receipts
        )
        configured = sum(
            receipt.get("measurements", {})
            .get("agent", {})
            .get("subject_tool_configured")
            is True
            for receipt in observed_receipts
        )
        invocation_observed = sum(
            isinstance(
                receipt.get("measurements", {})
                .get("agent", {})
                .get("subject_tool_invoked"),
                bool,
            )
            for receipt in observed_receipts
        )
        invoked = sum(
            receipt.get("measurements", {})
            .get("agent", {})
            .get("subject_tool_invoked")
            is True
            for receipt in observed_receipts
        )
        complete = len(observed_receipts) == expected
        reasons: list[str] = []
        if complete:
            if available != expected:
                reasons.append("subject-availability-unproven")
            if configured != expected:
                reasons.append("subject-configuration-unproven")
            if invocation_observed != expected:
                reasons.append("subject-invocation-observability-incomplete")
            if invoked == 0:
                reasons.append("subject-never-invoked")

        rows.append(
            {
                "condition_id": condition_id,
                "subject_id": subject_id,
                "expected_trials": expected,
                "observed_trials": len(observed_receipts),
                "available_trials": available,
                "configured_trials": configured,
                "invocation_observed_trials": invocation_observed,
                "invoked_trials": invoked,
                "not_invoked_trials": invocation_observed - invoked,
                "invocation_unknown_trials": len(observed_receipts)
                - invocation_observed,
                "status": (
                    "PENDING"
                    if not complete
                    else "PASS"
                    if not reasons
                    else "FAIL"
                ),
                "reason_codes": reasons,
            }
        )

    if not rows:
        return {
            "status": "NOT_APPLICABLE",
            "qualified": True,
            "policy": "non-control conditions must prove observable subject use",
            "conditions": [],
            "failed_conditions": 0,
            "pending_conditions": 0,
        }

    failed = sum(row["status"] == "FAIL" for row in rows)
    pending = sum(row["status"] == "PENDING" for row in rows)
    return {
        "status": (
            "PASS"
            if not failed and not pending
            else "PENDING"
            if pending
            else "FAIL"
        ),
        "qualified": not failed and not pending,
        "policy": (
            "each selected non-control condition must prove complete invocation "
            "observability and at least one subject-tool invocation"
        ),
        "conditions": rows,
        "failed_conditions": failed,
        "pending_conditions": pending,
    }


def subject_exposure_issues(qualification: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for row in qualification.get("conditions", []):
        if not isinstance(row, dict) or row.get("status") != "FAIL":
            continue
        condition_id = row.get("condition_id")
        subject_id = row.get("subject_id")
        reasons = row.get("reason_codes")
        if not isinstance(reasons, list):
            reasons = []
        issues.append(
            "subject exposure qualification failed for "
            f"{condition_id} ({subject_id}): "
            + ", ".join(str(reason) for reason in reasons)
        )
    return issues
