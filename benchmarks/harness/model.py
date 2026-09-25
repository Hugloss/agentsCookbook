"""Product-neutral benchmark contracts. Standard-library only."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

class TrialStatus(str, Enum):
    PASS="PASS"; FAIL="FAIL"; INCOMPLETE="INCOMPLETE"; INVALID="INVALID"
    CONTAMINATED="CONTAMINATED"; NO_QUALIFYING_DEFECT="NO_QUALIFYING_DEFECT"

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

class SubjectAdapter(Protocol):
    def identity(self) -> ParticipantIdentity: ...
    def prepare(self, workspace: str) -> Observation: ...
    def query(self, workspace: str, prompt: str) -> Observation: ...
    def post_change(self, workspace: str, changed_paths: tuple[str, ...]) -> Observation: ...
    def cleanup(self, workspace: str) -> Observation: ...

class AgentAdapter(Protocol):
    def identity(self) -> ParticipantIdentity: ...
    def run(self, workspace: str, prompt: str, exposed_subject: SubjectAdapter | None) -> Observation: ...

class OracleAdapter(Protocol):
    def identity(self) -> ParticipantIdentity: ...
    def healthcheck(self, workspace: str) -> Observation: ...
    def grade(self, workspace: str, observation: Observation) -> Observation: ...
