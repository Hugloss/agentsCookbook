"""Independent command oracle with mandatory positive healthcheck."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from benchmarks.harness.model import Observation, ParticipantIdentity
from benchmarks.harness.process import run

@dataclass(frozen=True)
class CommandOracle:
    participant_id: str; version: str; health_argv: tuple[str,...]; grade_argv: tuple[str,...]; timeout_seconds: int=60
    def identity(self): return ParticipantIdentity(self.participant_id,"oracle",self.version)
    def healthcheck(self,workspace):
        r=run(self.health_argv,cwd=Path(workspace),timeout_seconds=self.timeout_seconds)
        ok=(not r.timed_out and r.exit_code==0)
        return Observation({"healthy":ok,"exit_code":r.exit_code,"timed_out":r.timed_out},r.stdout+r.stderr,{"duration_ms":r.duration_ms})
    def grade(self,workspace,observation):
        r=run(self.grade_argv,cwd=Path(workspace),timeout_seconds=self.timeout_seconds)
        return Observation({"passed":not r.timed_out and r.exit_code==0,"exit_code":r.exit_code,"timed_out":r.timed_out},r.stdout+r.stderr,{"duration_ms":r.duration_ms})
