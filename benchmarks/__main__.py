"""Command-line entry point for reusable empirical benchmark suites."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from benchmarks.harness.report import ReportError, build_report
from benchmarks.harness.runner import preflight_trial, run_trial
from benchmarks.harness.selection import SelectionError, select_definitions
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

    preflight = sub.add_parser("preflight")
    preflight.add_argument("--suite", type=Path, required=True)
    preflight.add_argument("--cache", type=Path, required=True)
    preflight.add_argument("--work", type=Path, required=True)
    preflight.add_argument("--source", type=Path)
    preflight.add_argument("--codex-auth", type=Path)

    report = sub.add_parser("report")
    report.add_argument("--suite", type=Path, required=True)
    report.add_argument("--results", type=Path, required=True)
    report.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="report available valid receipts without requiring every frozen definition",
    )

    for command in (plan, run, report, preflight):
        command.add_argument("--task", action="append", default=[])
        command.add_argument("--agent", action="append", default=[])
        command.add_argument("--subject", action="append", default=[])
        command.add_argument("--condition")

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

    try:
        rows = select_definitions(
            suite,
            tasks=tuple(args.task),
            agents=tuple(args.agent),
            subjects=tuple(args.subject),
            condition=args.condition,
        )
    except SelectionError as exc:
        raise SystemExit(str(exc)) from exc

    if args.command == "plan":
        print(json.dumps(rows, indent=2, sort_keys=True))
        return 0

    if args.command == "report":
        if not args.results.is_dir() or not any(args.results.iterdir()):
            raise SystemExit(
                f"no benchmark receipts in {args.results}; run the selected suite first"
            )
        try:
            report_data = build_report(
                suite=suite,
                results_root=args.results,
                require_complete=not args.allow_incomplete,
                selected_definitions={row["definition_id"] for row in rows},
                selection={
                    "tasks": sorted(set(args.task)),
                    "agents": sorted(set(args.agent)),
                    "subjects": sorted(set(args.subject)),
                    "condition": args.condition,
                    "bare_control_included": bool(
                        not args.condition
                        and any(subject != "none" for subject in args.subject)
                    ),
                },
            )
        except ReportError as exc:
            raise SystemExit(
                f"benchmark report unavailable: {exc}; use --allow-incomplete to inspect a partial campaign"
            ) from exc
        print(json.dumps(report_data, indent=2, sort_keys=True))
        return 0

    if args.command == "preflight":
        checked: set[tuple[str, str]] = set()
        results = []
        for row in rows:
            key = (str(row["task_id"]), str(row["condition_id"]))
            if key in checked:
                continue
            checked.add(key)
            result = preflight_trial(
                suite=suite,
                task_id=key[0],
                condition_id=key[1],
                trial_index=int(row["trial"]),
                cache_root=args.cache,
                work_root=args.work,
                local_source=args.source,
                codex_auth=args.codex_auth,
            )
            results.append(vars(result))
            detail = f": {result.reason}" if result.reason else ""
            print(
                f"{result.task_id} / {result.condition_id}: {result.status}{detail}",
                file=sys.stderr,
                flush=True,
            )
        print(json.dumps(results, indent=2, sort_keys=True))
        return 0 if all(row["status"] == "READY" for row in results) else 2

    results = []
    invalid = False
    for row in rows:
        print(
            f"starting {row['task_id']} / {row['condition_id']} trial {row['trial']}",
            file=sys.stderr,
            flush=True,
        )
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
                "reason": result.reason,
            }
        )
        detail = f": {result.reason}" if result.reason else ""
        print(
            f"{row['task_id']} / {row['condition_id']}: {result.status}{detail}",
            file=sys.stderr,
            flush=True,
        )
        if result.status in {"INCOMPLETE", "INVALID", "CONTAMINATED"}:
            invalid = True

    print(json.dumps(results, indent=2, sort_keys=True))
    return 2 if invalid else 0


if __name__ == "__main__":
    raise SystemExit(main())
