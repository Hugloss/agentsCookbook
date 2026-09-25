"""Generic command-backed subjects plus the bare control."""
from __future__ import annotations
import json, shlex
from dataclasses import dataclass
from pathlib import Path
from benchmarks.harness.model import Observation, ParticipantIdentity
from benchmarks.harness.process import run

@dataclass(frozen=True)
class NoneSubject:
    def identity(self): return ParticipantIdentity("none","control","1")
    def prepare(self,workspace): return Observation({"available":False},"")
    def query(self,workspace,prompt): return Observation({"available":False,"invoked":False},"")
    def post_change(self,workspace,changed_paths): return Observation({"available":False},"")
    def cleanup(self,workspace): return Observation({},"")

@dataclass(frozen=True)
class CommandSubject:
    participant_id: str; version: str; query_argv: tuple[str,...]; timeout_seconds: int=60
    def identity(self): return ParticipantIdentity(self.participant_id,"repository_intelligence",self.version,{"argv":self.query_argv})
    def prepare(self,workspace): return Observation({"available":True},"")
    def query(self,workspace,prompt):
        argv=tuple(part.replace("{prompt}",prompt) for part in self.query_argv)
        result=run(argv,cwd=Path(workspace),timeout_seconds=self.timeout_seconds)
        payload={"available":True,"invoked":True,"exit_code":result.exit_code,"timed_out":result.timed_out}
        return Observation(payload,result.stdout,{"duration_ms":result.duration_ms,"response_bytes":len(result.stdout.encode())})
    def post_change(self,workspace,changed_paths): return Observation({"changed_paths":list(changed_paths)},"")
    def cleanup(self,workspace): return Observation({},"")

def command_from_string(participant_id: str, version: str, command: str, timeout_seconds: int=60) -> CommandSubject:
    return CommandSubject(participant_id,version,tuple(shlex.split(command)),timeout_seconds)
