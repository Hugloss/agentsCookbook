"""Lexigram report for behavioral-v4."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from benchmarks.harness.report import ReportError, build_report
from benchmarks.harness.selection import parse_agent_arguments
from benchmarks.harness.suite import load_suite

FAMILIES = (
    "post_change",
    "change_impact",
    "verification",
    "dependency_delta",
    "correlation",
    "declarations",
    "freshness",
    "negative_bounds",
)
LEXIGRAM = (
    (
        "admissibility",
        "ADMISSIBLE",
        "The trial has a valid sealed receipt and comparable authority.",
    ),
    ("authority", "BOUNDED", "No claim exceeds the admitted evidence."),
    (
        "resolution",
        "COMPLETE",
        "All required semantic claims and edited bytes are correct.",
    ),
    (
        "evidence",
        "PRESERVED",
        "Freshness, provenance, ambiguity, and reuse facts survive.",
    ),
    (
        "paired_benefit",
        "RESCUED",
        "The assisted run succeeds where its paired bare run fails.",
    ),
)


def _paired_grade(row: dict[str, Any]) -> str:
    bare = row["bare_status"] == "PASS"
    assisted = row["assisted_status"] == "PASS"
    if not assisted:
        return "REGRESSED" if bare else "NO_OBSERVED_GAIN"
    if not bare:
        return "RESCUED"
    if row.get("tool_calls_delta") is not None and row["tool_calls_delta"] < 0:
        return "LEANER"
    return "NO_OBSERVED_GAIN"


def _lexigram(report: dict[str, Any]) -> dict[str, Any]:
    statuses = report["status_counts"]
    pairs = report["paired_assistance"]
    labels = [_paired_grade(row) for row in pairs]
    grades = [
        {
            "dimension": "admissibility",
            "grade": "ADMISSIBLE"
            if report["observed_trials"] == report["expected_trials"]
            else "UNCOMPARABLE",
            "meaning": LEXIGRAM[0][2],
        },
        {
            "dimension": "authority",
            "grade": "BOUNDED"
            if not statuses.get("INVALID") and not statuses.get("CONTAMINATED")
            else "UNSAFE",
            "meaning": LEXIGRAM[1][2],
        },
        {
            "dimension": "resolution",
            "grade": "COMPLETE" if not statuses.get("FAIL") else "PARTIAL",
            "meaning": LEXIGRAM[2][2],
        },
        {
            "dimension": "evidence",
            "grade": "PRESERVED" if not statuses.get("INVALID") else "THIN",
            "meaning": LEXIGRAM[3][2],
        },
        {
            "dimension": "paired_benefit",
            "grade": "RESCUED"
            if "RESCUED" in labels
            else "LEANER"
            if "LEANER" in labels
            else "NO_OBSERVED_GAIN",
            "meaning": LEXIGRAM[4][2],
            "observations": labels,
        },
    ]
    return {
        "ordering": [row[0] for row in LEXIGRAM],
        "grades": grades,
        "policy": "lexicographic-words; unknown-is-not-zero; hard-authority-is-non-compensatory",
    }


def score(
    *, suite_root: Path, results: Path, agents: tuple[str, ...]
) -> dict[str, Any]:
    suite = load_suite(suite_root)
    if not agents or set(agents) - set(suite.agents):
        raise ValueError("select one or both frozen native agents explicitly")
    conditions = {row["id"]: row for row in suite.experiment["conditions"]}
    definitions = suite.trial_definitions()
    selected = {
        row["definition_id"]
        for row in definitions
        if conditions[row["condition_id"]]["agent"] in agents
    }
    expected = 96 * len(agents)
    if len(selected) != expected:
        raise ValueError("selected agents do not cover the frozen v4 suite")
    whole = build_report(
        suite=suite,
        results_root=results,
        selected_definitions=selected,
        require_complete=True,
    )
    families = {}
    for family in FAMILIES:
        tasks = {
            task_id
            for task_id, task in suite.tasks.items()
            if task.get("family") == family
        }
        family_selected = {
            row["definition_id"]
            for row in definitions
            if row["task_id"] in tasks
            and conditions[row["condition_id"]]["agent"] in agents
        }
        family_report = build_report(
            suite=suite,
            results_root=results,
            selected_definitions=family_selected,
            require_complete=True,
        )
        families[family] = {
            "task_ids": sorted(tasks),
            "expected_trials": family_report["expected_trials"],
            "observed_trials": family_report["observed_trials"],
            "status_counts": family_report["status_counts"],
            "paired_assistance": family_report["paired_assistance"],
            "lexigram": _lexigram(family_report),
        }
    return {
        "schema": "agents-cookbook-behavioral-outcomes.v2",
        "selection": {"agents": sorted(agents)},
        "expected_trials": expected,
        "observed_trials": whole["observed_trials"],
        "families": families,
        "lexigram": _lexigram(whole),
        "authority": {
            "overall_winner": None,
            "release_authority": False,
            "comparison": "lexicographic descriptive grades only",
            "numeric_aggregate": None,
            "unknown_policy": "unknown-not-zero",
            "hard_authority_veto": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--agent", action="append", required=True)
    args = parser.parse_args()
    try:
        payload = score(
            suite_root=Path(__file__).resolve().parent,
            results=args.results,
            agents=parse_agent_arguments(args.agent),
        )
    except (ValueError, ReportError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
