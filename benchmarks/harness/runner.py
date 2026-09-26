"""Executable trial lifecycle and atomic evidence-bundle publication."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benchmarks.harness.admission import TrialAdmissionError, admit_trial
from benchmarks.harness.bundle import verify_bundle
from benchmarks.harness.contamination import classify_contamination
from benchmarks.harness.events import append_event, seal_events
from benchmarks.harness.model import Observation, TrialStatus
from benchmarks.harness.receipt import write_receipt
from benchmarks.harness.schema_validation import (
    SchemaValidationError,
    validate_instance,
)
from benchmarks.harness.suite import SuiteDefinition
from benchmarks.harness.workspace import snapshot


class TrialRunnerError(RuntimeError):
    pass


@dataclass(frozen=True)
class TrialRunResult:
    trial_id: str
    definition_id: str
    status: str
    result_dir: Path
    reused: bool


def _validate_result_receipt(receipt: dict[str, Any]) -> None:
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "schema"
        / "result.schema.json"
    )
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
    bundle = Path(
        tempfile.mkdtemp(prefix=f".{trial_id}.bundle-", dir=results_root)
    )
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
    try:
        admission_context = admit_trial(
            suite=suite,
            task_id=task_id,
            condition_id=condition_id,
            trial_index=trial_index,
            harness_root=harness_root,
            cache_root=cache_root,
            work_root=work_root,
            local_source=local_source,
            codex_auth=codex_auth,
        )
        with admission_context as admission:
            task = admission.task
            expanded_condition = admission.expanded_condition
            seed = admission.seed
            definition = admission.definition_id
            context = admission.context
            mutation = admission.mutation
            admitted_state = admission.admitted_state
            subject = admission.subject
            agent = admission.agent
            oracle = admission.oracle
            subject_prepare = admission.subject_prepare
            agent_prepare = admission.agent_prepare
            oracle_health = admission.oracle_health
            subject_authority = admission.subject_authority
            agent_authority = admission.agent_authority
            oracle_authority = admission.oracle_authority
            harness_authority = admission.harness_authority
            environment_authority = admission.environment_authority
            mutation_authority = admission.mutation_authority
            auth_mode = admission.auth_mode
            trial_id = admission.trial_id
            final_dir = results_root / trial_id
            if final_dir.exists():
                valid, invalid_reason = verify_bundle(final_dir)
                if not valid:
                    raise TrialRunnerError(
                        f"existing trial bundle is invalid: {final_dir}: "
                        f"{invalid_reason}"
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
                )

            run_root = context.workspace.parent
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

            if not subject_authority["available"]:
                status = TrialStatus.INCOMPLETE
                reason = "subject unavailable or preparation failed"
            elif not agent_authority["available"]:
                status = TrialStatus.INCOMPLETE
                prepare_reason = agent_prepare.payload.get("reason")
                reason = (
                    str(prepare_reason)
                    if isinstance(prepare_reason, str) and prepare_reason
                    else "agent unavailable or preparation failed"
                )
            elif not oracle_authority["healthy"]:
                status = TrialStatus.INVALID
                reason = "independent oracle healthcheck failed"
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
                allowed_change_globs=tuple(
                    contamination_config["allowed_change_globs"]
                ),
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
                    "agent_terminal": agent_observation.payload.get(
                        "terminal_event"
                    ),
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
            )
    except TrialAdmissionError as exc:
        raise TrialRunnerError(str(exc)) from exc

