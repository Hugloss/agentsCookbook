"""Minimal resumable campaign primitives."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from .identity import trial_id

@dataclass(frozen=True)
class TrialSpec:
    experiment: dict[str,Any]; task: dict[str,Any]; condition: dict[str,Any]; trial: int; seed: int
    @property
    def id(self): return trial_id(experiment=self.experiment,task=self.task,condition=self.condition,trial=self.trial,seed=self.seed)

def pending(specs: list[TrialSpec], results_root: Path) -> list[TrialSpec]:
    return [s for s in specs if not (results_root/s.id/"result.json").exists()]
