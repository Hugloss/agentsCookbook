"""Command-line entry point for reusable empirical benchmark suites."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from benchmarks.harness.campaign import (
    CampaignError,
    campaign_status,
    resolve_campaign_paths,
)
from benchmarks.harness.preflight import preflight_trial
from benchmarks.harness.report import build_report
from benchmarks.harness.runner import run_trial
from benchmarks.harness.selection import SelectionError, select_definitions
from benchmarks.harness.suite import load_suite


def _add_selectors(command: argparse.ArgumentParser) -> None:
    command.add_argument("--task", action="append", default=[])
    command.add_argument("--agent", action="append", default=[])
    command.add_argument("--subject", action="append", default=[])
    command.add_argument("--condition")


def _add_campaign_paths(
    command: argparse.ArgumentParser,
    *,
    execution: bool,
) -> None:
    command.add_argument(
        "--root",
        type=Path,
        help=(
            "campaign root; derives cache/, work/, and results/ "
            "without creating a second campaign manifest"
        ),
    )
    if execution:
        command.add_argument("--cache", type=Path)
        command.add_argument("--work", type=Path)
    command.add_argument("--results", type=Path)


def _add_execution_inputs(command: argparse.ArgumentParser) -> None:
    command.add_argument("--harness-root", type=Path, default=Path("."))
    command.add_argument("--source", type=Path)
    command.add_argument(
        "--codex-auth",
        type=Path,
        help="copy only this auth.json into isolated CODEX_HOME for Codex runs",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m benchmarks")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate-suite")
    validate.add_argument("--suite", type=Path, required=True)

    plan = sub.add_parser("plan")
    plan.add_argument("--suite", type=Path, required=True)
    _add_selectors(plan)

    preflight = sub.add_parser("preflight")
    preflight.add_argument("--suite", type=Path, required=True)
    _add_selectors(preflight)
    _add_campaign_paths(preflight, execution=True)
    _add_execution_inputs(preflight)

    run = sub.add_parser("run")
    run.add_argument("--suite", type=Path, required=True)
    _add_selectors(run)
    _add_campaign_paths(run, execution=True)
    _add_execution_inputs(run)

    status = sub.add_parser("status")
    status.add_argument("--suite", type=Path, required=True)
    _add_selectors(status)
    _add_campaign_paths(status, execution=False)

    report = sub.add_parser("report")
    report.add_argument("--suite", type=Path, required=True)
    _add_selectors(report)
    _add_campaign_paths(report, execution=False)
    report.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="report available valid receipts without requiring every frozen definition",
    )

    return parser


def _select(args, suite):
    try:
        return select_definitions(
            suite,
            tasks=tuple(args.task),
            agents=tuple(args.agent),
            subjects=tuple(args.subject),
            condition=args.condition,
        )
    except SelectionError as exc:
        raise SystemExit(str(exc)) from exc


def _paths(args, *, need_execution: bool):
    try:
        return resolve_campaign_paths(
            root=args.root,
            cache=getattr(args, "cache", None),
            work=getattr(args, "work", None),
            results=args.results,
            need_execution=need_execution,
        )
    except CampaignError as exc:
        raise SystemExit(str(exc)) from exc


def _selection_metadata(args) -> dict[str, object]:
    return {
        "tasks": sorted(set(args.task)),
        "agents": sorted(set(args.agent)),
        "subjects": sorted(set(args.subject)),
        "condition": args.condition,
        "bare_control_included": bool(
            not args.condition
            and any(subject != "none" for subject in args.subject)
        ),
    }


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

    rows = _select(args, suite)

    if args.command == "plan":
        print(json.dumps(rows, indent=2, sort_keys=True))
        return 0

    if args.command == "status":
        paths = _paths(args, need_execution=False)
        status = campaign_status(
            suite=suite,
            results_root=paths.results,
            selected_definitions={
                str(row["definition_id"]) for row in rows
            },
        )
        status["paths"] = paths.as_dict()
        status["selection"] = _selection_metadata(args)
        print(json.dumps(status, indent=2, sort_keys=True))
        return 2 if (
            status["conflicting_trials"]
            or status["corrupt_bundles"]
            or status["foreign_bundles"]
        ) else 0

    if args.command == "report":
        paths = _paths(args, need_execution=False)
        print(
            json.dumps(
                build_report(
                    suite=suite,
                    results_root=paths.results,
                    require_complete=not args.allow_incomplete,
                    selected_definitions={
                        str(row["definition_id"]) for row in rows
                    },
                    selection=_selection_metadata(args),
                ),
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    paths = _paths(args, need_execution=True)
    assert paths.cache is not None
    assert paths.work is not None

    if args.command == "preflight":
        results = []
        counts: Counter[str] = Counter()
        for row in rows:
            result = preflight_trial(
                suite=suite,
                task_id=str(row["task_id"]),
                condition_id=str(row["condition_id"]),
                trial_index=int(row["trial"]),
                harness_root=args.harness_root,
                cache_root=paths.cache,
                work_root=paths.work,
                results_root=paths.results,
                local_source=args.source,
                codex_auth=args.codex_auth,
            )
            value = result.as_dict()
            results.append(value)
            counts[result.status] += 1
        payload = {
            "paths": paths.as_dict(),
            "selection": _selection_metadata(args),
            "summary": dict(sorted(counts.items())),
            "ready": all(
                row["status"] in {"READY", "COMPLETE"}
                for row in results
            ),
            "trials": results,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["ready"] else 2

    results = []
    invalid = False
    for row in rows:
        result = run_trial(
            suite=suite,
            task_id=str(row["task_id"]),
            condition_id=str(row["condition_id"]),
            trial_index=int(row["trial"]),
            harness_root=args.harness_root,
            cache_root=paths.cache,
            results_root=paths.results,
            work_root=paths.work,
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
