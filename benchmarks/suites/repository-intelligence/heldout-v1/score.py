"""Report complete held-out trials separately for Python and TypeScript."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmarks.harness.report import build_report
from benchmarks.harness.selection import SelectionError, parse_agent_arguments
from benchmarks.harness.suite import load_suite


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--agent", action="append", required=True)
    args = parser.parse_args()
    suite = load_suite(Path(__file__).resolve().parent)
    try:
        agents = parse_agent_arguments(args.agent)
    except SelectionError as exc:
        raise SystemExit(str(exc)) from exc
    unknown = sorted(set(agents) - set(suite.agents))
    if unknown:
        raise SystemExit("unknown benchmark agent(s): " + ", ".join(unknown))
    selected_agents = set(agents)
    conditions = {
        str(condition["id"]): condition
        for condition in suite.experiment["conditions"]
    }
    definitions = suite.trial_definitions()
    languages = {}
    for language in ("python", "typescript"):
        task_ids = {
            task_id
            for task_id, task in suite.tasks.items()
            if str(task.get("family", "")).startswith(language + "-")
        }
        selected = {
            str(row["definition_id"])
            for row in definitions
            if row["task_id"] in task_ids
            and conditions[str(row["condition_id"])]["agent"] in selected_agents
        }
        expected = 54 * len(agents)
        if len(task_ids) != 6 or len(selected) != expected:
            raise ValueError(
                f"{language}: expected six tasks and {expected} frozen trials "
                f"for agents {', '.join(agents)}"
            )
        report = build_report(
            suite=suite,
            results_root=args.results,
            selected_definitions=selected,
            require_complete=True,
        )
        languages[language] = {
            "task_ids": sorted(task_ids),
            "expected_trials": report["expected_trials"],
            "observed_trials": report["observed_trials"],
            "status_counts": report["status_counts"],
            "campaign_qualification": report["campaign_qualification"],
            "conditions": report["conditions"],
            "paired_assistance": report["paired_assistance"],
            "agent_profiles": report["agent_profiles"],
            "cross_agent_observations": report["cross_agent_observations"],
        }
    payload = {
        "schema": "agents-cookbook-heldout-observer-outcomes.v3",
        "expected_trials": sum(row["expected_trials"] for row in languages.values()),
        "observed_trials": sum(row["observed_trials"] for row in languages.values()),
        "languages": languages,
        "selection": {"agents": sorted(agents)},
        "campaign_qualification": {
            "status": (
                "QUALIFIED"
                if all(
                    row["campaign_qualification"]["status"] == "QUALIFIED"
                    for row in languages.values()
                )
                else "NOT_QUALIFIED"
            ),
            "languages": {
                language: row["campaign_qualification"]
                for language, row in sorted(languages.items())
            },
        },
        "authority": {
            "overall_winner": None,
            "cross_agent_comparison": (
                "descriptive-only"
                if len(agents) > 1
                else "not-applicable-single-agent-selection"
            ),
            "assistance_comparison": "within-agent-paired-trials",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
