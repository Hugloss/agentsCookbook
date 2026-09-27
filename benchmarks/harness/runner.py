"""Executable trial lifecycle and atomic evidence-bundle publication."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import platform
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benchmarks.adapters.codex import seed_codex_auth
from benchmarks.adapters.registry import build_agent, build_oracle, build_subject
from benchmarks.harness.bundle import verify_bundle
from benchmarks.harness.contamination import classify_contamination
from benchmarks.harness.events import append_event, seal_events
from benchmarks.harness.identity import definition_id, execution_id
from benchmarks.harness.model import (
    AgentAdapter,
    Observation,
    OracleAdapter,
    SubjectAdapter,
    TrialContext,
    TrialStatus,
)
from benchmarks.harness.mutation import apply_mutation
from benchmarks.harness.receipt import write_receipt
from benchmarks.harness.schema_validation import (
    SchemaValidationError,
    validate_instance,
)
from benchmarks.harness.source import materialize_repository
from benchmarks.harness.suite import SuiteDefinition
from benchmarks.harness.workspace import isolated_environment, snapshot
from scripts.agent_economics.bounded_process import ProcessLimits, run_bounded


class TrialRunnerError(RuntimeError):
    pass


@dataclass(frozen=True)
class TrialRunResult:
    trial_id: str
    definition_id: str
    status: str
    result_dir: Path
    reused: bool
    reason: str | None = None


@dataclass(frozen=True)
class TrialPreflightResult:
    task_id: str
    condition_id: str
    status: str
    reason: str | None


@dataclass(frozen=True)
class _PreparedTrial:
    task: dict[str, Any]
    expanded_condition: dict[str, Any]
    seed: int
    definition: str
    workspace: Path
    context: TrialContext
    mutation: Observation
    admitted_state: Any
    subject: SubjectAdapter
    agent: AgentAdapter
    oracle: OracleAdapter
    subject_prepare: Observation
    agent_prepare: Observation
    oracle_health: Observation
    auth_mode: str


def _git_bytes(root: Path, argv: tuple[str, ...]) -> bytes:
    result = run_bounded(
        repository_root=root,
        argv=argv,
        limits=ProcessLimits(
            timeout_seconds=30.0,
            max_stdout_bytes=50_000_000,
            max_stderr_bytes=1_000_000,
        ),
    )
    if (
        result.executable_missing
        or result.timed_out
        or result.return_code != 0
        or result.stdout_truncated
        or result.stderr_truncated
    ):
        raise TrialRunnerError(
            f"cannot establish harness git authority: {' '.join(argv)}"
        )
    return result.stdout


def _git_value(root: Path, argv: tuple[str, ...]) -> str:
    return _git_bytes(root, argv).decode("utf-8", errors="strict").strip()


def harness_identity(root: Path) -> dict[str, Any]:
    root = root.resolve()
    commit = _git_value(root, ("git", "rev-parse", "HEAD"))
    tree = _git_value(root, ("git", "rev-parse", "HEAD^{tree}"))
    diff = _git_bytes(root, ("git", "diff", "--binary", "HEAD"))
    untracked = [
        path
        for path in _git_bytes(
            root, ("git", "ls-files", "--others", "--exclude-standard", "-z")
        ).split(b"\0")
        if path
    ]
    fingerprint = hashlib.sha256(diff)
    try:
        for path in untracked:
            fingerprint.update(path)
            fingerprint.update((root / os.fsdecode(path)).read_bytes())
    except OSError as exc:
        raise TrialRunnerError("cannot fingerprint untracked benchmark files") from exc
    return {
        "repository": "Hugloss/agentsCookbook",
        "commit": commit,
        "tree": tree,
        "working_copy_sha256": fingerprint.hexdigest(),
        "working_copy_clean": not diff and not untracked,
        "contract": "generic-benchmark-runner-v1",
    }


def runtime_environment_identity() -> dict[str, Any]:
    return {
        "isolation_contract": ("codex-isolated-or-opencode-native-config-v2"),
        "system": platform.system(),
        "machine": platform.machine(),
        "python": platform.python_version(),
    }


def _declared(identity) -> dict[str, Any]:
    return dataclasses.asdict(identity)


def _subject_authority(subject, prepared: Observation) -> dict[str, Any]:
    return {
        "declared": _declared(subject.identity()),
        "available": bool(prepared.payload.get("available")),
        "observed": prepared.payload.get("observed_identity"),
    }


def _agent_authority(agent, prepared: Observation) -> dict[str, Any]:
    return {
        "declared": _declared(agent.identity()),
        "available": bool(prepared.payload.get("available")),
        "observed": {
            "version": prepared.payload.get("version"),
            "executable_sha256": prepared.payload.get("executable_sha256"),
            "mcp_exposure": prepared.payload.get("mcp_exposure"),
            "auth_mode": prepared.payload.get("auth_mode"),
            "model": prepared.payload.get("model"),
            "reasoning_effort": prepared.payload.get("reasoning_effort"),
            "provider": prepared.payload.get("provider"),
            "native_config_sha256": prepared.payload.get("native_config_sha256"),
            "native_mcp_servers": prepared.payload.get("native_mcp_servers"),
        },
    }


def _oracle_authority(oracle, health: Observation) -> dict[str, Any]:
    return {
        "declared": _declared(oracle.identity()),
        "healthy": bool(health.payload.get("healthy")),
    }


def _validate_result_receipt(receipt: dict[str, Any]) -> None:
    schema_path = Path(__file__).resolve().parents[1] / "schema" / "result.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        validate_instance(receipt, schema)
    except (OSError, json.JSONDecodeError, SchemaValidationError) as exc:
        raise TrialRunnerError(
            f"generated result receipt violates result schema: {exc}"
        ) from exc


def _artifact(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "path": path.name,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
    }


def _publish_bundle(
    *,
    results_root: Path,
    trial_id: str,
    event_path: Path,
    event_seal_path: Path,
    agent_trace: str,
    receipt: dict[str, Any],
) -> Path:
    results_root.mkdir(parents=True, exist_ok=True)
    final_dir = results_root / trial_id
    if final_dir.exists():
        valid, reason = verify_bundle(final_dir)
        if valid:
            return final_dir
        raise TrialRunnerError(
            f"published trial bundle is invalid: {final_dir}: {reason}"
        )
    bundle = Path(tempfile.mkdtemp(prefix=f".{trial_id}.bundle-", dir=results_root))
    try:
        shutil.copy2(event_path, bundle / "events.jsonl")
        shutil.copy2(event_seal_path, bundle / "events.jsonl.seal.json")
        (bundle / "agent-trace.jsonl").write_text(
            agent_trace,
            encoding="utf-8",
        )
        receipt["execution"]["artifacts"] = {
            "events": _artifact(bundle / "events.jsonl"),
            "events_seal": _artifact(bundle / "events.jsonl.seal.json"),
            "agent_trace": _artifact(bundle / "agent-trace.jsonl"),
        }
        _validate_result_receipt(receipt)
        write_receipt(bundle, receipt)
        os.rename(bundle, final_dir)
        valid, reason = verify_bundle(final_dir)
        if not valid:
            shutil.rmtree(final_dir, ignore_errors=True)
            raise TrialRunnerError(
                f"published trial bundle failed verification: {reason}"
            )
        try:
            fd = os.open(results_root, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError:
            pass
    except BaseException:
        shutil.rmtree(bundle, ignore_errors=True)
        raise
    return final_dir


def _reason_for_agent(observation: Observation) -> str | None:
    process = observation.payload.get("process")
    if isinstance(process, dict):
        if process.get("executable_missing"):
            return "agent executable unavailable"
        if process.get("timed_out"):
            return "agent execution timed out"
        if process.get("stdout_truncated") or process.get("stderr_truncated"):
            return "agent execution evidence exceeded configured bounds"
    if observation.payload.get("jsonl_parse_errors"):
        return "agent JSONL evidence is malformed"
    terminal = observation.payload.get("terminal_event")
    if not isinstance(terminal, dict):
        return "agent emitted no terminal event"
    if terminal.get("type") != "turn.completed":
        return f"agent terminal event was {terminal.get('type')}"
    return None


def _prepare_trial(
    *,
    suite: SuiteDefinition,
    task_id: str,
    condition_id: str,
    trial_index: int,
    run_root: Path,
    cache_root: Path,
    local_source: Path | None,
    codex_auth: Path | None,
) -> _PreparedTrial:
    task = suite.tasks[task_id]
    condition = next(
        (
            value
            for value in suite.experiment["conditions"]
            if value["id"] == condition_id
        ),
        None,
    )
    if condition is None:
        raise TrialRunnerError(f"unknown condition: {condition_id}")
    if trial_index < 0 or trial_index >= int(condition["trials"]):
        raise TrialRunnerError(
            f"trial index {trial_index} outside condition trial range"
        )

    expanded_condition = suite.expanded_condition(condition)
    seed = int(condition["seed"]) + trial_index
    definition = definition_id(
        experiment=suite.experiment,
        task=task,
        condition=expanded_condition,
        trial=trial_index,
        seed=seed,
    )
    workspace = run_root / "workspace"
    materialize_repository(
        repository=task["repository"],
        destination=workspace,
        cache_root=cache_root,
        local_source=local_source,
    )
    control_root = run_root / "control"
    environment = isolated_environment(control_root)
    if "HASHMARKS_BENCH_SOURCE" in os.environ:
        environment["HASHMARKS_BENCH_SOURCE"] = os.environ["HASHMARKS_BENCH_SOURCE"]
    context = TrialContext(
        workspace=workspace,
        control_root=control_root,
        environment=environment,
    )
    mutation = apply_mutation(
        context,
        suite_root=suite.root,
        mutation=task["mutation"],
    )
    admitted_state = snapshot(workspace)
    subject = build_subject(suite.subjects[str(condition["subject"])])
    agent_definition = suite.agents[str(condition["agent"])]
    agent = build_agent(agent_definition, budgets=task["budgets"])
    native_codex = (
        agent_definition["adapter"] == "codex"
        and agent_definition.get("configuration", {}).get("native_host") is True
    )
    if native_codex:
        context.environment["HOME"] = str(Path.home())
        context.environment["CODEX_HOME"] = str(
            Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").resolve()
        )
        # Keep the trial cache isolated for Hashmarks' artifact store and MCP child.
        for name in ("XDG_CONFIG_HOME", "XDG_STATE_HOME"):
            if name in os.environ:
                context.environment[name] = os.environ[name]
            else:
                context.environment.pop(name, None)
    auth_mode = (
        "native-host"
        if native_codex
        else seed_codex_auth(context, codex_auth)
        if agent_definition["adapter"] == "codex"
        else "native-opencode"
        if agent_definition["adapter"] == "opencode-native"
        else "not-applicable"
    )
    if agent_definition["adapter"] == "codex":
        context.environment["BENCHMARK_CODEX_AUTH_MODE"] = auth_mode
    oracle = build_oracle(
        task["oracle"],
        timeout_seconds=int(task["budgets"]["timeout_seconds"]),
        suite_root=suite.root,
    )
    return _PreparedTrial(
        task=task,
        expanded_condition=expanded_condition,
        seed=seed,
        definition=definition,
        workspace=workspace,
        context=context,
        mutation=mutation,
        admitted_state=admitted_state,
        subject=subject,
        agent=agent,
        oracle=oracle,
        subject_prepare=subject.prepare(context),
        agent_prepare=agent.prepare(context, subject),
        oracle_health=oracle.healthcheck(context),
        auth_mode=auth_mode,
    )


def _preparation_failure(
    prepared: _PreparedTrial,
) -> tuple[TrialStatus | None, str | None]:
    if not prepared.subject_prepare.payload.get("available"):
        return (
            TrialStatus.INCOMPLETE,
            str(
                prepared.subject_prepare.payload.get("reason")
                or "subject unavailable or preparation failed"
            ),
        )
    if not prepared.agent_prepare.payload.get("available"):
        return (
            TrialStatus.INCOMPLETE,
            str(
                prepared.agent_prepare.payload.get("reason")
                or "agent unavailable or preparation failed"
            ),
        )
    if not prepared.oracle_health.payload.get("healthy"):
        return TrialStatus.INVALID, "independent oracle healthcheck failed"
    return None, None


def preflight_trial(
    *,
    suite: SuiteDefinition,
    task_id: str,
    condition_id: str,
    trial_index: int,
    cache_root: Path,
    work_root: Path,
    local_source: Path | None = None,
    codex_auth: Path | None = None,
) -> TrialPreflightResult:
    """Prepare one frozen arm without starting an agent or publishing a receipt."""
    work_root.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(
            prefix="preflight-", dir=work_root
        ) as temporary:
            prepared = _prepare_trial(
                suite=suite,
                task_id=task_id,
                condition_id=condition_id,
                trial_index=trial_index,
                run_root=Path(temporary),
                cache_root=cache_root,
                local_source=local_source,
                codex_auth=codex_auth,
            )
            status, reason = _preparation_failure(prepared)
    except (OSError, RuntimeError, ValueError) as exc:
        status, reason = (
            TrialStatus.INCOMPLETE,
            f"preparation raised {type(exc).__name__}: {exc}",
        )
    return TrialPreflightResult(
        task_id=task_id,
        condition_id=condition_id,
        status=status.value if status else "READY",
        reason=reason,
    )


def run_trial(
    *,
    suite: SuiteDefinition,
    task_id: str,
    condition_id: str,
    trial_index: int,
    harness_root: Path,
    cache_root: Path,
    results_root: Path,
    work_root: Path,
    local_source: Path | None = None,
    codex_auth: Path | None = None,
) -> TrialRunResult:
    task = suite.tasks[task_id]
    condition = next(
        (
            value
            for value in suite.experiment["conditions"]
            if value["id"] == condition_id
        ),
        None,
    )
    if condition is None:
        raise TrialRunnerError(f"unknown condition: {condition_id}")
    if trial_index < 0 or trial_index >= int(condition["trials"]):
        raise TrialRunnerError(
            f"trial index {trial_index} outside condition trial range"
        )

    expanded_condition = suite.expanded_condition(condition)
    seed = int(condition["seed"]) + trial_index
    definition = definition_id(
        experiment=suite.experiment,
        task=task,
        condition=expanded_condition,
        trial=trial_index,
        seed=seed,
    )

    work_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f"{definition[:12]}-",
        dir=work_root,
    ) as temporary:
        run_root = Path(temporary)
        prepared = _prepare_trial(
            suite=suite,
            task_id=task_id,
            condition_id=condition_id,
            trial_index=trial_index,
            run_root=run_root,
            cache_root=cache_root,
            local_source=local_source,
            codex_auth=codex_auth,
        )
        task = prepared.task
        expanded_condition = prepared.expanded_condition
        seed = prepared.seed
        definition = prepared.definition
        workspace = prepared.workspace
        context = prepared.context
        mutation = prepared.mutation
        admitted_state = prepared.admitted_state
        subject = prepared.subject
        agent = prepared.agent
        oracle = prepared.oracle
        subject_prepare = prepared.subject_prepare
        agent_prepare = prepared.agent_prepare
        oracle_health = prepared.oracle_health
        auth_mode = prepared.auth_mode

        subject_authority = _subject_authority(subject, subject_prepare)
        agent_authority = _agent_authority(agent, agent_prepare)
        oracle_authority = _oracle_authority(oracle, oracle_health)
        harness_authority = harness_identity(harness_root)
        environment_authority = runtime_environment_identity()
        mutation_authority = mutation.payload.get("identity")

        trial_id = execution_id(
            definition=definition,
            subject_identity=subject_authority,
            agent_identity=agent_authority,
            oracle_identity=oracle_authority,
            harness_identity=harness_authority,
            environment_identity=environment_authority,
            mutation_identity=mutation_authority,
        )
        final_dir = results_root / trial_id
        if final_dir.exists():
            valid, invalid_reason = verify_bundle(final_dir)
            if not valid:
                raise TrialRunnerError(
                    f"existing trial bundle is invalid: {final_dir}: {invalid_reason}"
                )
            existing = json.loads(
                (final_dir / "result.json").read_text(encoding="utf-8")
            )
            return TrialRunResult(
                trial_id=trial_id,
                definition_id=definition,
                status=str(existing["status"]),
                result_dir=final_dir,
                reused=True,
                reason=existing.get("reason"),
            )

        event_path = run_root / "events.jsonl"
        sequence = 0

        def emit(kind: str, payload: dict[str, Any]) -> None:
            nonlocal sequence
            append_event(
                event_path,
                trial_id=trial_id,
                sequence=sequence,
                kind=kind,
                payload=payload,
            )
            sequence += 1

        emit(
            "trial.materialized",
            {
                "repository": task["repository"],
                "definition_id": definition,
                "seed": seed,
            },
        )
        emit("trial.mutation", mutation.payload)
        emit("subject.prepared", subject_prepare.payload)
        emit(
            "agent.prepared",
            {**agent_prepare.payload, "auth_mode": auth_mode},
        )
        emit("oracle.health", oracle_health.payload)

        agent_observation = Observation(
            {
                "terminal_complete": False,
                "final_message": None,
                "process": {},
            },
            "",
            {},
        )
        grade = Observation(
            {"passed": False, "reason": "not graded"},
            "",
            {},
        )
        reason: str | None = None

        preparation_status, preparation_reason = _preparation_failure(prepared)
        if preparation_status is not None:
            status = preparation_status
            reason = preparation_reason
        else:
            emit(
                "agent.started",
                {
                    "tool_available": (
                        agent_prepare.payload.get("mcp_exposure") is not None
                    ),
                    "mode": task["mode"],
                },
            )
            agent_observation = agent.run(context, task["prompt"], subject)
            emit(
                "agent.completed",
                {
                    "payload": agent_observation.payload,
                    "measurements": agent_observation.measurements,
                },
            )
            budget_violation = agent_observation.payload.get("budget_violation")
            agent_reason = _reason_for_agent(agent_observation)
            if isinstance(budget_violation, str) and budget_violation:
                status = TrialStatus.INVALID
                reason = budget_violation
            elif agent_reason is not None:
                status = TrialStatus.INCOMPLETE
                reason = agent_reason
            else:
                grade = oracle.grade(context, agent_observation)
                emit(
                    "oracle.graded",
                    {
                        "payload": grade.payload,
                        "measurements": grade.measurements,
                    },
                )
                if grade.payload.get("valid") is False:
                    status = TrialStatus.INVALID
                    reason = "independent oracle could not complete grading"
                else:
                    status = (
                        TrialStatus.PASS
                        if grade.payload.get("passed") is True
                        else TrialStatus.FAIL
                    )
                    if status is TrialStatus.FAIL:
                        grade_reason = grade.payload.get("reason")
                        reason = (
                            str(grade_reason)
                            if grade_reason
                            else "independent oracle rejected outcome"
                        )

        observed_state = snapshot(workspace)
        contamination_config = task["contamination"]
        allowed_generated = tuple(
            sorted(
                set(contamination_config["allowed_generated_globs"])
                | set(subject.generated_globs())
            )
        )
        contamination = classify_contamination(
            before=admitted_state,
            after=observed_state,
            allowed_change_globs=tuple(contamination_config["allowed_change_globs"]),
            allowed_generated_globs=allowed_generated,
        )
        emit("trial.contamination", contamination)
        if contamination["contaminated"]:
            status = TrialStatus.CONTAMINATED
            reason = "workspace changed outside frozen contamination allowances"

        changed_paths = tuple(
            sorted(
                set(contamination["diff"]["added"])
                | set(contamination["diff"]["removed"])
                | set(contamination["diff"]["changed"])
            )
        )
        if changed_paths:
            post_change = subject.post_change(context, changed_paths)
            emit(
                "subject.post_change",
                {
                    "payload": post_change.payload,
                    "measurements": post_change.measurements,
                },
            )
        cleanup = subject.cleanup(context)
        emit("subject.cleanup", cleanup.payload)

        event_evidence = seal_events(event_path, trial_id=trial_id)
        event_seal_path = event_path.with_name(event_path.name + ".seal.json")

        receipt: dict[str, Any] = {
            "definition_id": definition,
            "trial_id": trial_id,
            "experiment": suite.experiment,
            "task": task,
            "condition": expanded_condition,
            "status": status.value,
            "authority": {
                "subject": subject_authority,
                "agent": agent_authority,
                "oracle": oracle_authority,
                "harness": harness_authority,
                "environment": environment_authority,
                "mutation": mutation_authority,
            },
            "execution": {
                "seed": seed,
                "trial_index": trial_index,
                "events": event_evidence,
                "agent_terminal": agent_observation.payload.get("terminal_event"),
            },
            "measurements": {
                "subject_prepare": subject_prepare.measurements,
                "agent_prepare": agent_prepare.measurements,
                "agent": agent_observation.measurements,
                "oracle_health": oracle_health.measurements,
                "oracle_grade": grade.measurements,
                "contamination": contamination,
            },
            "reason": reason,
        }
        result_dir = _publish_bundle(
            results_root=results_root,
            trial_id=trial_id,
            event_path=event_path,
            event_seal_path=event_seal_path,
            agent_trace=agent_observation.raw,
            receipt=receipt,
        )
        return TrialRunResult(
            trial_id=trial_id,
            definition_id=definition,
            status=status.value,
            result_dir=result_dir,
            reused=False,
            reason=reason,
        )
