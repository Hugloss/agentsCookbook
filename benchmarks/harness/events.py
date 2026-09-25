"""Append-only JSONL event stream."""
from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any
from .identity import canonical_json

def append_event(path: Path, event: dict[str,Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o644)
    with os.fdopen(fd,"ab") as stream:
        stream.write(canonical_json(event)); stream.flush(); os.fsync(stream.fileno())
