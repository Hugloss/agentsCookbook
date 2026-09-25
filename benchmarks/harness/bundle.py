"""Verification for published benchmark evidence bundles."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from benchmarks.harness.identity import canonical_json
from benchmarks.harness.receipt import is_complete_receipt


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def verify_bundle(directory: Path) -> tuple[bool, str | None]:
    if directory.is_symlink() or not directory.is_dir():
        return False, "result bundle is not a real directory"
    if not is_complete_receipt(directory):
        return False, "result receipt is incomplete or invalid"
    try:
        receipt = json.loads(
            (directory / "result.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return False, "result receipt cannot be parsed"

    trial_id = receipt.get("trial_id")
    if not isinstance(trial_id, str) or directory.name != trial_id:
        return False, "result directory does not match trial_id"

    execution = receipt.get("execution")
    if not isinstance(execution, dict):
        return False, "result receipt has no execution evidence"
    artifacts = execution.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        return False, "result receipt has no artifact manifest"

    loaded: dict[str, bytes] = {}
    for name, evidence in artifacts.items():
        if not isinstance(name, str) or not isinstance(evidence, dict):
            return False, "artifact manifest entry is invalid"
        relative = evidence.get("path")
        if not isinstance(relative, str) or not relative:
            return False, f"artifact {name} has no path"
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            return False, f"artifact {name} path escapes result bundle"
        path = directory / candidate
        if path.is_symlink():
            return False, f"artifact {name} must not be a symlink"
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(directory.resolve())
        except (OSError, ValueError):
            return False, f"artifact {name} resolves outside result bundle"
        try:
            payload = path.read_bytes()
        except OSError:
            return False, f"artifact {name} is missing"
        if evidence.get("bytes") != len(payload):
            return False, f"artifact {name} byte count mismatch"
        if evidence.get("sha256") != _sha256(payload):
            return False, f"artifact {name} checksum mismatch"
        loaded[name] = payload

    declared_files = {
        "result.json",
        "result.sha256",
        "completion.json",
        *(str(value["path"]) for value in artifacts.values()),
    }
    actual_files = {path.name for path in directory.iterdir()}
    if actual_files != declared_files:
        return False, "result bundle contains undeclared or missing files"

    events_evidence = execution.get("events")
    if not isinstance(events_evidence, dict):
        return False, "result receipt has no sealed event evidence"
    events = loaded.get("events")
    seal = loaded.get("events_seal")
    if events is None or seal is None:
        return False, "event artifacts are missing from manifest"
    if events_evidence.get("events_sha256") != _sha256(events):
        return False, "event stream checksum differs from receipt"
    lines = events.splitlines()
    if events_evidence.get("event_count") != len(lines):
        return False, "event count differs from receipt"
    for sequence, line in enumerate(lines):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return False, f"event {sequence} is not valid JSON"
        if event.get("trial_id") != trial_id:
            return False, f"event {sequence} trial identity mismatch"
        if event.get("sequence") != sequence:
            return False, f"event {sequence} sequence mismatch"
    try:
        seal_value = json.loads(seal)
    except json.JSONDecodeError:
        return False, "event seal is not valid JSON"
    if seal_value != events_evidence:
        return False, "event seal differs from receipt"
    if canonical_json(seal_value) != seal:
        return False, "event seal is not canonical JSON"
    return True, None
