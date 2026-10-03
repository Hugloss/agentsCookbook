"""Descriptive scoring for separate required-tool diagnostics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmarks.harness.report import build_report
from benchmarks.harness.suite import load_suite
from benchmarks.harness.trace_diagnostics import build_trace_diagnostics
from benchmarks.tool_probe import REQUIRED_TOOLS


def _matches_required(name: object, subject: str, required: str) -> bool:
    tool = required.removeprefix(subject + "_")
    return name in {required, f"{subject}.{tool}", f"tools.{subject}.{tool}"}


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
    return bool(matching), succeeded


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
        rows.append({
            "trial_id": trial["trial_id"],
            "task_id": trial["task_id"],
            "status": trial["status"],
            "required_tool": required,
            "trace_observed": trace_observed,
            "required_call_attempted": attempted,
            "required_call_succeeded": successful,
        })
    score = {
        "schema": "agents-cookbook-tool-probe-score.v1",
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
    }
    args.output.write_text(json.dumps(score, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0
