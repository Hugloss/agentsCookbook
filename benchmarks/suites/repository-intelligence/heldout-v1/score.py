"""Report complete held-out trials separately for Python and TypeScript."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmarks.harness.report import build_report
from benchmarks.harness.suite import load_suite


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    suite = load_suite(Path(__file__).resolve().parent)
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
        }
        if len(task_ids) != 6 or len(selected) != 108:
            raise ValueError(f"{language}: expected six tasks and 108 frozen trials")
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
            "conditions": report["conditions"],
            "paired_assistance": report["paired_assistance"],
            "agent_profiles": report["agent_profiles"],
            "cross_agent_observations": report["cross_agent_observations"],
        }
    payload = {
        "schema": "agents-cookbook-heldout-observer-outcomes.v1",
        "expected_trials": 216,
        "observed_trials": sum(row["observed_trials"] for row in languages.values()),
        "languages": languages,
        "authority": {
            "overall_winner": None,
            "cross_agent_comparison": "descriptive-only",
            "assistance_comparison": "within-agent-paired-trials",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
