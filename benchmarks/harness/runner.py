"""Executable trial lifecycle and atomic evidence-bundle publication."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import traceback
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benchmarks.harness.admission import TrialAdmissionError, admit_trial
from benchmarks.harness.bundle import verify_bundle
from benchmarks.harness.campaign_authority import (
    CampaignAuthorityError,
    claim_launch,
    launch_state,
    verify_trial_authority,
)
from benchmarks.harness.contamination import classify_contamination
from benchmarks.harness.events import append_event, seal_events
from benchmarks.harness.identity import (
    EXECUTION_EVIDENCE_CONTRACT,
    execution_evidence_id,
    score_projection_id,
    digest,
)
from benchmarks.adapters.oracles import RepositoryLocationOracle
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
    reason: str | None = None
    stage: str | None = None
    reason_code: str | None = None
    diagnostic: str | None = None
    recovered: bool = False


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


def _bounded_preview(value: Any, *, limit: int = 240) -> str | None:
    if not isinstance(value, str):
        return None
    rendered = value.strip()
    if not rendered:
        return None
    if len(rendered) > limit:
        rendered = rendered[:limit] + "…"
    return repr(rendered)


def _reason_for_oracle_failure(grade: Observation) -> str:
    reason = grade.payload.get("reason")
    rendered = str(reason) if reason else "independent oracle rejected outcome"
    actual = _bounded_preview(grade.payload.get("actual_text"))
    if actual is not None:
        return f"{rendered}; actual={actual}"
    return rendered


def _agent_failure(observation: Observation) -> tuple[str, str] | None:
    process = observation.payload.get("process")
    if isinstance(process, dict):
        if process.get("executable_missing"):
            return "agent-executable-unavailable", "agent executable unavailable"
        if process.get("timed_out"):
            return "agent-timeout", "agent execution timed out"
        if process.get("stdout_truncated") or process.get("stderr_truncated"):
            return (
                "agent-evidence-truncated",
                "agent execution evidence exceeded configured bounds",
            )
        if process.get("return_code") not in (None, 0):
            return (
                "agent-process-nonzero",
                f"agent process exited with status {process['return_code']}",
            )
    if observation.payload.get("jsonl_parse_errors"):
        return "agent-jsonl-malformed", "agent JSONL evidence is malformed"
    terminal = observation.payload.get("terminal_event")
    if not isinstance(terminal, dict):
        return "agent-terminal-missing", "agent emitted no terminal event"
    if terminal.get("type") != "turn.completed":
        reason = terminal.get("reason")
        rendered = f"agent terminal event was {terminal.get('type')}"
        if isinstance(reason, str) and reason:
            rendered += f": {reason}"
        return "agent-terminal-failed", rendered
    answer = observation.payload.get("final_message")
    if not isinstance(answer, str) or not answer.strip():
        return (
            "agent-final-answer-missing",
            "agent completed without a final assistant answer",
        )
    return None


def _reason_for_agent(observation: Observation) -> str | None:
    failure = _agent_failure(observation)
    return failure[1] if failure is not None else None


def _bounded_diagnostic(value: str | None, *, limit: int = 8_000) -> str | None:
    if not isinstance(value, str):
        return None
    rendered = value.strip()
    if not rendered:
        return None
    if len(rendered) <= limit:
        return rendered
    return rendered[:limit] + "…"


def _recover_interrupted_launch(
    *,
    admission: Any,
    results_root: Path,
    campaign: dict[str, Any],
) -> TrialRunResult:
    """Seal a previously claimed crash as INCOMPLETE without relaunching the model."""
    reason = "previous trial launch was interrupted before a complete receipt"
    stage = "campaign-recovery"
    reason_code = "interrupted-launch"
    diagnostic_detail = (
        "A durable launch claim exists but no complete receipt was published. "
        "The trial is recorded as INCOMPLETE and is not retried."
    )
    trial_id = admission.trial_id
    run_root = admission.context.workspace.parent
    event_path = run_root / "events.jsonl"
    append_event(
        event_path,
        trial_id=trial_id,
        sequence=0,
        kind="trial.recovered_interruption",
        payload={
            "definition_id": admission.definition_id,
            "reason_code": reason_code,
        },
    )
    event_evidence = seal_events(event_path, trial_id=trial_id)
    event_seal_path = event_path.with_name(event_path.name + ".seal.json")

    cleanup_payload: dict[str, Any]
    try:
        cleanup_payload = admission.cleanup_subject().payload
    except Exception as exc:
        cleanup_payload = {"error": str(exc)}

    identity_field = (
        {"seed": admission.replicate_id}
        if admission.legacy_seed
        else {"replicate_id": admission.replicate_id}
    )
    agent_trace = ""
    workspace_root = str(admission.context.workspace.resolve())
    admitted_state_sha256 = digest(admission.admitted_state)
    trace_sha256 = hashlib.sha256(agent_trace.encode("utf-8")).hexdigest()
    execution_evidence = execution_evidence_id(
        task=admission.task,
        condition=admission.expanded_condition,
        trial=admission.trial_index,
        **identity_field,
        subject_identity=admission.subject_authority,
        agent_identity=admission.agent_authority,
        harness_identity=admission.harness_authority,
        environment_identity=admission.environment_authority,
        mutation_identity=admission.mutation_authority,
        agent_answer=None,
        workspace_root=workspace_root,
        location_observation=None,
        agent_trace_sha256=trace_sha256,
        **(
            {
                "campaign_id": campaign["campaign_id"],
                "admitted_state_sha256": admitted_state_sha256,
            }
            if not admission.legacy_seed
            else {}
        ),
    )
    score_projection = score_projection_id(
        execution_evidence=execution_evidence,
        oracle_identity=admission.oracle_authority["declared"],
        **(
            {"contract": "benchmark-score-projection.v3"}
            if not admission.legacy_seed
            else {}
        ),
    )
    receipt: dict[str, Any] = {
        "definition_id": admission.definition_id,
        "trial_id": trial_id,
        "experiment": admission.suite.experiment,
        "task": admission.task,
        "condition": admission.expanded_condition,
        "status": TrialStatus.INCOMPLETE.value,
        "authority": {
            "subject": admission.subject_authority,
            "agent": admission.agent_authority,
            "oracle": admission.oracle_authority,
            "harness": admission.harness_authority,
            "environment": admission.environment_authority,
            "mutation": admission.mutation_authority,
        },
        "execution": {
            **identity_field,
            **(
                {"campaign_id": campaign["campaign_id"]}
                if not admission.legacy_seed
                else {}
            ),
            "trial_index": admission.trial_index,
            "events": event_evidence,
            "agent_terminal": {
                "type": "turn.failed",
                "reason": reason,
            },
            "agent_answer": None,
            "workspace_root": workspace_root,
            "admitted_state_sha256": admitted_state_sha256,
            "location_observation": None,
            "evidence_contract": (
                EXECUTION_EVIDENCE_CONTRACT
                if admission.legacy_seed
                else "benchmark-execution-evidence.v3"
            ),
            "evidence_identity": execution_evidence,
        },
        "scoring": {
            "projection_identity": score_projection,
            "oracle_grade": {
                "passed": False,
                "valid": False,
                "reason": "not graded because prior launch was interrupted",
            },
        },
        "diagnostic": {
            "stage": stage,
            "reason_code": reason_code,
            "detail": diagnostic_detail,
        },
        "measurements": {
            "subject_prepare": admission.subject_prepare.measurements,
            "agent_prepare": admission.agent_prepare.measurements,
            "oracle_health": admission.oracle_health.measurements,
            "oracle_grade": {},
            "contamination": {
                "contaminated": None,
                "diff": {"added": [], "removed": [], "changed": []},
                "not_observed": "interrupted launch recovery",
            },
            "subject_cleanup": cleanup_payload,
        },
        "reason": reason,
    }
    result_dir = _publish_bundle(
        results_root=results_root,
        trial_id=trial_id,
        event_path=event_path,
        event_seal_path=event_seal_path,
        agent_trace=agent_trace,
        receipt=receipt,
    )
    return TrialRunResult(
        trial_id=trial_id,
        definition_id=admission.definition_id,
        status=TrialStatus.INCOMPLETE.value,
        result_dir=result_dir,
        reused=False,
        reason=reason,
        stage=stage,
        reason_code=reason_code,
        diagnostic=diagnostic_detail,
        recovered=True,
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
    source: Mapping[str, str] | None = None,
    campaign: dict[str, Any] | None = None,
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
            source=source,
        )
        with admission_context as admission:
            task = admission.task
            expanded_condition = admission.expanded_condition
            replicate_id = admission.replicate_id
            identity_field = (
                {"seed": replicate_id}
                if admission.legacy_seed
                else {"replicate_id": replicate_id}
            )
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
            if not admission.legacy_seed:
                if campaign is None:
                    raise TrialRunnerError(
                        "replicate trial requires campaign authority"
                    )
                verify_trial_authority(
                    results_root=results_root,
                    campaign=campaign,
                    admission=admission,
                )
                state = launch_state(
                    results_root=results_root,
                    campaign=campaign,
                    definition_id=definition,
                    trial_id=trial_id,
                )
                if state == "INTERRUPTED":
                    return _recover_interrupted_launch(
                        admission=admission,
                        results_root=results_root,
                        campaign=campaign,
                    )
                if final_dir.exists() and state != "COMPLETE":
                    raise TrialRunnerError(
                        "result exists without a matching launch claim"
                    )
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
                diagnostic = existing.get("diagnostic")
                if not isinstance(diagnostic, dict):
                    diagnostic = {}
                return TrialRunResult(
                    trial_id=trial_id,
                    definition_id=definition,
                    status=str(existing["status"]),
                    result_dir=final_dir,
                    reused=True,
                    reason=existing.get("reason"),
                    stage=diagnostic.get("stage"),
                    reason_code=diagnostic.get("reason_code"),
                    diagnostic=diagnostic.get("detail"),
                    recovered=False,
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
                    **identity_field,
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
            location_observation: dict[str, Any] | None = None
            stage: str | None = None
            reason_code: str | None = None
            diagnostic_detail: str | None = None
            agent_exception_traceback: str | None = None
            status, reason = admission.initial_outcome()
            if status is not None:
                stage = "admission"
                reason_code = "admission-initial-outcome"
            if not admission.legacy_seed and status is not None:
                raise TrialRunnerError(f"pre-model admission failed: {reason}")

            if status is None:
                if campaign is not None:
                    claim_launch(
                        results_root=results_root,
                        campaign=campaign,
                        definition_id=definition,
                        trial_id=trial_id,
                    )
                emit(
                    "agent.started",
                    {
                        "tool_available": (
                            agent_prepare.payload.get("mcp_exposure") is not None
                        ),
                        "mode": task["mode"],
                    },
                )
                try:
                    agent_observation = agent.run(context, task["prompt"], subject)
                except Exception as exc:
                    agent_exception_traceback = traceback.format_exc()
                    agent_observation = Observation(
                        {
                            "terminal_event": {
                                "type": "turn.failed",
                                "reason": str(exc),
                            },
                            "terminal_complete": False,
                            "final_message": None,
                            "process": {},
                        },
                        repr(exc),
                    )
                emit(
                    "agent.completed",
                    {
                        "payload": agent_observation.payload,
                        "measurements": agent_observation.measurements,
                    },
                )
                try:
                    if isinstance(oracle, RepositoryLocationOracle):
                        location_observation = oracle.observe(
                            context, agent_observation
                        )
                    budget_violation = agent_observation.payload.get("budget_violation")
                    agent_failure = _agent_failure(agent_observation)
                    if isinstance(budget_violation, str) and budget_violation:
                        status = TrialStatus.INVALID
                        reason = budget_violation
                        stage = "agent-execution"
                        reason_code = "agent-budget-violation"
                        diagnostic_detail = _bounded_diagnostic(budget_violation)
                    elif agent_failure is not None:
                        status = TrialStatus.INCOMPLETE
                        reason_code, reason = agent_failure
                        stage = "agent-execution"
                        diagnostic_detail = _bounded_diagnostic(
                            agent_exception_traceback or reason
                        )
                    else:
                        grade = (
                            oracle.grade_observed(location_observation)
                            if isinstance(oracle, RepositoryLocationOracle)
                            and location_observation is not None
                            else oracle.grade(context, agent_observation)
                        )
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
                            stage = "oracle-grading"
                            reason_code = "oracle-invalid"
                            diagnostic_detail = _bounded_diagnostic(
                                str(grade.payload.get("reason") or reason)
                            )
                        else:
                            status = (
                                TrialStatus.PASS
                                if grade.payload.get("passed") is True
                                else TrialStatus.FAIL
                            )
                            if status is TrialStatus.FAIL:
                                reason = _reason_for_oracle_failure(grade)
                                stage = "oracle-grading"
                                reason_code = "oracle-mismatch"
                                diagnostic_detail = _bounded_diagnostic(reason)
                except Exception as exc:
                    status = TrialStatus.INCOMPLETE
                    reason = f"post-execution observation failed: {exc}"
                    stage = "post-execution-observation"
                    reason_code = "post-execution-observation-exception"
                    diagnostic_detail = _bounded_diagnostic(traceback.format_exc())
                    emit("trial.observation_failed", {"reason": reason})

            try:
                observed_state = snapshot(context.workspace)
                contamination_config = task["contamination"]
                allowed_generated = tuple(
                    sorted(
                        set(contamination_config["allowed_generated_globs"])
                        | set(admission.generated_globs())
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
            except Exception as exc:
                contamination = {
                    "contaminated": None,
                    "diff": {"added": [], "removed": [], "changed": []},
                    "observation_error": str(exc),
                }
                status = TrialStatus.INCOMPLETE
                reason = f"workspace observation failed: {exc}"
                stage = "workspace-observation"
                reason_code = "workspace-observation-exception"
                diagnostic_detail = _bounded_diagnostic(traceback.format_exc())
            emit("trial.contamination", contamination)
            if contamination["contaminated"]:
                status = TrialStatus.CONTAMINATED
                reason = "workspace changed outside frozen contamination allowances"
                stage = "contamination"
                reason_code = "workspace-contamination"
                diagnostic_detail = _bounded_diagnostic(reason)

            changed_paths = tuple(
                sorted(
                    set(contamination["diff"]["added"])
                    | set(contamination["diff"]["removed"])
                    | set(contamination["diff"]["changed"])
                )
            )
            if changed_paths:
                try:
                    post_change = admission.post_change(changed_paths)
                    emit(
                        "subject.post_change",
                        {
                            "payload": post_change.payload,
                            "measurements": post_change.measurements,
                        },
                    )
                except Exception as exc:
                    status = TrialStatus.INCOMPLETE
                    reason = f"subject post-change failed: {exc}"
                    stage = "subject-post-change"
                    reason_code = "subject-post-change-exception"
                    diagnostic_detail = _bounded_diagnostic(traceback.format_exc())
                    emit("subject.post_change_failed", {"reason": reason})
            try:
                cleanup = admission.cleanup_subject()
                emit("subject.cleanup", cleanup.payload)
            except Exception as exc:
                status = TrialStatus.INCOMPLETE
                reason = f"subject cleanup failed: {exc}"
                stage = "subject-cleanup"
                reason_code = "subject-cleanup-exception"
                diagnostic_detail = _bounded_diagnostic(traceback.format_exc())
                emit("subject.cleanup_failed", {"reason": reason})

            event_evidence = seal_events(event_path, trial_id=trial_id)
            event_seal_path = event_path.with_name(event_path.name + ".seal.json")

            agent_answer = agent_observation.payload.get("final_message")
            workspace_root = str(context.workspace.resolve())
            trace_sha256 = hashlib.sha256(
                agent_observation.raw.encode("utf-8")
            ).hexdigest()
            execution_evidence = execution_evidence_id(
                task=task,
                condition=expanded_condition,
                trial=trial_index,
                **identity_field,
                subject_identity=subject_authority,
                agent_identity=agent_authority,
                harness_identity=harness_authority,
                environment_identity=environment_authority,
                mutation_identity=mutation_authority,
                agent_answer=agent_answer,
                workspace_root=workspace_root,
                location_observation=location_observation,
                agent_trace_sha256=trace_sha256,
                **(
                    {
                        "campaign_id": campaign["campaign_id"],
                        "admitted_state_sha256": digest(admitted_state),
                    }
                    if campaign is not None and not admission.legacy_seed
                    else {}
                ),
            )
            score_projection = score_projection_id(
                execution_evidence=execution_evidence,
                oracle_identity=oracle_authority["declared"],
                **(
                    {"contract": "benchmark-score-projection.v3"}
                    if not admission.legacy_seed
                    else {}
                ),
            )

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
                    **identity_field,
                    **(
                        {"campaign_id": campaign["campaign_id"]}
                        if campaign is not None and not admission.legacy_seed
                        else {}
                    ),
                    "trial_index": trial_index,
                    "events": event_evidence,
                    "agent_terminal": agent_observation.payload.get("terminal_event"),
                    "agent_answer": agent_answer,
                    "workspace_root": workspace_root,
                    "admitted_state_sha256": digest(admitted_state),
                    "location_observation": location_observation,
                    "evidence_contract": (
                        EXECUTION_EVIDENCE_CONTRACT
                        if admission.legacy_seed
                        else "benchmark-execution-evidence.v3"
                    ),
                    "evidence_identity": execution_evidence,
                },
                "scoring": {
                    "projection_identity": score_projection,
                    "oracle_grade": grade.payload,
                },
                "diagnostic": {
                    "stage": stage,
                    "reason_code": reason_code,
                    "detail": diagnostic_detail,
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
                stage=stage,
                reason_code=reason_code,
                diagnostic=diagnostic_detail,
                recovered=False,
            )
    except (TrialAdmissionError, CampaignAuthorityError) as exc:
        raise TrialRunnerError(str(exc)) from exc
