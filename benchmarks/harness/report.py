"""Aggregate complete benchmark receipts without ranking products."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from benchmarks.harness.bundle import verify_bundle
from benchmarks.harness.suite import SuiteDefinition


class ReportError(ValueError):
    pass


_VALID_OUTCOMES = {"PASS", "FAIL", "NO_QUALIFYING_DEFECT"}
_NUMERIC_AGENT_METRICS = (
    "duration_ms",
    "command_calls",
    "mcp_calls",
    "subject_mcp_calls",
    "mcp_result_bytes",
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
)


def _receipts(results_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not results_root.exists():
        return rows
    for directory in sorted(path for path in results_root.iterdir() if path.is_dir()):
        if directory.name.startswith("."):
            continue
        valid, reason = verify_bundle(directory)
        if not valid:
            raise ReportError(
                f"invalid published result bundle {directory}: {reason}"
            )
        try:
            value = json.loads(
                (directory / "result.json").read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise ReportError(f"cannot load complete receipt {directory}: {exc}") from exc
        if not isinstance(value, dict):
            raise ReportError(f"receipt is not an object: {directory}")
        rows.append(value)
    return rows


def _condition_id(receipt: dict[str, Any]) -> str:
    value = receipt.get("condition", {}).get("id")
    if not isinstance(value, str) or not value:
        raise ReportError("receipt has no condition id")
    return value


def _task_id(receipt: dict[str, Any]) -> str:
    value = receipt.get("task", {}).get("id")
    if not isinstance(value, str) or not value:
        raise ReportError("receipt has no task id")
    return value


def _agent_metric(receipt: dict[str, Any], name: str) -> int | float | None:
    value = receipt.get("measurements", {}).get("agent", {}).get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _aggregate_condition(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = Counter(str(row.get("status")) for row in receipts)
    valid = [row for row in receipts if row.get("status") in _VALID_OUTCOMES]
    passed = [row for row in valid if row.get("status") == "PASS"]
    tool_available = [
        row
        for row in valid
        if row.get("authority", {}).get("subject", {}).get("available") is True
        and row.get("measurements", {})
        .get("agent", {})
        .get("subject_tool_configured")
        is True
    ]
    invoked = [
        row
        for row in tool_available
        if row.get("measurements", {})
        .get("agent", {})
        .get("subject_tool_invoked")
        is True
    ]
    metrics: dict[str, Any] = {}
    for name in _NUMERIC_AGENT_METRICS:
        values = [
            value
            for row in valid
            if (value := _agent_metric(row, name)) is not None
        ]
        metrics[name] = {
            "observations": len(values),
            "mean": mean(values) if values else None,
            "total": sum(values) if values else None,
        }
    return {
        "trials": len(receipts),
        "valid_outcomes": len(valid),
        "statuses": dict(sorted(statuses.items())),
        "task_success_rate": len(passed) / len(valid) if valid else None,
        "subject_tool_adoption_rate": (
            len(invoked) / len(tool_available) if tool_available else None
        ),
        "metrics": metrics,
    }


def _pair_key(receipt: dict[str, Any]) -> tuple[str, str, int, int]:
    condition = receipt["condition"]
    execution = receipt["execution"]
    agent_id = str(condition["agent_definition"]["id"])
    return (
        _task_id(receipt),
        agent_id,
        int(execution["trial_index"]),
        int(execution["seed"]),
    )


def _paired_assistance(receipts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bare: dict[tuple[str, str, int, int], dict[str, Any]] = {}
    assisted: list[dict[str, Any]] = []
    for receipt in receipts:
        if receipt.get("status") not in _VALID_OUTCOMES:
            continue
        adapter = (
            receipt.get("condition", {})
            .get("subject_definition", {})
            .get("adapter")
        )
        if adapter == "none":
            key = _pair_key(receipt)
            if key in bare:
                raise ReportError(f"multiple bare executions for pair {key}")
            bare[key] = receipt
        else:
            assisted.append(receipt)

    rows: list[dict[str, Any]] = []
    for receipt in assisted:
        key = _pair_key(receipt)
        baseline = bare.get(key)
        if baseline is None:
            continue
        row: dict[str, Any] = {
            "task_id": key[0],
            "agent_id": key[1],
            "trial_index": key[2],
            "seed": key[3],
            "condition_id": _condition_id(receipt),
            "subject_id": receipt["condition"]["subject_definition"]["id"],
            "bare_status": baseline["status"],
            "assisted_status": receipt["status"],
            "task_success_delta": (
                int(receipt["status"] == "PASS")
                - int(baseline["status"] == "PASS")
            ),
        }
        for metric in (
            "duration_ms",
            "command_calls",
            "mcp_calls",
            "input_tokens",
            "output_tokens",
        ):
            left = _agent_metric(baseline, metric)
            right = _agent_metric(receipt, metric)
            row[f"{metric}_delta"] = (
                right - left if left is not None and right is not None else None
            )
        rows.append(row)
    return sorted(
        rows,
        key=lambda row: (
            str(row["task_id"]),
            str(row["agent_id"]),
            int(row["trial_index"]),
            str(row["condition_id"]),
        ),
    )


def build_report(
    *,
    suite: SuiteDefinition,
    results_root: Path,
    require_complete: bool = True,
) -> dict[str, Any]:
    receipts = _receipts(results_root)
    expected = {
        str(row["definition_id"]): row for row in suite.trial_definitions()
    }
    by_definition: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for receipt in receipts:
        definition = receipt.get("definition_id")
        if not isinstance(definition, str):
            raise ReportError("receipt has no definition_id")
        if definition not in expected:
            raise ReportError(
                f"results contain execution outside frozen suite: {definition}"
            )
        by_definition[definition].append(receipt)

    duplicates = {
        definition: values
        for definition, values in by_definition.items()
        if len(values) > 1
    }
    if duplicates:
        raise ReportError(
            "multiple executions found for frozen definition(s): "
            + ", ".join(sorted(duplicates))
        )

    missing = sorted(set(expected) - set(by_definition))
    if require_complete and missing:
        raise ReportError(
            f"campaign is incomplete: {len(missing)} frozen definition(s) missing"
        )

    by_condition: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for receipt in receipts:
        by_condition[_condition_id(receipt)].append(receipt)

    statuses = Counter(str(row.get("status")) for row in receipts)
    return {
        "schema": {
            "name": "agents-cookbook-benchmark-report",
            "version": 1,
        },
        "suite": suite.experiment["suite"],
        "experiment": {
            "id": suite.experiment["id"],
            "version": suite.experiment["version"],
        },
        "expected_trials": len(expected),
        "observed_trials": len(receipts),
        "missing_definitions": missing,
        "status_counts": dict(sorted(statuses.items())),
        "conditions": {
            condition: _aggregate_condition(rows)
            for condition, rows in sorted(by_condition.items())
        },
        "paired_assistance": _paired_assistance(receipts),
        "authority": {
            "overall_winner": None,
            "ranking_performed": False,
            "mixed_execution_definitions_rejected": True,
            "invalid_outcomes_excluded_from_success_rates": True,
        },
    }
