"""Frozen benchmark-suite loading and semantic validation."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benchmarks.harness.identity import definition_id


class SuiteError(ValueError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SuiteError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SuiteError(f"{path} must contain one JSON object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class SuiteDefinition:
    root: Path
    experiment: dict[str, Any]
    tasks: dict[str, dict[str, Any]]
    subjects: dict[str, dict[str, Any]]
    agents: dict[str, dict[str, Any]]

    def expanded_condition(self, condition: dict[str, Any]) -> dict[str, Any]:
        subject_id = str(condition["subject"])
        agent_id = str(condition["agent"])
        return {
            **condition,
            "subject_definition": self.subjects[subject_id],
            "agent_definition": self.agents[agent_id],
        }

    def trial_definitions(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for task_id in self.experiment["tasks"]:
            task = self.tasks[str(task_id)]
            for condition in self.experiment["conditions"]:
                expanded = self.expanded_condition(condition)
                for trial in range(int(condition["trials"])):
                    seed = int(condition["seed"]) + trial
                    rows.append(
                        {
                            "task_id": task_id,
                            "condition_id": condition["id"],
                            "trial": trial,
                            "seed": seed,
                            "definition_id": definition_id(
                                experiment=self.experiment,
                                task=task,
                                condition=expanded,
                                trial=trial,
                                seed=seed,
                            ),
                        }
                    )
        return rows


def load_suite(root: Path) -> SuiteDefinition:
    root = root.resolve()
    experiment = _load_json(root / "experiment.json")

    tasks: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "tasks").glob("*.json")):
        value = _load_json(path)
        task_id = str(value.get("id", ""))
        if not task_id or task_id in tasks:
            raise SuiteError(f"invalid or duplicate task id in {path}")
        tasks[task_id] = value

    subjects: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "subjects").glob("*.json")):
        value = _load_json(path)
        subject_id = str(value.get("id", ""))
        if not subject_id or subject_id in subjects:
            raise SuiteError(f"invalid or duplicate subject id in {path}")
        subjects[subject_id] = value

    agents: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "agents").glob("*.json")):
        value = _load_json(path)
        agent_id = str(value.get("id", ""))
        if not agent_id or agent_id in agents:
            raise SuiteError(f"invalid or duplicate agent id in {path}")
        agents[agent_id] = value

    if not tasks or not subjects or not agents:
        raise SuiteError("suite requires tasks, subjects and agents")

    for task_id in experiment.get("tasks", []):
        if str(task_id) not in tasks:
            raise SuiteError(f"experiment references missing task: {task_id}")

    for condition in experiment.get("conditions", []):
        if condition.get("subject") not in subjects:
            raise SuiteError(
                f"condition {condition.get('id')} references missing subject"
            )
        if condition.get("agent") not in agents:
            raise SuiteError(
                f"condition {condition.get('id')} references missing agent"
            )
        if int(condition.get("trials", 0)) < 1:
            raise SuiteError(f"condition {condition.get('id')} has no trials")
        if "seed" not in condition:
            raise SuiteError(f"condition {condition.get('id')} has no seed")

    for task in tasks.values():
        repository = task.get("repository", {})
        for field in ("commit", "tree"):
            value = str(repository.get(field, ""))
            if len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
                raise SuiteError(f"task {task['id']} has invalid repository {field}")
        mutation = task.get("mutation")
        if mutation is not None:
            artifact = (root / str(mutation["artifact"])).resolve()
            try:
                artifact.relative_to(root)
            except ValueError as exc:
                raise SuiteError(
                    f"task {task['id']} mutation escapes suite root"
                ) from exc
            if not artifact.is_file():
                raise SuiteError(f"task {task['id']} mutation artifact missing")
            actual = _sha256(artifact)
            if actual != mutation["sha256"]:
                raise SuiteError(
                    f"task {task['id']} mutation checksum mismatch: {actual}"
                )
            if not mutation.get("changed_paths"):
                raise SuiteError(
                    f"task {task['id']} mutation must freeze changed_paths"
                )
        contamination = task.get("contamination")
        if not isinstance(contamination, dict):
            raise SuiteError(
                f"task {task['id']} must define contamination allowances"
            )
        if "allowed_change_globs" not in contamination:
            raise SuiteError(
                f"task {task['id']} must define allowed_change_globs"
            )
        if "allowed_generated_globs" not in contamination:
            raise SuiteError(
                f"task {task['id']} must define allowed_generated_globs"
            )

    return SuiteDefinition(
        root=root,
        experiment=experiment,
        tasks=tasks,
        subjects=subjects,
        agents=agents,
    )
