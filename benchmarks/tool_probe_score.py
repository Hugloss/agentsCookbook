"""Descriptive scoring for separate required-tool diagnostics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmarks.harness.report import build_report
from benchmarks.harness.suite import load_suite
from benchmarks.harness.trace_diagnostics import build_trace_diagnostics
from benchmarks.tool_probe import REQUIRED_TOOLS
from benchmarks.tool_routing import (
    TOOL_ROUTER,
    classify_call,
    first_discovery_index,
    matches_subject_operation,
)


def _matches_required(name: object, subject: str, required: str) -> bool:
    return matches_subject_operation(
        name,
        subject=subject,
        operation=required.removeprefix(subject + "_"),
    )


def _call_class(call: dict[str, object], subject: str) -> str:
    value = call.get("tool_class")
    if isinstance(value, str):
        return value
    return classify_call(
        call.get("tool"),
        call.get("inputs") or call.get("input"),
        subject=subject,
    )


def _required_call_result(
    calls: list[dict[str, object]] | None, subject: str, required: str
) -> tuple[bool | None, bool | None]:
    if calls is None:
        return None, None
    matching = [call for call in calls if _matches_required(
        call.get("tool"), subject, required
    )]
    succeeded = any(
        call.get("status") == "completed"
        and isinstance(call.get("result_bytes"), int)
        and call["result_bytes"] > 0
        for call in matching
    )
    if succeeded:
        return True, True
    if matching and any(
        call.get("status") == "completed" and call.get("result_bytes") is None
        for call in matching
    ):
        return True, None
    return bool(matching), False


def _required_success_index(
    calls: list[dict[str, object]],
    subject: str,
    required: str,
) -> int | None:
    for index, call in enumerate(calls):
        if not _matches_required(call.get("tool"), subject, required):
            continue
        if (
            call.get("status") == "completed"
            and isinstance(call.get("result_bytes"), int)
            and call["result_bytes"] > 0
        ):
            return index
    return None


def _required_before_native_discovery(
    calls: list[dict[str, object]] | None,
    subject: str,
    required: str,
) -> bool | None:
    if calls is None:
        return None
    normalized = [
        {**call, "tool_class": _call_class(call, subject)}
        for call in calls
    ]
    discovery_index = first_discovery_index(normalized)
    required_index = _required_success_index(normalized, subject, required)
    opaque_router_indexes = [
        index
        for index, call in enumerate(normalized)
        if call.get("tool_class") == TOOL_ROUTER
        and call.get("routing_observability") != "expanded"
    ]

    if required_index is not None and required_index < discovery_index:
        if any(index < required_index for index in opaque_router_indexes):
            return None
        return True
    if any(index < discovery_index for index in opaque_router_indexes):
        return None
    return False


def _first_native_discovery(
    calls: list[dict[str, object]] | None,
    subject: str,
) -> tuple[str | None, object | None]:
    if calls is None:
        return None, None
    normalized = [
        {**call, "tool_class": _call_class(call, subject)}
        for call in calls
    ]
    index = first_discovery_index(normalized)
    if index == len(normalized):
        return None, None
    call = normalized[index]
    tool_class = call.get("tool_class")
    return (
        tool_class if isinstance(tool_class, str) else None,
        call.get("tool"),
    )


def smoke_gate(
    score: dict[str, object], *, subject: str, expected_trials: int = 3
) -> None:
    if score.get("schema") != "agents-cookbook-tool-probe-score.v3":
        raise ValueError("tool-probe smoke score v3 is required")
    if score.get("subject") != subject or score.get("required_tool") != REQUIRED_TOOLS[subject]:
        raise ValueError("smoke score subject or required tool differs from selection")
    rows = score.get("required_tool_results")
    if not isinstance(rows, list) or len(rows) != expected_trials or (
        score.get("expected_trials") != expected_trials or
        score.get("observed_trials") != expected_trials
    ):
        raise ValueError("smoke requires exactly three observed trials")
    if len({row.get("trial_id") for row in rows}) != expected_trials or len({
        row.get("task_id") for row in rows
    }) != 1 or any(
        not isinstance(row.get("trial_id"), str) or not row["trial_id"] or
        not isinstance(row.get("task_id"), str) or not row["task_id"]
        for row in rows
    ):
        raise ValueError("smoke trial identities or task selection are inconsistent")
    for row in rows:
        if row.get("status") not in {"PASS", "FAIL"} or row.get("required_call_succeeded") is not True or (
            row.get("required_before_native_discovery") is not True
        ):
            raise ValueError(
                "smoke requires completed nonempty subject calls before native "
                "repository discovery in all trials"
            )


def main(suite_root: Path) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--agent", action="append", required=True)
    parser.add_argument("--definition-id", action="append", default=[])
    args = parser.parse_args()
    suite = load_suite(suite_root)
    if args.agent != ["opencode-native"]:
        parser.error("tool-probe score requires only opencode-native")
    selected = set(args.definition_id) or {
        str(row["definition_id"]) for row in suite.trial_definitions()
    }
    report = build_report(
        suite=suite, results_root=args.results, selected_definitions=selected,
        require_complete=True,
    )
    traces = build_trace_diagnostics(args.results)
    subject = suite.experiment["conditions"][0]["subject"]
    required = REQUIRED_TOOLS[subject]
    rows = []
    for trial in traces["trials"]:
        if trial["definition_id"] not in selected:
            continue
        calls = trial["calls"]
        trace_observed = calls is not None
        attempted, successful = _required_call_result(calls, subject, required)
        first_class, first_tool = _first_native_discovery(calls, subject)
        rows.append({
            "trial_id": trial["trial_id"],
            "task_id": trial["task_id"],
            "status": trial["status"],
            "required_tool": required,
            "trace_observed": trace_observed,
            "required_call_attempted": attempted,
            "required_call_succeeded": successful,
            "required_before_native_discovery": _required_before_native_discovery(
                calls,
                subject,
                required,
            ),
            "first_native_discovery_class": first_class,
            "first_native_discovery_tool": first_tool,
        })
    score = {
        "schema": "agents-cookbook-tool-probe-score.v3",
        "authority": {"diagnostic_only": True, "heldout_comparable": False},
        "subject": subject,
        "required_tool": required,
        "expected_trials": report["expected_trials"],
        "observed_trials": report["observed_trials"],
        "semantic_status_counts": report["status_counts"],
        "required_tool_results": sorted(rows, key=lambda row: row["trial_id"]),
        "required_call_successes": sum(row["required_call_succeeded"] is True for row in rows),
        "required_call_failures": sum(row["required_call_succeeded"] is False for row in rows),
        "required_call_unknown": sum(row["required_call_succeeded"] is None for row in rows),
        "required_before_native_discovery_successes": sum(
            row["required_before_native_discovery"] is True for row in rows
        ),
        "required_before_native_discovery_failures": sum(
            row["required_before_native_discovery"] is False for row in rows
        ),
        "required_before_native_discovery_unknown": sum(
            row["required_before_native_discovery"] is None for row in rows
        ),
    }
    args.output.write_text(json.dumps(score, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0
