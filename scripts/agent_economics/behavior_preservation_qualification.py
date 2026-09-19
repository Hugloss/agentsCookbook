from __future__ import annotations

import argparse
import json
from pathlib import Path

from .behavior_preservation import (
    EVIDENCE_REQUIRED,
    READY,
    TEST_STRENGTHENING_REQUIRED,
    behavior_preservation_readiness,
)


def _boundary(
    identity: str = "public-normalization",
    *,
    classification: str = "direct",
    freshness: str = "fresh",
) -> dict[str, object]:
    return {
        "identity": identity,
        "classification": classification,
        "freshness": freshness,
        "provider_reference": {
            "provider": "test-focus",
            "evidence_identity": f"sha256:{identity}",
        },
    }


def _tests() -> list[dict[str, object]]:
    return [{"path": "tests/test_core.py", "evidence_identity": "sha256:test-core"}]


def _receipt(
    *,
    source_identity: str = "sha256:source-a",
    status: str = "PASS",
    test_ids: list[str] | None = None,
) -> dict[str, object]:
    return {
        "source_identity": source_identity,
        "status": status,
        "test_evidence_identities": test_ids or ["sha256:test-core"],
        "execution_identity": "sha256:execution-a",
    }


def _run(**overrides: object) -> dict[str, object]:
    args: dict[str, object] = {
        "target": "src/pkg/core.py",
        "source_identity": "sha256:source-a",
        "boundaries": [_boundary()],
        "test_references": _tests(),
        "execution_receipt": _receipt(),
        "repository_gates": [{"name": "full", "command": "uv run pytest"}],
    }
    args.update(overrides)
    return behavior_preservation_readiness(**args)  # type: ignore[arg-type]


def qualify(artifact_path: Path | None = None) -> dict[str, object]:
    failures: list[str] = []

    ready = _run()
    if ready["status"] != READY:
        failures.append("complete fresh direct evidence did not become READY")
    authority = ready.get("authority", {})
    if not isinstance(authority, dict) or authority.get("edit_authorized") is not False:
        failures.append("READY incorrectly authorized an edit")
    if isinstance(authority, dict) and authority.get("refactor_safety_proven") is not False:
        failures.append("READY incorrectly claimed refactor safety")

    no_receipt = _run(execution_receipt=None)
    if no_receipt["status"] != EVIDENCE_REQUIRED:
        failures.append("test ownership without execution receipt became READY")

    wrong_source = _run(execution_receipt=_receipt(source_identity="sha256:source-old"))
    if wrong_source["status"] != EVIDENCE_REQUIRED:
        failures.append("receipt bound to different source identity became READY")

    stale = _run(boundaries=[_boundary(freshness="stale")])
    if stale["status"] != EVIDENCE_REQUIRED:
        failures.append("stale provider proof became READY")

    indirect = _run(boundaries=[_boundary(classification="indirect")])
    if indirect["status"] != TEST_STRENGTHENING_REQUIRED:
        failures.append("indirect-only proof did not require test strengthening")

    failed = _run(execution_receipt=_receipt(status="FAIL"))
    if failed["status"] != EVIDENCE_REQUIRED:
        failures.append("failed pre-edit execution became READY")

    no_gates = _run(repository_gates=[])
    if no_gates["status"] != EVIDENCE_REQUIRED:
        failures.append("missing broader repository gates became READY")

    coverage_only = _run(
        boundaries=[_boundary(classification="indirect")],
        coverage_evidence={"line_percent": 100, "branch_percent": 100},
    )
    if coverage_only["status"] != TEST_STRENGTHENING_REQUIRED:
        failures.append("coverage percentage promoted indirect evidence to READY")

    wrong_tests = _run(execution_receipt=_receipt(test_ids=["sha256:other-test"]))
    if wrong_tests["status"] != EVIDENCE_REQUIRED:
        failures.append("execution receipt for different selected tests became READY")

    changed_source = _run(source_identity="sha256:source-b", execution_receipt=_receipt(source_identity="sha256:source-b"))
    changed_boundary = _run(boundaries=[_boundary("error-contract")])
    changed_tests = _run(
        test_references=[{"path": "tests/test_other.py", "evidence_identity": "sha256:test-other"}],
        execution_receipt=_receipt(test_ids=["sha256:test-other"]),
    )
    changed_execution = _run(
        execution_receipt={
            **_receipt(),
            "execution_identity": "sha256:execution-b",
        }
    )
    for label, payload in (
        ("source", changed_source),
        ("boundary", changed_boundary),
        ("tests", changed_tests),
        ("execution", changed_execution),
    ):
        if payload["evidence_identity"] == ready["evidence_identity"]:
            failures.append(f"{label} change did not change evidence identity")

    observations = {
        "ready_status": ready["status"],
        "no_receipt_status": no_receipt["status"],
        "wrong_source_status": wrong_source["status"],
        "stale_status": stale["status"],
        "indirect_status": indirect["status"],
        "failed_status": failed["status"],
        "no_gates_status": no_gates["status"],
        "coverage_only_status": coverage_only["status"],
        "authority": authority,
        "post_edit_requirements": ready.get("post_edit_requirements"),
    }
    result: dict[str, object] = {
        "probe": "behavior-preservation",
        "qualification_phase": "BP1",
        "passed": not failures,
        "observations": observations,
        "failures": failures,
    }
    if artifact_path is not None:
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Qualify BP1 behavior-preservation evidence.")
    parser.add_argument(
        "--artifact-path",
        type=Path,
        default=Path(".agent-artifacts/behavior-preservation-bp1-qualification.json"),
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    result = qualify(args.artifact_path)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
