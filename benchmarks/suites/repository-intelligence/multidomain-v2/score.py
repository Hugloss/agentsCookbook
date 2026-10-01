"""Score complete multidomain agent trials without a release verdict."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmarks.evidence import load_cases
from benchmarks.harness.report import ReportError, build_report
from benchmarks.harness.selection import parse_agent_arguments
from benchmarks.harness.suite import load_suite


FAMILIES = ("logs", "splunk", "dependencies", "semantics", "identities", "code_owners")


def score(*, suite_root: Path, results: Path, agents: tuple[str, ...]) -> dict:
    suite = load_suite(suite_root)
    evidence_cases = load_cases(suite_root / "evidence.json")
    reviewed = sum(case["review"]["state"] == "approved" for case in evidence_cases)
    if not agents or set(agents) - set(suite.agents):
        raise ValueError("select one or both frozen native agents explicitly")
    conditions = {row["id"]: row for row in suite.experiment["conditions"]}
    definitions = suite.trial_definitions()
    all_selected = {
        row["definition_id"]
        for row in definitions
        if conditions[row["condition_id"]]["agent"] in agents
    }
    if len(all_selected) != 108 * len(agents):
        raise ValueError("selected agents do not cover the frozen six-arm suite")
    whole = build_report(
        suite=suite,
        results_root=results,
        selected_definitions=all_selected,
        require_complete=True,
    )
    families = {}
    for family in FAMILIES:
        tasks = {
            task_id
            for task_id, task in suite.tasks.items()
            if task.get("family") == family
        }
        selected = {
            row["definition_id"]
            for row in definitions
            if row["task_id"] in tasks
            and conditions[row["condition_id"]]["agent"] in agents
        }
        if len(tasks) != 6 or len(selected) != 18 * len(agents):
            raise ValueError(f"{family}: expected six tasks and 18 trials per agent")
        report = build_report(
            suite=suite,
            results_root=results,
            selected_definitions=selected,
            require_complete=True,
        )
        families[family] = {
            "task_ids": sorted(tasks),
            "expected_trials": report["expected_trials"],
            "observed_trials": report["observed_trials"],
            "status_counts": report["status_counts"],
            "conditions": report["conditions"],
            "paired_assistance": report["paired_assistance"],
        }
    valid_outcomes = {"PASS", "FAIL", "NO_QUALIFYING_DEFECT"}
    complete_outcomes = all(
        set(row["status_counts"]).issubset(valid_outcomes) for row in families.values()
    )
    return {
        "schema": "agents-cookbook-multidomain-observer-outcomes.v1",
        "selection": {"agents": sorted(agents)},
        "expected_trials": 108 * len(agents),
        "observed_trials": whole["observed_trials"],
        "families": families,
        "authority": {
            "overall_winner": None,
            "release_authority": False,
            "corpus_review_state": "approved" if reviewed == 60 else "draft",
            "reviewed_cases": reviewed,
            "complete_valid_outcomes": complete_outcomes,
            "paired_assistance_scope": "within-agent-valid-outcomes-only",
            "cross_agent_comparison": "descriptive-only",
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
    except (ValueError, ReportError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
