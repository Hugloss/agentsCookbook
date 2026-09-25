"""Stable identities for frozen benchmark definitions and observed executions."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def definition_id(
    *,
    experiment: dict[str, Any],
    task: dict[str, Any],
    condition: dict[str, Any],
    trial: int,
    seed: int,
) -> str:
    return digest(
        {
            "experiment": experiment,
            "task": task,
            "condition": condition,
            "trial": trial,
            "seed": seed,
        }
    )


def execution_id(
    *,
    definition: str,
    subject_identity: dict[str, Any],
    agent_identity: dict[str, Any],
    oracle_identity: dict[str, Any],
    harness_identity: dict[str, Any],
    environment_identity: dict[str, Any],
    mutation_identity: dict[str, Any] | None,
) -> str:
    return digest(
        {
            "definition_id": definition,
            "subject": subject_identity,
            "agent": agent_identity,
            "oracle": oracle_identity,
            "harness": harness_identity,
            "environment": environment_identity,
            "mutation": mutation_identity,
        }
    )
