"""Bounded subprocess execution with observable receipts."""
from __future__ import annotations
import os, subprocess, time
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class ProcessResult:
    argv: tuple[str,...]; cwd: str; exit_code: int|None; stdout: str; stderr: str
    duration_ms: int; timed_out: bool

def run(argv: tuple[str,...], *, cwd: Path, timeout_seconds: int, env: dict[str,str]|None=None) -> ProcessResult:
    started=time.monotonic()
    effective=os.environ.copy()
    if env: effective.update(env)
    try:
        p=subprocess.run(argv,cwd=cwd,env=effective,text=True,capture_output=True,timeout=timeout_seconds,check=False,start_new_session=True)
        return ProcessResult(argv,str(cwd),p.returncode,p.stdout,p.stderr,int((time.monotonic()-started)*1000),False)
    except subprocess.TimeoutExpired as exc:
        return ProcessResult(argv,str(cwd),None,exc.stdout or "",exc.stderr or "",int((time.monotonic()-started)*1000),True)
