"""Command-line entry point for reusable empirical benchmark suites."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmarks.harness.runner import run_trial
from benchmarks.harness.suite import load_suite


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m benchmarks")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate-suite")
    validate.add_argument("--suite", type=Path, required=True)

    plan = sub.add_parser("plan")
    plan.add_argument("--suite", type=Path, required=True)

    run = sub.add_parser("run")
    run.add_argument("--suite", type=Path, required=True)
    run.add_argument("--results", type=Path, required=True)
    run.add_argument("--cache", type=Path, required=True)
    run.add_argument("--work", type=Path, required=True)
    run.add_argument("--harness-root", type=Path, default=Path("."))
    run.add_argument("--source", type=Path)
    run.add_argument(
        "--codex-auth",
        type=Path,
        help="copy only this auth.json into isolated CODEX_HOME for Codex runs",
    )
    run.add_argument("--task")
    run.add_argument("--condition")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    suite = load_suite(args.suite)

    if args.command == "validate-suite":
        print(
            json.dumps(
                {
                    "suite": suite.experiment["suite"],
                    "experiment": suite.experiment["id"],
                    "tasks": len(suite.tasks),
                    "subjects": len(suite.subjects),
                    "agents": len(suite.agents),
                    "trials": len(suite.trial_definitions()),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "plan":
        print(json.dumps(suite.trial_definitions(), indent=2, sort_keys=True))
        return 0

    rows = suite.trial_definitions()
    if args.task:
        rows = [row for row in rows if row["task_id"] == args.task]
    if args.condition:
        rows = [
            row for row in rows if row["condition_id"] == args.condition
        ]
    if not rows:
        raise SystemExit("no trials matched the requested filters")

    results = []
    invalid = False
    for row in rows:
        result = run_trial(
            suite=suite,
            task_id=str(row["task_id"]),
            condition_id=str(row["condition_id"]),
            trial_index=int(row["trial"]),
            harness_root=args.harness_root,
            cache_root=args.cache,
            results_root=args.results,
            work_root=args.work,
            local_source=args.source,
            codex_auth=args.codex_auth,
        )
        results.append(
            {
                "trial_id": result.trial_id,
                "definition_id": result.definition_id,
                "status": result.status,
                "result_dir": str(result.result_dir),
                "reused": result.reused,
            }
        )
        if result.status in {"INCOMPLETE", "INVALID", "CONTAMINATED"}:
            invalid = True

    print(json.dumps(results, indent=2, sort_keys=True))
    return 2 if invalid else 0


if __name__ == "__main__":
    raise SystemExit(main())
