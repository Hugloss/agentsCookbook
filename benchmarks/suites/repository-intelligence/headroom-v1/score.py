"""Diagnostic report for repository-intelligence bare-control headroom."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from benchmarks.harness.report import ReportError, build_report
from benchmarks.harness.selection import SelectionError, parse_agent_arguments
from benchmarks.harness.suite import load_suite


def _bare_headroom(
    report: dict[str, Any],
    *,
    bare_condition_ids: set[str],
) -> dict[str, Any]:
    summaries = [
        report["conditions"][condition_id]
        for condition_id in sorted(bare_condition_ids)
        if condition_id in report["conditions"]
    ]
    valid = sum(int(row["valid_outcomes"]) for row in summaries)
    passes = sum(int(row["statuses"].get("PASS", 0)) for row in summaries)
    failures = sum(int(row["statuses"].get("FAIL", 0)) for row in summaries)
    unresolved = sum(
        int(row["trials"]) - int(row["valid_outcomes"])
        for row in summaries
    )
    if not valid:
        state = "unavailable"
    elif failures:
        state = "observed"
    else:
        state = "not-observed"
    return {
        "state": state,
        "valid_trials": valid,
        "passes": passes,
        "failures": failures,
        "unresolved_trials": unresolved,
        "headroom_trials": failures,
        "headroom_rate": failures / valid if valid else None,
        "interpretation": (
            "bare control has reproducible semantic headroom"
            if state == "observed"
            else "bare control solved every valid diagnostic trial; this corpus does not yet demonstrate headroom"
            if state == "not-observed"
            else "bare-control headroom cannot be assessed without valid outcomes"
        ),
    }


def score(
    *,
    suite_root: Path,
    results: Path,
    agents: tuple[str, ...],
) -> dict[str, Any]:
    suite = load_suite(suite_root)
    if not agents:
        raise ValueError("select at least one frozen native agent")
    unknown = sorted(set(agents) - set(suite.agents))
    if unknown:
        raise ValueError("unknown benchmark agent(s): " + ", ".join(unknown))

    selected_agents = set(agents)
    conditions = {
        str(condition["id"]): condition
        for condition in suite.experiment["conditions"]
    }
    definitions = suite.trial_definitions()
    selected = {
        str(row["definition_id"])
        for row in definitions
        if conditions[str(row["condition_id"])]["agent"] in selected_agents
    }
    report = build_report(
        suite=suite,
        results_root=results,
        selected_definitions=selected,
        require_complete=True,
        selection={
            "tasks": [],
            "agents": sorted(agents),
            "subjects": [],
            "condition": None,
            "bare_control_included": True,
        },
    )
    bare_condition_ids = {
        str(condition["id"])
        for condition in suite.experiment["conditions"]
        if condition["agent"] in selected_agents and condition["subject"] == "none"
    }
    return {
        "schema": "agents-cookbook-repository-intelligence-headroom.v2",
        "diagnostic_only": True,
        "selection": {"agents": sorted(agents)},
        "expected_trials": report["expected_trials"],
        "observed_trials": report["observed_trials"],
        "status_counts": report["status_counts"],
        "campaign_qualification": report["campaign_qualification"],
        "bare_control_headroom": _bare_headroom(
            report,
            bare_condition_ids=bare_condition_ids,
        ),
        "bare_stability": [
            row
            for row in report["stability"]
            if row["subject_id"] == "none"
        ],
        "subject_adoption": report["subject_adoption"],
        "paired_assistance_summary": report["paired_assistance_summary"],
        "paired_assistance_usage_summary": report.get(
            "paired_assistance_usage_summary",
            [],
        ),
        "paired_assistance_exclusions": report["paired_assistance_exclusions"],
        "task_assistance_evidence": report.get("task_assistance_evidence", []),
        "conditions": report["conditions"],
        "agent_profiles": report["agent_profiles"],
        "diagnostics": report["diagnostics"],
        "authority": {
            "release_authority": False,
            "heldout_replacement": False,
            "overall_winner": None,
            "comparison": "within-agent paired diagnostic only",
            "headroom_is_observed_not_assumed": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--agent", action="append", required=True)
    args = parser.parse_args()
    try:
        agents = parse_agent_arguments(args.agent)
        payload = score(
            suite_root=Path(__file__).resolve().parent,
            results=args.results,
            agents=agents,
        )
    except (SelectionError, ValueError, ReportError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{args.output.name}.",
        dir=args.output.parent,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, args.output)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
