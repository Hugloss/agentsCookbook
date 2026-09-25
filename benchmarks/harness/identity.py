"""Stable identities for frozen benchmark inputs."""
from __future__ import annotations
import hashlib, json
from typing import Any

def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)+"\n").encode()

def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()

def trial_id(*, experiment: dict[str, Any], task: dict[str, Any], condition: dict[str, Any], trial: int, seed: int) -> str:
    return digest({"experiment":experiment,"task":task,"condition":condition,"trial":trial,"seed":seed})
