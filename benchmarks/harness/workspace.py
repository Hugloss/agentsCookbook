"""Fresh-workspace materialization and contamination evidence."""
from __future__ import annotations
import hashlib, os, shutil, subprocess
from pathlib import Path

IGNORED={".git"}

def _files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_file() and not any(part in IGNORED for part in path.relative_to(root).parts):
            yield path

def snapshot(root: Path) -> dict[str,str]:
    out={}
    for path in _files(root):
        h=hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
        out[path.relative_to(root).as_posix()]=h.hexdigest()
    return out

def materialize_git(*, source: Path, commit: str, destination: Path) -> str:
    if destination.exists(): raise FileExistsError(destination)
    subprocess.run(("git","clone","--no-hardlinks",str(source),str(destination)),check=True,capture_output=True,text=True)
    subprocess.run(("git","checkout","--detach",commit),cwd=destination,check=True,capture_output=True,text=True)
    actual=subprocess.run(("git","rev-parse","HEAD"),cwd=destination,check=True,capture_output=True,text=True).stdout.strip()
    if actual != commit: raise RuntimeError(f"workspace authority mismatch: expected {commit}, got {actual}")
    return actual

def diff_snapshots(before: dict[str,str], after: dict[str,str]) -> dict[str,list[str]]:
    b=set(before); a=set(after)
    return {"added":sorted(a-b),"removed":sorted(b-a),"changed":sorted(p for p in a&b if before[p]!=after[p])}
