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
    "tool_calls",
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


def _metric_summary(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for name in _NUMERIC_AGENT_METRICS:
        values = [
            value
            for row in receipts
            if (value := _agent_metric(row, name)) is not None
        ]
        metrics[name] = {
            "observations": len(values),
            "mean": mean(values) if values else None,
            "total": sum(values) if values else None,
        }
    return metrics


def _aggregate_condition(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = Counter(str(row.get("status")) for row in receipts)
    valid = [row for row in receipts if row.get("status") in _VALID_OUTCOMES]
    passed = [row for row in valid if row.get("status") == "PASS"]
    tool_available = [
        row
        for row in receipts
        if row.get("authority", {}).get("subject", {}).get("available") is True
        and row.get("measurements", {})
        .get("agent", {})
        .get("subject_tool_configured")
        is True
        and isinstance(
            row.get("measurements", {})
            .get("agent", {})
            .get("subject_tool_invoked"),
            bool,
        )
    ]
    invoked = [
        row
        for row in tool_available
        if row.get("measurements", {})
        .get("agent", {})
        .get("subject_tool_invoked")
        is True
    ]
    observability = sorted(
        {
            value
            for row in receipts
            if isinstance(
                (
                    value := row.get("measurements", {})
                    .get("agent", {})
                    .get("source_read_observability")
                ),
                str,
            )
        }
    )
    return {
        "trials": len(receipts),
        "valid_outcomes": len(valid),
        "statuses": dict(sorted(statuses.items())),
        "task_success_rate": len(passed) / len(valid) if valid else None,
        "subject_tool_adoption_rate": (
            len(invoked) / len(tool_available) if tool_available else None
        ),
        "subject_tool_adoption_denominator": len(tool_available),
        "source_read_observability": observability,
        "metrics": _metric_summary(receipts),
        "valid_outcome_metrics": _metric_summary(valid),
    }


def _agent_id(receipt: dict[str, Any]) -> str:
    value = (
        receipt.get("condition", {})
        .get("agent_definition", {})
        .get("id")
    )
    if not isinstance(value, str) or not value:
        raise ReportError("receipt has no frozen agent id")
    return value


def _subject_id(receipt: dict[str, Any]) -> str:
    value = (
        receipt.get("condition", {})
        .get("subject_definition", {})
        .get("id")
    )
    if not isinstance(value, str) or not value:
        raise ReportError("receipt has no frozen subject id")
    return value


def _comparison_identity(receipt: dict[str, Any]) -> dict[str, Any]:
    """Runtime authority shared by conditions; trial MCP wiring is excluded."""
    agent = receipt.get("authority", {}).get("agent", {})
    observed = agent.get("observed", {})
    if not isinstance(observed, dict):
        observed = {}
    adapter = receipt["condition"]["agent_definition"]["adapter"]
    common = {
        "adapter": adapter,
        "version": observed.get("version"),
        "executable_sha256": observed.get("executable_sha256"),
        "auth_mode": observed.get("auth_mode"),
        "model": observed.get("model"),
    }
    if adapter == "opencode-native":
        common.update(
            provider=observed.get("provider"),
            native_config_sha256=observed.get("native_config_sha256"),
        )
    elif adapter == "codex":
        common["reasoning_effort"] = observed.get("reasoning_effort")
    return common


def _subject_comparison_identity(
    receipt: dict[str, Any],
) -> dict[str, Any] | None:
    if _subject_id(receipt) == "none":
        return None
    subject = receipt.get("authority", {}).get("subject", {})
    observed = subject.get("observed")
    if not isinstance(observed, dict):
        observed = {"value": observed}
    return {
        "declared": subject.get("declared"),
        "observed": observed,
    }


def _check_comparable_subjects(receipts: list[dict[str, Any]]) -> None:
    identities: dict[tuple[str, str], dict[str, Any]] = {}
    for receipt in receipts:
        identity = _subject_comparison_identity(receipt)
        if identity is None:
            continue
        key = (_agent_id(receipt), _subject_id(receipt))
        prior = identities.setdefault(key, identity)
        if prior != identity:
            raise ReportError(
                "mixed observed subject authority for "
                f"agent {key[0]} / subject {key[1]}; "
                "use separate result campaigns"
            )


def validate_comparability(receipts: list[dict[str, Any]]) -> None:
    _check_comparable_agents(receipts)
    _check_comparable_subjects(receipts)


def _check_comparable_agents(receipts: list[dict[str, Any]]) -> None:
    identities: dict[str, dict[str, Any]] = {}
    for receipt in receipts:
        agent = _agent_id(receipt)
        identity = _comparison_identity(receipt)
        if not any(
            identity.get(key) is not None
            for key in ("version", "executable_sha256", "model", "native_config_sha256")
        ):
            continue
        prior = identities.setdefault(agent, identity)
        if prior != identity:
            raise ReportError(
                f"mixed observed runtime authority for agent {agent}; "
                "use separate result campaigns"
            )


def _pair_key(receipt: dict[str, Any]) -> tuple[str, str, int, int]:
    condition = receipt["condition"]
    execution = receipt["execution"]
    agent_id = _agent_id(receipt)
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


def _cross_agent_observations(
    receipts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[
        tuple[str, str, int, int],
        dict[str, dict[str, Any]],
    ] = defaultdict(dict)
    for receipt in receipts:
        if receipt.get("status") not in _VALID_OUTCOMES:
            continue
        execution = receipt["execution"]
        key = (
            _task_id(receipt),
            _subject_id(receipt),
            int(execution["trial_index"]),
            int(execution["seed"]),
        )
        agent = _agent_id(receipt)
        if agent in grouped[key]:
            raise ReportError(
                f"multiple executions for cross-agent observation {key} / {agent}"
            )
        grouped[key][agent] = {
            "status": receipt["status"],
            "duration_ms": _agent_metric(receipt, "duration_ms"),
            "tool_calls": _agent_metric(receipt, "tool_calls"),
            "mcp_calls": _agent_metric(receipt, "mcp_calls"),
            "subject_mcp_calls": _agent_metric(
                receipt,
                "subject_mcp_calls",
            ),
            "input_tokens": _agent_metric(receipt, "input_tokens"),
            "output_tokens": _agent_metric(receipt, "output_tokens"),
            "subject_tool_invoked": (
                receipt.get("measurements", {})
                .get("agent", {})
                .get("subject_tool_invoked")
            ),
        }

    return [
        {
            "task_id": key[0],
            "subject_id": key[1],
            "trial_index": key[2],
            "seed": key[3],
            "agents": dict(sorted(agents.items())),
        }
        for key, agents in sorted(grouped.items())
        if len(agents) > 1
    ]


def build_report(
    *,
    suite: SuiteDefinition,
    results_root: Path,
    require_complete: bool = True,
    selected_definitions: set[str] | None = None,
    selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipts = _receipts(results_root)
    all_expected = {
        str(row["definition_id"]): row for row in suite.trial_definitions()
    }
    expected = (
        all_expected
        if selected_definitions is None
        else {
            key: row for key, row in all_expected.items()
            if key in selected_definitions
        }
    )
    if selected_definitions is not None and set(expected) != selected_definitions:
        raise ReportError("report selection contains definitions outside frozen suite")
    by_definition: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for receipt in receipts:
        definition = receipt.get("definition_id")
        if not isinstance(definition, str):
            raise ReportError("receipt has no definition_id")
        if definition not in all_expected:
            raise ReportError(
                f"results contain execution outside frozen suite: {definition}"
            )
        if definition in expected:
            by_definition[definition].append(receipt)

    receipts = [row for rows in by_definition.values() for row in rows]

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

    validate_comparability(receipts)

    by_condition: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_agent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for receipt in receipts:
        by_condition[_condition_id(receipt)].append(receipt)
        by_agent[_agent_id(receipt)].append(receipt)

    statuses = Counter(str(row.get("status")) for row in receipts)
    return {
        "schema": {
            "name": "agents-cookbook-benchmark-report",
            "version": 3,
        },
        "suite": suite.experiment["suite"],
        "experiment": {
            "id": suite.experiment["id"],
            "version": suite.experiment["version"],
        },
        "selection": selection or {
            "tasks": [], "agents": [], "subjects": [],
            "condition": None, "bare_control_included": False,
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
        "agent_profiles": {
            agent: _aggregate_condition(rows)
            for agent, rows in sorted(by_agent.items())
        },
        "cross_agent_observations": _cross_agent_observations(receipts),
        "authority": {
            "overall_winner": None,
            "ranking_performed": False,
            "mixed_execution_definitions_rejected": True,
            "invalid_outcomes_excluded_from_success_rates": True,
            "economics_include_invalid_and_incomplete_trials": True,
            "paired_assistance_scope": "valid-outcomes-only",
            "cross_agent_rows_are_descriptive": True,
        },
    }
