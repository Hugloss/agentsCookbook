"""Product-neutral benchmark contracts. Standard-library only."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol


class TrialStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCOMPLETE = "INCOMPLETE"
    INVALID = "INVALID"
    CONTAMINATED = "CONTAMINATED"
    NO_QUALIFYING_DEFECT = "NO_QUALIFYING_DEFECT"


@dataclass(frozen=True)
class ParticipantIdentity:
    participant_id: str
    kind: str
    version: str
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Observation:
    payload: dict[str, Any]
    raw: str
    measurements: dict[str, int | float | str | bool] = field(default_factory=dict)


@dataclass(frozen=True)
class TrialContext:
    workspace: Path
    environment: dict[str, str]


class SubjectAdapter(Protocol):
    def identity(self) -> ParticipantIdentity: ...
    def prepare(self, context: TrialContext) -> Observation: ...
    def query(self, context: TrialContext, prompt: str) -> Observation: ...
    def post_change(self, context: TrialContext, changed_paths: tuple[str, ...]) -> Observation: ...
    def cleanup(self, context: TrialContext) -> Observation: ...


class AgentAdapter(Protocol):
    def identity(self) -> ParticipantIdentity: ...
    def run(
        self,
        context: TrialContext,
        prompt: str,
        exposed_subject: SubjectAdapter | None,
    ) -> Observation: ...


class OracleAdapter(Protocol):
    def identity(self) -> ParticipantIdentity: ...
    def healthcheck(self, context: TrialContext) -> Observation: ...
    def grade(self, context: TrialContext, observation: Observation) -> Observation: ...
