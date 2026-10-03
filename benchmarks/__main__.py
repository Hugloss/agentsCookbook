"""Command-line entry point for reusable empirical benchmark suites."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path

from benchmarks.config import BenchmarkConfig, BenchmarkConfigError
from benchmarks.diagnostic import DiagnosticError, prepare_diagnostic_suite
from benchmarks.harness.campaign import (
    CampaignError,
    campaign_status,
    resolve_campaign_paths,
)
from benchmarks.harness.campaign_authority import (
    CampaignAuthorityError,
    admit_campaign,
    audit_campaign,
    read_campaign,
    verify_saved_campaign,
)
from benchmarks.harness.preflight import preflight_trial
from benchmarks.harness.decision_evidence import build_decision_evidence
from benchmarks.harness.oracle_reviews import (
    OracleReviewError,
    oracle_review_guide,
    oracle_reviews_declared,
    validate_oracle_reviews,
)
from benchmarks.harness.oracle_review_runner import run_pending_oracle_reviews
from benchmarks.harness.readiness import check_runtime_readiness
from benchmarks.harness.runtime_authority import required_runtime_authority
from benchmarks.harness.report import ReportError, build_report
from benchmarks.harness.runner import (
    TrialRunnerError,
    reuse_completed_trial,
    run_trial,
)
from benchmarks.harness.run_store import (
    RunStoreError,
    active_definition,
    active_trial,
    exclusive_store,
    list_saved_runs,
    prepare_saved_run,
    select_saved_run,
)
from benchmarks.harness.live_console import (
    LiveCampaignProgress,
    LiveTaskMatrix,
    TrialHeartbeat,
    render_campaign_admission,
    render_trial_failure,
)
from benchmarks.harness.selection import (
    SelectionError,
    parse_agent_arguments,
    select_definitions,
)
from benchmarks.harness.suite import load_runtime_suite, load_suite
from scripts.agent_economics.bounded_process import retain_lock_in_subprocesses


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
            "store of numbered campaigns; defaults to BENCHMARK_CAMPAIGN_ROOT"
        ),
    )
    if execution:
        command.add_argument("--cache", type=Path)
        command.add_argument("--work", type=Path)
    command.add_argument("--results", type=Path)
    command.add_argument("--run-id", help="select an older numbered run or legacy")


def _add_execution_inputs(command: argparse.ArgumentParser) -> None:
    command.add_argument("--harness-root", type=Path)
    command.add_argument(
        "--env-file",
        type=Path,
        required=True,
        help="explicit benchmark environment file; no file is auto-discovered",
    )
    command.add_argument("--source", type=Path)
    command.add_argument(
        "--codex-auth",
        type=Path,
        help="copy only this auth.json into isolated CODEX_HOME for Codex runs",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="uv run --no-project python -m benchmarks")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate-suite")
    validate.add_argument("--suite", type=Path, required=True)

    diagnostic = sub.add_parser("diagnostic-prepare")
    diagnostic.add_argument("--suite", type=Path, required=True)
    diagnostic.add_argument("--score", type=Path, required=True)
    diagnostic.add_argument("--source-results", type=Path, required=True)
    diagnostic.add_argument("--output-suite", type=Path, required=True)
    diagnostic.add_argument("--include-task", action="append", default=[])

    reviews = sub.add_parser("oracle-review-check")
    reviews.add_argument("--suite", type=Path, required=True)
    reviews.add_argument("--require-complete", action="store_true")

    review = sub.add_parser("oracle-review")
    review.add_argument("--suite", type=Path, required=True)
    review.add_argument("--execute", action="store_true")
    review.add_argument("--cache", type=Path)

    check = sub.add_parser("check")
    check.add_argument("--suite", type=Path)
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
    preflight.add_argument("--suite", type=Path)
    _add_selectors(preflight)
    _add_campaign_paths(preflight, execution=True)
    _add_execution_inputs(preflight)

    audit = sub.add_parser("campaign-audit")
    audit.add_argument("--suite", type=Path)
    _add_selectors(audit)
    _add_campaign_paths(audit, execution=True)
    _add_execution_inputs(audit)

    prepare = sub.add_parser("prepare")
    prepare.add_argument("--suite", type=Path)
    _add_selectors(prepare)
    _add_campaign_paths(prepare, execution=True)
    _add_execution_inputs(prepare)
    prepare.add_argument("--new", action="store_true", required=True)

    run = sub.add_parser("run")
    run.add_argument("--suite", type=Path)
    _add_selectors(run)
    _add_campaign_paths(run, execution=True)
    _add_execution_inputs(run)
    mode = run.add_mutually_exclusive_group(required=True)
    mode.add_argument("--auto", action="store_true")
    mode.add_argument("--new", action="store_true")
    mode.add_argument("--resume", action="store_true")

    runs = sub.add_parser("runs")
    runs.add_argument("--env-file", type=Path)
    runs.add_argument("--root", type=Path)

    status = sub.add_parser("status")
    status.add_argument("--suite", type=Path)
    status.add_argument("--env-file", type=Path)
    _add_selectors(status)
    _add_campaign_paths(status, execution=False)
    status.add_argument("--require-qualified", action="store_true")

    report = sub.add_parser("report")
    report.add_argument("--suite", type=Path)
    report.add_argument("--env-file", type=Path)
    _add_selectors(report)
    _add_campaign_paths(report, execution=False)
    report.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="report available valid receipts without requiring every frozen definition",
    )

    score = sub.add_parser("score")
    score.add_argument("--env-file", type=Path, required=True)
    score.add_argument("--suite", type=Path)
    score.add_argument("--root", type=Path)
    score.add_argument("--agent", action="append", default=[])
    score.add_argument("--score-script", type=Path)
    score.add_argument("--output", type=Path)
    score.add_argument("--run-id")

    regrade_score = sub.add_parser("regrade-score")
    regrade_score.add_argument("--suite", type=Path, required=True)
    regrade_score.add_argument("--source-results", type=Path, required=True)
    regrade_score.add_argument("--output", type=Path, required=True)
    regrade_score.add_argument("--agent", action="append", required=True)

    return parser


def _resolve_config(args: argparse.Namespace) -> BenchmarkConfig:
    try:
        config = BenchmarkConfig.load(getattr(args, "env_file", None))
        config.require_for(args.command)
        if hasattr(args, "suite") and args.suite is None:
            args.suite = config.path("BENCHMARK_SUITE_PATH")
        if (
            hasattr(args, "root")
            and args.root is None
            and getattr(args, "results", None) is None
        ):
            args.root = config.path("BENCHMARK_CAMPAIGN_ROOT")
        if hasattr(args, "harness_root") and args.harness_root is None:
            args.harness_root = config.path("BENCHMARK_HARNESS_REPO_ROOT")
        if hasattr(args, "agent") and not args.agent and args.command != "check":
            args.agent = list(config.agents())
        if args.command == "score":
            args.score_script = args.score_script or config.path(
                "BENCHMARK_SCORE_SCRIPT_PATH"
            )
            args.output = args.output or config.path("BENCHMARK_SCORE_OUTPUT_PATH")
        if hasattr(args, "suite") and args.suite is None:
            raise BenchmarkConfigError("BENCHMARK_SUITE_PATH or --suite is required")
        if (
            args.command in {"preflight", "campaign-audit", "prepare", "run", "report", "score"}
            and not args.agent
        ):
            raise BenchmarkConfigError("BENCHMARK_AGENT or --agent is required")
        if (
            args.command in {"preflight", "campaign-audit", "prepare", "run"}
            and args.harness_root is None
        ):
            raise BenchmarkConfigError(
                "BENCHMARK_HARNESS_REPO_ROOT or --harness-root is required"
            )
        return config
    except BenchmarkConfigError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc


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
        root = args.root
        run_id = None
        if root is not None:
            if any(
                value is not None
                for value in (getattr(args, "cache", None), getattr(args, "work", None), args.results)
            ):
                raise CampaignError("--root cannot be combined with --cache, --work, or --results")
            selected_run = select_saved_run(root, getattr(args, "run_id", None))
            root = selected_run.root
            run_id = selected_run.run_id
        elif getattr(args, "run_id", None) is not None:
            raise CampaignError("--run-id requires --root")
        paths = resolve_campaign_paths(
            root=root,
            cache=getattr(args, "cache", None),
            work=getattr(args, "work", None),
            results=args.results,
            need_execution=need_execution,
            results_optional=results_optional,
        )
        return replace(paths, run_id=run_id)
    except (CampaignError, RunStoreError) as exc:
        raise SystemExit(str(exc)) from exc


def _reports_dir(run_root: Path) -> Path:
    return run_root / "reports"


def _write_derived_json(run_root: Path, filename: str, payload: object) -> Path:
    """Atomically refresh one small, shareable derived report."""
    directory = _reports_dir(run_root)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / filename
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        dir=directory,
    )
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
        directory_fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return destination


def _selection_metadata(args, suite, rows) -> dict[str, object]:
    conditions = {
        str(condition["id"]): condition for condition in suite.experiment["conditions"]
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


def _selected_agent_ids(suite, rows: list[dict[str, object]]) -> list[str]:
    conditions = {
        str(condition["id"]): condition
        for condition in suite.experiment["conditions"]
    }
    return sorted(
        {
            str(conditions[str(row["condition_id"])]["agent"])
            for row in rows
        }
    )


def _assert_saved_run_agents(
    saved: SavedRun,
    agents: list[str] | tuple[str, ...] | set[str],
) -> dict[str, object]:
    """Bind resume/scoring to the campaign's frozen agent population."""
    manifest = read_campaign(saved.root / "results")
    frozen_agents = sorted(str(value) for value in manifest.get("agents", {}))
    selected_agents = sorted(set(str(value) for value in agents))
    if frozen_agents != selected_agents:
        raise RunStoreError(
            f"saved run {saved.run_id} agent selection does not match "
            f"BENCHMARK_AGENT (frozen={frozen_agents}, "
            f"selected={selected_agents}); use the frozen agent set to resume "
            "or score, or start a new run"
        )
    return manifest


def _assert_saved_run_selection(
    saved: SavedRun,
    *,
    suite,
    rows: list[dict[str, object]],
) -> dict[str, object]:
    """Fail before admission when selected tasks/conditions differ from the run."""
    selected_agents = _selected_agent_ids(suite, rows)
    manifest = _assert_saved_run_agents(saved, selected_agents)
    selected = {str(row["definition_id"]) for row in rows}
    frozen = set(manifest["selected_definitions"])
    if frozen != selected:
        raise RunStoreError(
            f"saved run {saved.run_id} frozen definition selection does not "
            "match the current benchmark selection; use the same task/subject/"
            "condition selection to resume, or use make benchmark-new"
        )
    return manifest


def _guard_automatic_start(
    root: Path,
    *,
    suite,
    rows: list[dict[str, object]],
) -> None:
    """Require an explicit choice only for an unfinished matching latest run."""
    saved_runs = list_saved_runs(root)
    if not saved_runs:
        return

    latest = saved_runs[-1]
    manifest = read_campaign(latest.root / "results")
    selected = {str(row["definition_id"]) for row in rows}
    frozen = set(manifest["selected_definitions"])
    if frozen != selected:
        print(
            f"BENCHMARK auto | latest run {latest.run_id} has a different "
            "frozen selection; starting a new run",
            file=sys.stderr,
            flush=True,
        )
        return

    status = campaign_status(
        suite=suite,
        results_root=latest.root / "results",
        selected_definitions=selected,
    )
    if status["complete"]:
        return

    raise RunStoreError(
        f"saved run {latest.run_id} is unfinished "
        f"({status['complete_trials']}/{status['expected_trials']} verified, "
        f"{status['pending_trials']} pending, "
        f"{status['interrupted_trials']} interrupted); choose explicitly: "
        "make benchmark-resume or make benchmark-new"
    )


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    explicit_score_output = getattr(args, "output", None) is not None
    if args.command == "oracle-review-check":
        suite = load_suite(args.suite)
        try:
            result = validate_oracle_reviews(
                suite,
                require_complete=args.require_complete,
            )
        except OracleReviewError as exc:
            raise SystemExit(f"oracle review unavailable: {exc}") from exc
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["complete"] or not args.require_complete else 2
    if args.command == "oracle-review":
        suite = load_suite(args.suite)
        try:
            if args.execute:
                result = run_pending_oracle_reviews(
                    suite,
                    cache_root=args.cache,
                )
                print(json.dumps(result, indent=2, sort_keys=True))
                if not result["complete"]:
                    print(
                        "Next: make benchmark-oracle-review-check",
                        file=sys.stderr,
                    )
                return 0
            print(oracle_review_guide(suite))
        except OracleReviewError as exc:
            raise SystemExit(f"oracle review unavailable: {exc}") from exc
        return 0
    if args.command == "diagnostic-prepare":
        try:
            evidence = prepare_diagnostic_suite(
                source_suite=args.suite,
                score_path=args.score,
                source_results=args.source_results,
                destination=args.output_suite,
                include_tasks=set(args.include_task),
            )
        except (DiagnosticError, OSError, ValueError) as exc:
            raise SystemExit(f"diagnostic suite unavailable: {exc}") from exc
        print(json.dumps(evidence, indent=2, sort_keys=True))
        return 0
    if args.command == "regrade-score":
        script = args.suite.resolve() / "score.py"
        if not script.is_file():
            raise SystemExit(f"selected suite has no score script: {script}")
        invocation = [
            sys.executable,
            str(script),
            "--regrade-source-results",
            str(args.source_results),
            "--output",
            str(args.output),
        ]
        for agent in args.agent:
            invocation.extend(("--agent", agent))
        environment = dict(os.environ)
        project_root = str(Path(__file__).resolve().parents[1])
        environment["PYTHONPATH"] = os.pathsep.join(
            filter(None, (project_root, environment.get("PYTHONPATH", "")))
        )
        return subprocess.run(invocation, env=environment, check=False).returncode
    config = _resolve_config(args)
    runtime_source = config.runtime_environment()
    if hasattr(args, "agent"):
        try:
            args.agent = list(parse_agent_arguments(args.agent))
        except SelectionError as exc:
            raise SystemExit(str(exc)) from exc
    if args.command == "runs":
        if args.root is None:
            raise SystemExit("provide --root or BENCHMARK_CAMPAIGN_ROOT")
        try:
            saved = list_saved_runs(args.root)
        except RunStoreError as exc:
            raise SystemExit(str(exc)) from exc
        print(json.dumps({
            "latest": saved[-1].run_id if saved else None,
            "runs": [{"run_id": run.run_id, "root": str(run.root)} for run in saved],
        }, indent=2, sort_keys=True))
        return 0
    if args.command == "score":
        assert args.root is not None
        assert args.output is not None
        assert args.score_script is not None
        script = args.score_script.resolve()
        if not script.is_file():
            raise SystemExit(f"ERROR: benchmark score script does not exist: {script}")
        if script.parent != args.suite.resolve():
            raise SystemExit(
                f"ERROR: benchmark score script must belong to selected suite: {args.suite}"
            )
        try:
            saved = select_saved_run(args.root, args.run_id)
            _assert_saved_run_agents(saved, args.agent)
        except (RunStoreError, CampaignAuthorityError) as exc:
            raise SystemExit(str(exc)) from exc
        if not explicit_score_output:
            if args.output.is_absolute() or len(args.output.parts) != 1:
                raise SystemExit(
                    "BENCHMARK_SCORE_OUTPUT_PATH must be a filename within "
                    "the selected run's reports directory"
                )
            args.output = _reports_dir(saved.root) / args.output
            args.output.parent.mkdir(parents=True, exist_ok=True)
        invocation = [
            sys.executable,
            str(script),
            "--results",
            str(saved.root / "results"),
            "--output",
            str(args.output),
        ]
        for agent in args.agent:
            invocation.extend(("--agent", agent))
        environment = dict(runtime_source)
        project_root = str(Path(__file__).resolve().parents[1])
        environment["PYTHONPATH"] = os.pathsep.join(
            filter(None, (project_root, environment.get("PYTHONPATH", "")))
        )
        return subprocess.run(invocation, env=environment, check=False).returncode
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
        unknown_agents = sorted(set(args.agent) - set(suite.agents))
        if unknown_agents:
            raise SystemExit("unknown benchmark agent(s): " + ", ".join(unknown_agents))
        authority_rows = [
            {"condition_id": str(condition["id"])}
            for condition in suite.experiment["conditions"]
            if not args.agent or str(condition["agent"]) in args.agent
        ]
        if not authority_rows:
            raise SystemExit("benchmark check has no suite conditions")
        required = required_runtime_authority(suite, authority_rows)
        try:
            config.require(*required)
        except BenchmarkConfigError as exc:
            raise SystemExit(f"ERROR: {exc}") from exc
        try:
            report = check_runtime_readiness(
                suite,
                agents=tuple(args.agent),
                source=runtime_source,
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

    if args.command in {"preflight", "campaign-audit", "prepare", "run"}:
        try:
            config.require(*required_runtime_authority(suite, rows))
        except BenchmarkConfigError as exc:
            raise SystemExit(f"ERROR: {exc}") from exc

    if args.command == "plan":
        print(json.dumps(rows, indent=2, sort_keys=True))
        return 0

    if args.command == "status":
        paths = _paths(args, need_execution=False)
        assert paths.results is not None
        status = campaign_status(
            suite=suite,
            results_root=paths.results,
            selected_definitions={str(row["definition_id"]) for row in rows},
            active_definition=(
                active_definition(args.root, paths.run_id)
                if args.root is not None and paths.run_id is not None
                else None
            ),
        )
        status["paths"] = paths.as_dict()
        status["run_id"] = paths.run_id
        status["selection"] = _selection_metadata(args, suite, rows)
        if paths.root is not None:
            status["paths"]["reports"] = str(_reports_dir(paths.root))
            _write_derived_json(paths.root, "status.json", status)
        print(json.dumps(status, indent=2, sort_keys=True))
        return (
            2
            if (
                status["conflicting_trials"]
                or status["corrupt_bundles"]
                or status["foreign_bundles"]
                or (args.require_qualified and not status["qualified"])
            )
            else 0
        )

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
        report_data["run_id"] = paths.run_id
        if paths.root is not None:
            report_data["reports_dir"] = str(_reports_dir(paths.root))
            _write_derived_json(paths.root, "report.json", report_data)
            decision = build_decision_evidence(report_data)
            decision["run_id"] = paths.run_id
            _write_derived_json(paths.root, "decision-evidence.json", decision)
        print(json.dumps(report_data, indent=2, sort_keys=True))
        return 0

    if args.command in {"prepare", "run"}:
        if args.root is None or any(
            value is not None for value in (args.cache, args.work, args.results)
        ):
            raise SystemExit("prepare/run requires --root or BENCHMARK_CAMPAIGN_ROOT without separate paths")
        if (args.command == "prepare" or args.new) and args.run_id is not None:
            raise SystemExit("--run-id can only be used with run --resume")
        try:
            with exclusive_store(args.root) as lock_fd, retain_lock_in_subprocesses(lock_fd):
                admission_started = time.monotonic()

                def on_admission_progress(event):
                    print(
                        render_campaign_admission(
                            event,
                            elapsed=time.monotonic() - admission_started,
                        ),
                        file=sys.stderr,
                        flush=True,
                    )

                if args.command == "run" and args.auto:
                    _guard_automatic_start(args.root, suite=suite, rows=rows)
                create_new = args.command == "prepare" or args.new or args.auto
                if create_new:
                    saved, campaign = prepare_saved_run(
                        args.root,
                        lambda staged: admit_campaign(
                            suite=suite,
                            rows=rows,
                            results_root=staged / "results",
                            harness_root=args.harness_root,
                            cache_root=staged / "cache",
                            work_root=staged / "work",
                            local_source=args.source,
                            codex_auth=args.codex_auth,
                            source=runtime_source,
                            on_progress=on_admission_progress,
                        ),
                    )
                else:
                    saved = select_saved_run(args.root, args.run_id)
                    _assert_saved_run_selection(saved, suite=suite, rows=rows)
                    resume_started = time.monotonic()
                    campaign = verify_saved_campaign(
                        suite=suite,
                        rows=rows,
                        results_root=saved.root / "results",
                        harness_root=args.harness_root,
                    )
                    print(
                        "RESUME campaign authority | verified | "
                        f"{int(round((time.monotonic() - resume_started) * 1000))}ms",
                        file=sys.stderr,
                        flush=True,
                    )
                if args.command == "prepare":
                    print(json.dumps({
                        "run_id": saved.run_id,
                        "root": str(saved.root),
                        "campaign_id": campaign["campaign_id"],
                    }, indent=2, sort_keys=True))
                    return 0
                paths = resolve_campaign_paths(
                    root=saved.root, cache=None, work=None, results=None,
                    need_execution=True,
                )
                paths = replace(paths, run_id=saved.run_id)
                return _execute_run(
                    args,
                    suite,
                    rows,
                    paths,
                    campaign,
                    runtime_source,
                    config,
                )
        except (RunStoreError, CampaignAuthorityError, OracleReviewError) as exc:
            raise SystemExit(f"benchmark run unavailable: {exc}") from exc

    paths = _paths(
        args,
        need_execution=True,
        results_optional=args.command in {"preflight", "campaign-audit"},
    )
    assert paths.cache is not None
    assert paths.work is not None

    if args.command == "campaign-audit":
        try:
            review = (
                validate_oracle_reviews(suite, require_complete=False)
                if oracle_reviews_declared(suite)
                else None
            )
            authority = audit_campaign(
                suite=suite,
                rows=rows,
                results_root=paths.results,
                harness_root=args.harness_root,
                cache_root=paths.cache,
                work_root=paths.work,
                local_source=args.source,
                codex_auth=args.codex_auth,
                source=runtime_source,
            )
        except (CampaignAuthorityError, OracleReviewError, OSError) as exc:
            raise SystemExit(f"campaign audit failed: {exc}") from exc
        print(
            json.dumps(
                {
                    "audit": "model-free; no campaign authority published",
                    "selected_definitions": len(authority["selected_definitions"]),
                    "task_conditions": sum(
                        len(x) for x in authority["task_conditions"].values()
                    ),
                    "task_inputs": len(authority["task_inputs"]),
                    "oracle_review": review,
                    "ready_for_campaign": review is None or review["complete"],
                    "paths": paths.as_dict(),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if review is None or review["complete"] else 2

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
                source=runtime_source,
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
            "ready": all(row["status"] in {"READY", "COMPLETE"} for row in results),
            "trials": results,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["ready"] else 2

    raise SystemExit(f"unsupported benchmark command: {args.command}")


def _persist_completed_run_reports(
    *,
    args,
    config: BenchmarkConfig,
    suite,
    rows,
    paths,
    runtime_source,
    final_status: dict[str, object],
) -> dict[str, Path]:
    """Persist derived artifacts after final campaign verification."""
    assert paths.root is not None
    assert paths.results is not None

    selection = _selection_metadata(args, suite, rows)
    reports_dir = _reports_dir(paths.root)

    status_payload = dict(final_status)
    status_payload["paths"] = paths.as_dict()
    status_payload["paths"]["reports"] = str(reports_dir)
    status_payload["run_id"] = paths.run_id
    status_payload["selection"] = selection
    status_path = _write_derived_json(paths.root, "status.json", status_payload)

    report_data = build_report(
        suite=suite,
        results_root=paths.results,
        require_complete=True,
        selected_definitions={str(row["definition_id"]) for row in rows},
        selection=selection,
    )
    report_data["run_id"] = paths.run_id
    report_data["reports_dir"] = str(reports_dir)
    report_path = _write_derived_json(paths.root, "report.json", report_data)

    decision_data = build_decision_evidence(report_data)
    decision_data["run_id"] = paths.run_id
    decision_path = _write_derived_json(
        paths.root,
        "decision-evidence.json",
        decision_data,
    )

    score_script = config.path("BENCHMARK_SCORE_SCRIPT_PATH") or (
        suite.root / "score.py"
    )
    score_output = config.path("BENCHMARK_SCORE_OUTPUT_PATH") or Path("score.json")
    if score_script is None or not score_script.is_file():
        raise ReportError(f"benchmark score script does not exist: {score_script}")
    if score_script.resolve().parent != suite.root.resolve():
        raise ReportError(
            f"benchmark score script must belong to selected suite: {suite.root}"
        )
    if score_output.is_absolute() or len(score_output.parts) != 1:
        raise ReportError(
            "BENCHMARK_SCORE_OUTPUT_PATH must be a filename within "
            "the selected run's reports directory"
        )
    score_path = reports_dir / score_output
    score_path.parent.mkdir(parents=True, exist_ok=True)
    invocation = [
        sys.executable,
        str(score_script),
        "--results",
        str(paths.results),
        "--output",
        str(score_path),
    ]
    for agent in args.agent:
        invocation.extend(("--agent", agent))
    environment = dict(runtime_source)
    project_root = str(Path(__file__).resolve().parents[1])
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (project_root, environment.get("PYTHONPATH", "")))
    )
    completed = subprocess.run(
        invocation,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise ReportError(
            "benchmark score generation failed"
            + (f": {detail}" if detail else "")
        )
    if not score_path.is_file():
        raise ReportError("benchmark score generation produced no output")

    return {
        "status": status_path,
        "report": report_path,
        "decision_evidence": decision_path,
        "score": score_path,
    }


def _execute_run(args, suite, rows, paths, campaign, runtime_source, config) -> int:
    results = []
    assert paths.results is not None
    live_matrix = LiveTaskMatrix(suite, rows)
    run_started = time.monotonic()
    conditions = {
        str(condition["id"]): condition
        for condition in suite.experiment["conditions"]
    }
    selected_definitions = {str(row["definition_id"]) for row in rows}
    initial_status = campaign_status(
        suite=suite,
        results_root=paths.results,
        selected_definitions=selected_definitions,
    )
    live_progress = LiveCampaignProgress(suite, rows, initial_status)
    initial_rows = {
        str(item["definition_id"]): item
        for item in initial_status["rows"]
    }
    unresolved = int(initial_status.get("unresolved_outcome_trials", 0))
    qualification_detail = (
        f" | qualification BLOCKED | unresolved {unresolved} "
        f"{'outcome' if unresolved == 1 else 'outcomes'} | "
        "continuing diagnostic evidence"
        if unresolved
        else ""
    )
    print(
        f"RUN {paths.run_id} ({paths.root}) | CAMPAIGN {len(rows)} trials | "
        f"verified {initial_status['complete_trials']} | "
        f"pending {initial_status['pending_trials']} | "
        f"interrupted {initial_status['interrupted_trials']} | "
        "completed receipts will be reused; interrupted launches will be "
        "preserved and retried as numbered attempts"
        f"{qualification_detail}",
        file=sys.stderr,
        flush=True,
    )
    for row in rows:
        print(
            live_progress.start_line(
                row,
                elapsed=time.monotonic() - run_started,
            ),
            file=sys.stderr,
            flush=True,
        )
        trial_started = time.monotonic()
        heartbeat = TrialHeartbeat(
            progress=live_progress,
            row=row,
            run_started=run_started,
            emit=lambda line: print(line, file=sys.stderr, flush=True),
        )
        try:
            frozen_status = initial_rows.get(str(row["definition_id"]))
            if (
                isinstance(frozen_status, dict)
                and frozen_status.get("state") == "COMPLETE"
            ):
                trial_ids = frozen_status.get("trial_ids")
                if (
                    not isinstance(trial_ids, list)
                    or len(trial_ids) != 1
                    or not isinstance(trial_ids[0], str)
                ):
                    raise TrialRunnerError(
                        "completed campaign row has invalid trial identity"
                    )
                result = reuse_completed_trial(
                    results_root=paths.results,
                    definition_id=str(row["definition_id"]),
                    trial_id=trial_ids[0],
                )
            else:
                with heartbeat, active_trial(
                    args.root,
                    paths.run_id,
                    str(row["definition_id"]),
                ):
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
                        source=runtime_source,
                        campaign=campaign,
                        on_progress=heartbeat.update_stage,
                    )
            receipt = json.loads(
                (result.result_dir / "result.json").read_text(encoding="utf-8")
            )
            summary = live_matrix.record(row, receipt)
        except Exception as exc:
            print(
                live_progress.abort_line(
                    row,
                    stage=heartbeat.stage,
                    elapsed=time.monotonic() - run_started,
                    error=exc,
                ),
                file=sys.stderr,
                flush=True,
            )
            try:
                observed = campaign_status(
                    suite=suite,
                    results_root=paths.results,
                    selected_definitions=selected_definitions,
                )
                print(
                    f"CAMPAIGN verified {observed['complete_trials']}/{len(rows)} | "
                    f"pending {observed['pending_trials']} | "
                    f"interrupted {observed['interrupted_trials']} | "
                    f"qualified {observed['qualified']}",
                    file=sys.stderr,
                    flush=True,
                )
            except Exception as status_exc:
                print(
                    f"CAMPAIGN status unavailable after abort: {status_exc}",
                    file=sys.stderr,
                    flush=True,
                )
            if isinstance(exc, (TrialRunnerError, ReportError, CampaignError, OSError, ValueError)):
                return 2
            raise
        results.append(
            {
                "trial_id": result.trial_id,
                "definition_id": result.definition_id,
                "status": result.status,
                "result_dir": str(result.result_dir),
                "reused": result.reused,
                "recovered": result.recovered,
                "reason": result.reason,
                "stage": result.stage,
                "reason_code": result.reason_code,
                "diagnostic": result.diagnostic,
            }
        )
        detail = f": {result.reason}" if result.reason else ""
        print(
            f"{row['task_id']} / {row['condition_id']}: {result.status}{detail}",
            file=sys.stderr,
            flush=True,
        )
        condition = conditions[str(row["condition_id"])]
        failure = render_trial_failure(
            row=row,
            subject=str(condition["subject"]),
            result=result,
            receipt=receipt,
        )
        if failure is not None:
            print(failure, file=sys.stderr, flush=True)
        print(
            live_progress.finish_line(
                result,
                elapsed=time.monotonic() - run_started,
                trial_seconds=time.monotonic() - trial_started,
            ),
            file=sys.stderr,
            flush=True,
        )
        if summary is not None:
            print(summary, file=sys.stderr, flush=True)

    try:
        final_status = campaign_status(
            suite=suite,
            results_root=paths.results,
            selected_definitions=selected_definitions,
        )
    except Exception as exc:
        print(
            f"ABORT final campaign verification | processed {len(results)}/{len(rows)} | {exc}",
            file=sys.stderr,
            flush=True,
        )
        print(json.dumps(results, indent=2, sort_keys=True))
        return 2
    print(
        f"RUN SUMMARY processed {len(results)}/{len(rows)} | "
        f"verified {final_status['complete_trials']}/{len(rows)} | "
        f"outcomes {json.dumps(final_status['outcomes'], sort_keys=True)} | "
        f"qualified {final_status['qualified']} | "
        f"run elapsed {int(time.monotonic() - run_started)}s",
        file=sys.stderr,
        flush=True,
    )
    try:
        report_paths = _persist_completed_run_reports(
            args=args,
            config=config,
            suite=suite,
            rows=rows,
            paths=paths,
            runtime_source=runtime_source,
            final_status=final_status,
        )
    except (OSError, ReportError, ValueError) as exc:
        print(
            f"REPORTS unavailable after completed execution: {exc}",
            file=sys.stderr,
            flush=True,
        )
        print(json.dumps(results, indent=2, sort_keys=True))
        return 2
    print(
        "REPORTS saved | "
        f"status {report_paths['status']} | "
        f"report {report_paths['report']} | "
        f"decision {report_paths['decision_evidence']} | "
        f"score {report_paths['score']}",
        file=sys.stderr,
        flush=True,
    )

    if not final_status["qualified"]:
        blockers = [
            f"{label} {final_status[key]}"
            for key, label in (
                ("pending_trials", "pending"),
                ("interrupted_trials", "interrupted"),
                ("conflicting_trials", "conflicting"),
                ("unresolved_outcome_trials", "non-outcome receipts"),
            )
            if final_status.get(key)
        ]
        blockers.extend(
            f"{label} {len(final_status[key])}"
            for key, label in (
                ("corrupt_bundles", "corrupt bundles"),
                ("foreign_bundles", "foreign bundles"),
            )
            if final_status.get(key)
        )
        blockers.extend(
            f"{label}: {final_status[key]}"
            for key, label in (
                ("comparability_error", "comparability"),
                ("campaign_authority_error", "campaign authority"),
            )
            if final_status.get(key)
        )
        print(
            "NOT QUALIFIED: "
            + (", ".join(blockers) if blockers else "inspect campaign status"),
            file=sys.stderr,
            flush=True,
        )
        print(
            "Next: inspect benchmark status and report with the same selectors",
            file=sys.stderr,
            flush=True,
        )
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0 if final_status["qualified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
