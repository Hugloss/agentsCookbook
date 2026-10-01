"""Offline score projection over frozen benchmark execution evidence."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

from benchmarks.adapters.oracles import RepositoryLocationOracle
from benchmarks.harness.identity import score_projection_id
from benchmarks.harness.model import Observation, TrialContext


class RegradeError(ValueError):
    pass


def regrade_repository_location_receipt(
    receipt: dict[str, Any],
    oracle: RepositoryLocationOracle,
) -> dict[str, Any]:
    """Recompute repository-location scoring without rerunning the agent."""
    execution = receipt.get("execution")
    if not isinstance(execution, dict):
        raise RegradeError("receipt has no execution evidence")

    evidence_identity = execution.get("evidence_identity")
    answer = execution.get("agent_answer")
    workspace_root = execution.get("workspace_root")
    if not isinstance(evidence_identity, str) or not evidence_identity:
        raise RegradeError("receipt has no execution evidence identity")
    if not isinstance(workspace_root, str) or not workspace_root:
        raise RegradeError("receipt has no recorded workspace root")

    context = TrialContext(
        workspace=Path(workspace_root),
        control_root=Path(workspace_root),
        environment={},
    )
    health = oracle.healthcheck(context)
    if health.payload.get("healthy") is not True:
        raise RegradeError(
            str(health.payload.get("reason") or "offline oracle healthcheck failed")
        )

    observation = Observation({"final_message": answer}, "")
    grade = oracle.grade(context, observation)
    declared = dataclasses.asdict(oracle.identity())
    return {
        "execution_evidence_id": evidence_identity,
        "projection_identity": score_projection_id(
            execution_evidence=evidence_identity,
            oracle_identity=declared,
        ),
        "oracle": declared,
        "oracle_grade": grade.payload,
    }
