from __future__ import annotations

from collections.abc import Mapping, Sequence

SCHEMA = "agentscookbook-working-evidence/v1"
SECTIONS = ("task", "known", "decisions", "remaining")


def new_working_evidence(*, goal: str) -> dict[str, object]:
    """Return the intentionally small, file-oriented task-state document."""
    return {
        "schema": SCHEMA,
        "task": {"goal": goal},
        "known": [],
        "decisions": [],
        "remaining": [],
    }


def validate_working_evidence(payload: object) -> list[str]:
    """Validate task-local evidence without creating a persistence service."""
    if not isinstance(payload, Mapping):
        return ["working evidence root must be an object"]

    errors: list[str] = []
    if payload.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA!r}")

    task = payload.get("task")
    if not isinstance(task, Mapping):
        errors.append("task must be an object")
    elif not isinstance(task.get("goal"), str) or not str(task.get("goal")).strip():
        errors.append("task.goal must be a non-empty string")

    for key in ("known", "decisions", "remaining"):
        value = payload.get(key)
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            errors.append(f"{key} must be a list")

    forbidden = {
        "repository_graph",
        "ownership_graph",
        "test_graph",
        "repository_cache",
        "verification_cache",
        "repository_snapshot",
    }
    leaked = sorted(forbidden & set(payload))
    if leaked:
        errors.append(
            "working evidence must not duplicate repository intelligence: "
            + ", ".join(leaked)
        )
    return errors
