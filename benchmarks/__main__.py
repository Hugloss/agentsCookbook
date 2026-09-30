"""Command-line entry point for reusable empirical benchmark suites."""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from collections.abc import MutableMapping
from pathlib import Path

from benchmarks.harness.campaign import (
    CampaignError,
    campaign_status,
    resolve_campaign_paths,
)
from benchmarks.harness.preflight import preflight_trial
from benchmarks.harness.readiness import check_runtime_readiness
from benchmarks.harness.runtime_authority import (
    RUNTIME_AUTHORITY_ENV_KEYS,
    required_runtime_authority,
)
from benchmarks.harness.report import ReportError, build_report
from benchmarks.harness.runner import run_trial
from benchmarks.harness.selection import (
    SelectionError,
    parse_agent_arguments,
    select_definitions,
)
from benchmarks.harness.suite import load_runtime_suite, load_suite


_BENCHMARK_ENV_KEYS = frozenset(RUNTIME_AUTHORITY_ENV_KEYS)


def _load_benchmark_env(
    path: Path,
    environment: MutableMapping[str, str],
    *,
    require_file: bool,
) -> None:
    if not path.is_file():
        if require_file:
            raise SystemExit(f"benchmark env file does not exist: {path}")
        return
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise SystemExit(f"cannot read benchmark env file {path}: {exc}") from exc
    for line_no, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            key = line.strip()
            if key in _BENCHMARK_ENV_KEYS:
                raise SystemExit(
                    f"{path}:{line_no}: benchmark environment entry needs KEY=VALUE"
                )
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in _BENCHMARK_ENV_KEYS or environment.get(key):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if value:
            environment[key] = value


def _add_selectors(
    command: argparse.ArgumentParser,
    *,
    require_agent: bool = False,
) -> None:
    command.add_argument("--task", action="append", default=[])
    command.add_argument(
        "--agent",
        action="append",
        default=[],
        required=require_agent,
    )
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
    command.add_argument("--harness-root", type=Path, required=True)
    command.add_argument(
        "--env-file",
        type=Path,
        help="explicit benchmark environment file; no file is auto-discovered",
    )
    command.add_argument("--source", type=Path)
    command.add_argument(
        "--codex-auth",
        type=Path,
        help="copy only this auth.json into isolated CODEX_HOME for Codex runs",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uv run --no-project python -m benchmarks"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate-suite")
    validate.add_argument("--suite", type=Path, required=True)

    check = sub.add_parser("check")
    check.add_argument("--suite", type=Path, required=True)
    check.add_argument(
        "--agent",
        action="append",
        default=[],
        help="optional native agent filter; without it, check every suite agent",
    )
    check.add_argument(
        "--env-file",
        type=Path,
        required=True,
        help="explicit benchmark environment file; no file is auto-discovered",
    )

    plan = sub.add_parser("plan")
    plan.add_argument("--suite", type=Path, required=True)
    _add_selectors(plan)

    preflight = sub.add_parser("preflight")
    preflight.add_argument("--suite", type=Path, required=True)
    _add_selectors(preflight, require_agent=True)
    _add_campaign_paths(preflight, execution=True)
    _add_execution_inputs(preflight)

    run = sub.add_parser("run")
    run.add_argument("--suite", type=Path, required=True)
    _add_selectors(run, require_agent=True)
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


def _paths(args, *, need_execution: bool, results_optional: bool = False):
    try:
        return resolve_campaign_paths(
            root=args.root,
            cache=getattr(args, "cache", None),
            work=getattr(args, "work", None),
            results=args.results,
            need_execution=need_execution,
            results_optional=results_optional,
        )
    except CampaignError as exc:
        raise SystemExit(str(exc)) from exc


def _selection_metadata(args, suite, rows) -> dict[str, object]:
    conditions = {
        str(condition["id"]): condition
        for condition in suite.experiment["conditions"]
    }
    bare_control_included = any(
        conditions.get(str(row["condition_id"]), {}).get("subject") == "none"
        for row in rows
    )
    return {
        "tasks": sorted(set(args.task)),
        "agents": sorted(set(args.agent)),
        "subjects": sorted(set(args.subject)),
        "condition": args.condition,
        "bare_control_included": bare_control_included,
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if hasattr(args, "agent"):
        try:
            args.agent = list(parse_agent_arguments(args.agent))
        except SelectionError as exc:
            raise SystemExit(str(exc)) from exc
    suite = (
        load_runtime_suite(args.suite)
        if args.command == "check"
        else load_suite(args.suite)
    )

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

    if args.command == "check":
        _load_benchmark_env(
            args.env_file,
            os.environ,
            require_file=True,
        )
        unknown_agents = sorted(set(args.agent) - set(suite.agents))
        if unknown_agents:
            raise SystemExit(
                "unknown benchmark agent(s): " + ", ".join(unknown_agents)
            )
        authority_rows = [
            {"condition_id": str(condition["id"])}
            for condition in suite.experiment["conditions"]
            if not args.agent or str(condition["agent"]) in args.agent
        ]
        if not authority_rows:
            raise SystemExit("benchmark check has no suite conditions")
        missing = [
            name
            for name in required_runtime_authority(suite, authority_rows)
            if not os.environ.get(name)
        ]
        if missing:
            raise SystemExit(
                "missing explicit benchmark runtime authority: "
                + ", ".join(missing)
                + "; set the value(s) in the file passed with --env-file "
                "or export them explicitly"
            )
        try:
            report = check_runtime_readiness(
                suite,
                agents=tuple(args.agent),
            )
        except (OSError, ValueError) as exc:
            raise SystemExit(f"benchmark runtime check failed: {exc}") from exc
        for item in report.checks:
            print(item.line())
        print(
            "benchmark runtime: READY"
            if report.ready
            else "benchmark runtime: NOT READY"
        )
        return 0 if report.ready else 2

    rows = _select(args, suite)

    if args.command in {"preflight", "run"}:
        if args.env_file is not None:
            _load_benchmark_env(
                args.env_file,
                os.environ,
                require_file=True,
            )
        missing = [
            name
            for name in required_runtime_authority(suite, rows)
            if not os.environ.get(name)
        ]
        if missing:
            raise SystemExit(
                "missing explicit benchmark runtime authority: "
                + ", ".join(missing)
                + "; set the value(s) in the file passed with --env-file "
                "or export them explicitly"
            )

    if args.command == "plan":
        print(json.dumps(rows, indent=2, sort_keys=True))
        return 0

    if args.command == "status":
        paths = _paths(args, need_execution=False)
        assert paths.results is not None
        status = campaign_status(
            suite=suite,
            results_root=paths.results,
            selected_definitions={
                str(row["definition_id"]) for row in rows
            },
        )
        status["paths"] = paths.as_dict()
        status["selection"] = _selection_metadata(args, suite, rows)
        print(json.dumps(status, indent=2, sort_keys=True))
        return 2 if (
            status["conflicting_trials"]
            or status["corrupt_bundles"]
            or status["foreign_bundles"]
        ) else 0

    if args.command == "report":
        paths = _paths(args, need_execution=False)
        assert paths.results is not None
        if not paths.results.is_dir() or not any(paths.results.iterdir()):
            raise SystemExit(
                f"no benchmark receipts in {paths.results}; run the selected suite first"
            )
        try:
            report_data = build_report(
                suite=suite,
                results_root=paths.results,
                require_complete=not args.allow_incomplete,
                selected_definitions={str(row["definition_id"]) for row in rows},
                selection=_selection_metadata(args, suite, rows),
            )
        except ReportError as exc:
            raise SystemExit(
                f"benchmark report unavailable: {exc}; use --allow-incomplete to inspect a partial campaign"
            ) from exc
        print(
            json.dumps(report_data, indent=2, sort_keys=True)
        )
        return 0

    paths = _paths(
        args,
        need_execution=True,
        results_optional=args.command == "preflight",
    )
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
            detail = f": {result.reason}" if result.reason else ""
            print(
                f"{result.task_id} / {result.condition_id}: {result.status}{detail}",
                file=sys.stderr,
                flush=True,
            )
        payload = {
            "paths": paths.as_dict(),
            "selection": _selection_metadata(args, suite, rows),
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
    assert paths.results is not None
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
