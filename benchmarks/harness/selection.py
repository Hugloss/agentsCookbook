"""Select frozen benchmark definitions consistently across CLI surfaces."""
from __future__ import annotations

from typing import Any

from benchmarks.harness.suite import SuiteDefinition


class SelectionError(ValueError):
    pass


def select_definitions(
    suite: SuiteDefinition,
    *,
    tasks: tuple[str, ...] = (),
    agents: tuple[str, ...] = (),
    subjects: tuple[str, ...] = (),
    condition: str | None = None,
) -> list[dict[str, Any]]:
    if condition and (agents or subjects):
        raise SelectionError("--condition cannot be combined with --agent or --subject")
    for label, requested, known in (
        ("task", tasks, suite.tasks),
        ("agent", agents, suite.agents),
        ("subject", subjects, suite.subjects),
    ):
        unknown = sorted(set(requested) - set(known))
        if unknown:
            raise SelectionError(f"unknown {label} ID(s): {', '.join(unknown)}")
    conditions = {row["id"]: row for row in suite.experiment["conditions"]}
    if condition and condition not in conditions:
        raise SelectionError(f"unknown condition ID: {condition}")

    chosen_subjects = set(subjects)
    if chosen_subjects and chosen_subjects != {"none"}:
        chosen_subjects.add("none")
    rows = []
    for row in suite.trial_definitions():
        frozen = conditions[row["condition_id"]]
        if tasks and row["task_id"] not in tasks:
            continue
        if condition and row["condition_id"] != condition:
            continue
        if agents and frozen["agent"] not in agents:
            continue
        if chosen_subjects and frozen["subject"] not in chosen_subjects:
            continue
        rows.append(row)
    if not rows:
        raise SelectionError("no trials matched the requested filters")
    return rows
