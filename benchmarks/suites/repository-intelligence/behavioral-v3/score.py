"""Score behavioral-v3 without producing a release verdict."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmarks.harness.report import ReportError, build_report
from benchmarks.harness.selection import parse_agent_arguments
from benchmarks.harness.suite import load_suite

FAMILIES = ("post_change", "change_impact", "verification", "dependency_delta")


def score(*, suite_root: Path, results: Path, agents: tuple[str, ...]) -> dict:
    suite = load_suite(suite_root)
    if not agents or set(agents) - set(suite.agents):
        raise ValueError("select one or both frozen native agents explicitly")
    conditions = {row["id"]: row for row in suite.experiment["conditions"]}
    definitions = suite.trial_definitions()
    selected_all = {
        row["definition_id"]
        for row in definitions
        if conditions[row["condition_id"]]["agent"] in agents
    }
    if len(selected_all) != 24 * len(agents):
        raise ValueError("selected agents do not cover the frozen behavioral suite")
    whole = build_report(
        suite=suite,
        results_root=results,
        selected_definitions=selected_all,
        require_complete=True,
    )
    families = {}
    for family in FAMILIES:
        tasks = {task_id for task_id, task in suite.tasks.items() if task.get("family") == family}
        selected = {
            row["definition_id"]
            for row in definitions
            if row["task_id"] in tasks
            and conditions[row["condition_id"]]["agent"] in agents
        }
        if len(tasks) != 2 or len(selected) != 6 * len(agents):
            raise ValueError(f"{family}: expected two tasks and six trials per agent")
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
    return {
        "schema": "agents-cookbook-behavioral-outcomes.v1",
        "selection": {"agents": sorted(agents)},
        "expected_trials": 24 * len(agents),
        "observed_trials": whole["observed_trials"],
        "families": families,
        "authority": {
            "overall_winner": None,
            "release_authority": False,
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
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
