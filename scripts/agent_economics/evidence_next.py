from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path
from typing import Any


class EvidenceNextError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceNextError(f"cannot read artifact: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceNextError("artifact must be a JSON object")
    return value


def _candidate(payload: dict[str, Any], target: str | None) -> dict[str, Any]:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise EvidenceNextError("artifact has no candidates")
    if target is None:
        if len(candidates) != 1:
            raise EvidenceNextError("artifact has multiple candidates; --target is required")
        candidate = candidates[0]
        if not isinstance(candidate, dict):
            raise EvidenceNextError("candidate must be an object")
        return candidate
    matches = [row for row in candidates if isinstance(row, dict) and row.get("target") == target]
    if len(matches) != 1:
        raise EvidenceNextError(f"target must identify exactly one candidate: {target}")
    return matches[0]


def next_evidence(
    payload: dict[str, Any], *, target: str | None = None, profile: dict[str, Any] | None = None
) -> dict[str, Any]:
    schema = payload.get("schema")
    if not isinstance(schema, dict) or schema.get("name") != "agent-economics-probe":
        raise EvidenceNextError("unsupported artifact schema")
    candidate = _candidate(payload, target)
    required = candidate.get("required_next_evidence")
    if not isinstance(required, list) or not required:
        raise EvidenceNextError("candidate has no required next evidence")
    if len(required) != 1:
        raise EvidenceNextError("candidate has multiple required next evidence items; explicit selection is required")
    item = required[0]
    if not isinstance(item, dict):
        raise EvidenceNextError("required next evidence must be an object")
    kind = item.get("kind")
    candidate_target = candidate.get("target")
    if not isinstance(kind, str) or not isinstance(candidate_target, str):
        raise EvidenceNextError("next evidence kind/target is invalid")

    command: list[str] | None = None
    unresolved: list[str] = []
    if kind == "test_focus":
        if profile is None:
            unresolved.append("profile")
        else:
            repository = profile.get("repository")
            if not isinstance(repository, dict):
                raise EvidenceNextError("profile has no repository section")
            packages = repository.get("package_roots")
            tests = repository.get("test_roots")
            if not isinstance(packages, list) or len(packages) != 1:
                unresolved.append("single_package_root")
            if not isinstance(tests, list) or len(tests) != 1:
                unresolved.append("single_test_root")
            quality_debt = profile.get("quality_debt")
            if isinstance(quality_debt, dict):
                root_evidence = quality_debt.get("analysis_root_evidence")
                if isinstance(root_evidence, list) and any(
                    isinstance(row, dict) and row.get("status") == "PROPOSED"
                    for row in root_evidence
                ):
                    unresolved.append("profile_has_unreviewed_proposed_roots")
            if not unresolved:
                command = [
                    "python", "-m", "agent_economics", "test-focus",
                    "--repository-root", ".",
                    "--source-root", str(packages[0]),
                    "--tests-root", str(tests[0]),
                    "--changed-path", candidate_target,
                    "--artifact-path", ".agent-artifacts/test-focus.json",
                ]
    else:
        unresolved.append(f"unsupported_next_evidence:{kind}")

    return {
        "schema": {"name": "agent-economics-next-evidence", "version": 1},
        "target": candidate_target,
        "current_probe": payload.get("tool", {}).get("name") if isinstance(payload.get("tool"), dict) else None,
        "next_evidence": {"kind": kind, "reason": item.get("reason")},
        "command": command,
        "command_display": shlex.join(command) if command is not None else None,
        "unresolved": unresolved,
        "interpretation": {
            "translates_existing_evidence_requirement_only": True,
            "does_not_authorize_edit": True,
            "does_not_execute_command": True,
            "profile_is_configuration_input_not_policy_authority": True,
            "proposed_profile_evidence_is_not_accepted_configuration": True,
        },
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Translate an artifact's existing next-evidence requirement into a bounded command.")
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--target", default=None)
    parser.add_argument("--profile", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        payload = _load(args.artifact)
        profile = _load(args.profile) if args.profile is not None else None
        print(json.dumps(next_evidence(payload, target=args.target, profile=profile), indent=2, sort_keys=True))
    except EvidenceNextError as exc:
        raise SystemExit(f"next: {exc}") from exc


if __name__ == "__main__":
    main()
