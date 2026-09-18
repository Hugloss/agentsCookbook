from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


_LOCATION = re.compile(r"(?P<path>(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+):(?P<line>[1-9][0-9]*)")


def build_repair_packet(
    *,
    repository_root: Path,
    command_result: dict[str, object],
    changed_paths: list[str] | None = None,
    max_excerpt_chars: int = 12_000,
    max_anchors: int = 20,
) -> dict[str, object]:
    if max_excerpt_chars < 1 or max_anchors < 1:
        raise ValueError("repair packet bounds must be positive")
    stdout = str(command_result.get("stdout", ""))
    stderr = str(command_result.get("stderr", ""))
    diagnostic = (stderr + "\n" + stdout).strip()
    excerpt = diagnostic[:max_excerpt_chars]
    anchors: list[dict[str, object]] = []
    seen: set[tuple[str, int]] = set()
    for match in _LOCATION.finditer(excerpt):
        item = (match.group("path"), int(match.group("line")))
        if item in seen:
            continue
        seen.add(item)
        anchors.append({"path": item[0], "line": item[1]})
        if len(anchors) >= max_anchors:
            break
    core = {
        "classification": command_result.get("classification"),
        "failure_identity": command_result.get("failure_identity"),
        "command": command_result.get("command"),
        "changed_paths": sorted(changed_paths or []),
        "anchors": anchors,
        "diagnostic_excerpt": excerpt,
        "diagnostic_truncated": len(diagnostic) > len(excerpt),
        "authority": {
            "repair_performed": False,
            "verification_complete": False,
            "ci_status": "NOT_RUN",
        },
        "required_next_evidence": [
            {"kind": "inspect_failure_anchors_and_changed_contracts"}
        ],
    }
    core["evidence_identity"] = "sha256:" + hashlib.sha256(
        json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return core
