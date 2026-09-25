"""Resumable campaign identities that bind observed execution authority."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .identity import definition_id, execution_id
from .receipt import is_complete_receipt


@dataclass(frozen=True)
class TrialSpec:
    experiment: dict[str, Any]
    task: dict[str, Any]
    condition: dict[str, Any]
    trial: int
    seed: int
    subject_identity: dict[str, Any]
    agent_identity: dict[str, Any]
    oracle_identity: dict[str, Any]
    harness_identity: dict[str, Any]
    environment_identity: dict[str, Any]
    mutation_identity: dict[str, Any] | None = None

    @property
    def definition_id(self) -> str:
        return definition_id(
            experiment=self.experiment,
            task=self.task,
            condition=self.condition,
            trial=self.trial,
            seed=self.seed,
        )

    @property
    def id(self) -> str:
        return execution_id(
            definition=self.definition_id,
            subject_identity=self.subject_identity,
            agent_identity=self.agent_identity,
            oracle_identity=self.oracle_identity,
            harness_identity=self.harness_identity,
            environment_identity=self.environment_identity,
            mutation_identity=self.mutation_identity,
        )


def pending(specs: list[TrialSpec], results_root: Path) -> list[TrialSpec]:
    return [spec for spec in specs if not is_complete_receipt(results_root / spec.id)]
