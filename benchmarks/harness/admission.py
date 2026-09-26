"""Shared benchmark trial admission used by preflight and execution."""
from __future__ import annotations

import dataclasses
import platform
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from benchmarks.adapters.codex import seed_codex_auth
from benchmarks.adapters.registry import build_agent, build_oracle, build_subject
from benchmarks.harness.identity import definition_id, execution_id
from benchmarks.harness.model import Observation, TrialContext, TrialStatus
from benchmarks.harness.mutation import apply_mutation
from benchmarks.harness.source import materialize_repository
from benchmarks.harness.suite import SuiteDefinition
from benchmarks.harness.workspace import isolated_environment, snapshot
from scripts.agent_economics.bounded_process import ProcessLimits, run_bounded


class TrialAdmissionError(RuntimeError):
    pass


@dataclass(frozen=True)
class TrialAdmission:
    task: dict[str, Any]
    condition: dict[str, Any]
    expanded_condition: dict[str, Any]
    trial_index: int
    seed: int
    definition_id: str
    context: TrialContext
    mutation: Observation
    admitted_state: dict[str, Any]
    subject: Any
    agent: Any
    oracle: Any
    subject_prepare: Observation
    agent_prepare: Observation
    oracle_health: Observation
    subject_authority: dict[str, Any]
    agent_authority: dict[str, Any]
    oracle_authority: dict[str, Any]
    harness_authority: dict[str, Any]
    environment_authority: dict[str, Any]
    mutation_authority: Any
    auth_mode: str

    @property
    def trial_id(self) -> str:
        return execution_id(
            definition=self.definition_id,
            subject_identity=self.subject_authority,
            agent_identity=self.agent_authority,
            oracle_identity=self.oracle_authority,
            harness_identity=self.harness_authority,
            environment_identity=self.environment_authority,
            mutation_identity=self.mutation_authority,
        )

    def initial_outcome(self) -> tuple[TrialStatus | None, str | None]:
        if not self.subject_authority["available"]:
            reason = self.subject_prepare.payload.get("reason")
            return (
                TrialStatus.INCOMPLETE,
                str(reason)
                if isinstance(reason, str) and reason
                else "subject unavailable or preparation failed",
            )
        if not self.agent_authority["available"]:
            reason = self.agent_prepare.payload.get("reason")
            return (
                TrialStatus.INCOMPLETE,
                str(reason)
                if isinstance(reason, str) and reason
                else "agent unavailable or preparation failed",
            )
        if not self.oracle_authority["healthy"]:
            return (
                TrialStatus.INVALID,
                "independent oracle healthcheck failed",
            )
        return None, None


def _git_value(root: Path, argv: tuple[str, ...]) -> str:
    result = run_bounded(
        repository_root=root,
        argv=argv,
        limits=ProcessLimits(
            timeout_seconds=30.0,
            max_stdout_bytes=1_000_000,
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
        raise TrialAdmissionError(
            f"cannot establish harness git authority: {' '.join(argv)}"
        )
    return result.stdout.decode("utf-8", errors="strict").strip()


def harness_identity(root: Path) -> dict[str, Any]:
    root = root.resolve()
    commit = _git_value(root, ("git", "rev-parse", "HEAD"))
    tree = _git_value(root, ("git", "rev-parse", "HEAD^{tree}"))
    tracked_status = _git_value(
        root,
        ("git", "status", "--porcelain", "--untracked-files=no"),
    )
    if tracked_status:
        raise TrialAdmissionError("benchmark harness tracked files are dirty")
    return {
        "repository": "Hugloss/agentsCookbook",
        "commit": commit,
        "tree": tree,
        "contract": "generic-benchmark-runner-v1",
    }


def runtime_environment_identity() -> dict[str, Any]:
    return {
        "isolation_contract": (
            "codex-isolated-or-opencode-native-config-v2"
        ),
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
            "native_config_sha256": prepared.payload.get(
                "native_config_sha256"
            ),
            "native_mcp_servers": prepared.payload.get(
                "native_mcp_servers"
            ),
        },
    }


def _oracle_authority(oracle, health: Observation) -> dict[str, Any]:
    return {
        "declared": _declared(oracle.identity()),
        "healthy": bool(health.payload.get("healthy")),
    }


def _resolve_condition(
    suite: SuiteDefinition,
    condition_id: str,
) -> dict[str, Any]:
    condition = next(
        (
            value
            for value in suite.experiment["conditions"]
            if value["id"] == condition_id
        ),
        None,
    )
    if condition is None:
        raise TrialAdmissionError(f"unknown condition: {condition_id}")
    return condition


@contextmanager
def admit_trial(
    *,
    suite: SuiteDefinition,
    task_id: str,
    condition_id: str,
    trial_index: int,
    harness_root: Path,
    cache_root: Path,
    work_root: Path,
    local_source: Path | None = None,
    codex_auth: Path | None = None,
) -> Iterator[TrialAdmission]:
    task = suite.tasks[task_id]
    condition = _resolve_condition(suite, condition_id)
    if trial_index < 0 or trial_index >= int(condition["trials"]):
        raise TrialAdmissionError(
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
        workspace = run_root / "workspace"
        materialize_repository(
            repository=task["repository"],
            destination=workspace,
            cache_root=cache_root,
            local_source=local_source,
        )
        control_root = run_root / "control"
        environment = isolated_environment(control_root)
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
        auth_mode = (
            seed_codex_auth(context, codex_auth)
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
        )
        subject_prepare = subject.prepare(context)
        agent_prepare = agent.prepare(context, subject)
        oracle_health = oracle.healthcheck(context)

        yield TrialAdmission(
            task=task,
            condition=condition,
            expanded_condition=expanded_condition,
            trial_index=trial_index,
            seed=seed,
            definition_id=definition,
            context=context,
            mutation=mutation,
            admitted_state=admitted_state,
            subject=subject,
            agent=agent,
            oracle=oracle,
            subject_prepare=subject_prepare,
            agent_prepare=agent_prepare,
            oracle_health=oracle_health,
            subject_authority=_subject_authority(subject, subject_prepare),
            agent_authority=_agent_authority(agent, agent_prepare),
            oracle_authority=_oracle_authority(oracle, oracle_health),
            harness_authority=harness_identity(harness_root),
            environment_authority=runtime_environment_identity(),
            mutation_authority=mutation.payload.get("identity"),
            auth_mode=auth_mode,
        )
