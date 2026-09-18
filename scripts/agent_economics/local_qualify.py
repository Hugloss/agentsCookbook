from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .command_runner import run_named_command
from .loop_state import LoopBudget, LoopSession, semantic_identity
from .repair_packet import build_repair_packet


def _source_identity(root: Path, changed: list[str]) -> str:
    entries: list[dict[str, object]] = []
    for raw in sorted(changed):
        path = root / raw
        entries.append({
            "path": raw,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None,
        })
    return semantic_identity(entries)


def qualify_local(
    *,
    repository_root: Path,
    manifest_path: Path,
    command_names: list[str],
    changed_paths: list[str] | None = None,
    selected_paths: list[str] | None = None,
    state_path: Path = Path(".agent-artifacts/local-loop.json"),
) -> dict[str, object]:
    root = repository_root.resolve()
    changed = changed_paths or []
    stages: list[dict[str, object]] = []
    authority = "LOCAL_INCOMPLETE"
    state_target = state_path if state_path.is_absolute() else root / state_path
    with LoopSession(state_target, budget=LoopBudget()) as session:
        for name in command_names:
            result = run_named_command(
                repository_root=root,
                manifest_path=manifest_path,
                name=name,
                selected_paths=selected_paths or (),
            )
            packet = build_repair_packet(
                repository_root=root,
                command_result=result,
                changed_paths=changed,
            )
            state = session.record(
                source_identity=_source_identity(root, changed),
                command_identity=str(result["command"]["identity"]),
                failure_identity=str(result["failure_identity"]),
                evidence_identity=str(packet["evidence_identity"]),
                stdout_bytes=int(result["execution"]["stdout_bytes"]),
                stderr_bytes=int(result["execution"]["stderr_bytes"]),
            )
            stages.append({
                "command": name,
                "stage": result["command"]["stage"],
                "status": result["status"],
                "classification": result["classification"],
                "failure_identity": result["failure_identity"],
                "repair_packet": packet if result["status"] != "PASS" else None,
            })
            if result["status"] != "PASS":
                authority = "LOCAL_FAILED"
                return {
                    "schema": {"name": "agent-economics-local-qualification", "version": 1},
                    "status": authority,
                    "ci_status": "NOT_RUN",
                    "stages": stages,
                    "loop": {"stop_reason": state.get("stop_reason"), "state_identity": state.get("state_identity")},
                }
            if state.get("stop_reason"):
                return {
                    "schema": {"name": "agent-economics-local-qualification", "version": 1},
                    "status": "LOCAL_INCOMPLETE",
                    "ci_status": "NOT_RUN",
                    "stages": stages,
                    "loop": {"stop_reason": state.get("stop_reason"), "state_identity": state.get("state_identity")},
                }
        if stages and stages[-1]["stage"] == "repository":
            authority = "LOCAL_QUALIFIED"
        return {
            "schema": {"name": "agent-economics-local-qualification", "version": 1},
            "status": authority,
            "ci_status": "NOT_RUN",
            "stages": stages,
            "loop": {"stop_reason": None},
        }


def main(argv: list[str] | None = None) -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Run staged repository-local qualification.")
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--command", action="append", required=True)
    parser.add_argument("--changed-path", action="append", default=[])
    parser.add_argument("--selected-path", action="append", default=[])
    parser.add_argument("--state-path", type=Path, default=Path(".agent-artifacts/local-loop.json"))
    args = parser.parse_args(argv)
    payload = qualify_local(
        repository_root=args.repository_root,
        manifest_path=args.manifest,
        command_names=args.command,
        changed_paths=args.changed_path,
        selected_paths=args.selected_path,
        state_path=args.state_path,
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
