from __future__ import annotations

import argparse
import json
from pathlib import Path

from .refactor_locality import (
    DECOMPOSITION_JUSTIFIED,
    DECOMPOSITION_LOCALITY_RISK,
    KEEP_COHESIVE_AUTHORITY,
    LOCALITY_REGRESSED,
    LOCALITY_TRADEOFF_REVIEW_REQUIRED,
    compare_locality,
    decomposition_decision,
    locality_snapshot,
)


def _symbol(
    path: str,
    qualname: str,
    start: int,
    end: int,
    *,
    depth: int = 0,
    forwarding: bool = False,
    edit: bool = True,
) -> dict[str, object]:
    return {
        "path": path,
        "qualname": qualname,
        "line_start": start,
        "line_end": end,
        "navigation_depth": depth,
        "forwarding_only": forwarding,
        "edit_required": edit,
        "evidence_required": True,
    }


def _snapshot(
    repo: str,
    symbols: list[dict[str, object]],
    *,
    lines: int,
    branches: int,
    nesting: int,
    responsibilities: list[str] | None = None,
    state_kind: str = "observed",
) -> dict[str, object]:
    return locality_snapshot(
        repository_identity=repo,
        target="src/pkg/core.py::authority",
        target_path="src/pkg/core.py",
        source_identity=f"sha256:{repo[-1]}-source",
        measurement_configuration_identity="sha256:locality-config-v1",
        symbols=symbols,
        verifier_paths=["tests/test_core.py"],
        responsibilities=responsibilities or ["authority"],
        authority_lines=lines,
        branch_points=branches,
        nesting_depth=nesting,
        state_kind=state_kind,
    )


def qualify(artifact_path: Path | None = None) -> dict[str, object]:
    failures: list[str] = []

    pre = _snapshot(
        "sha256:repo-a",
        [_symbol("src/pkg/core.py", "authority", 1, 225)],
        lines=225,
        branches=32,
        nesting=4,
    )
    size_only_post = _snapshot(
        "sha256:repo-b",
        [_symbol("src/pkg/core.py", "authority", 1, 16)],
        lines=16,
        branches=1,
        nesting=1,
        state_kind="proposed",
    )
    size_only_comparison = compare_locality(pre, size_only_post)
    size_only_decision = decomposition_decision(
        pre_snapshot=pre,
        post_snapshot=size_only_post,
        comparison=size_only_comparison,
        decomposition_evidence=[
            {
                "kind": "size_only",
                "evidence_identity": "sha256:loc",
                "summary": "225 lines to 16",
            }
        ],
    )
    if size_only_decision["status"] != KEEP_COHESIVE_AUTHORITY:
        failures.append("size-only reduction was treated as decomposition justification")

    fragmented = _snapshot(
        "sha256:repo-c",
        [
            _symbol("src/pkg/core.py", "authority", 1, 16),
            _symbol("src/pkg/a.py", "check_a", 1, 40, depth=1),
            _symbol("src/pkg/b.py", "check_b", 1, 40, depth=1),
            _symbol("src/pkg/c.py", "check_c", 1, 40, depth=2),
            _symbol("src/pkg/c.py", "forward", 42, 45, depth=3, forwarding=True),
        ],
        lines=16,
        branches=1,
        nesting=1,
        responsibilities=["validation", "presentation", "translation"],
        state_kind="proposed",
    )
    fragmented_comparison = compare_locality(pre, fragmented)
    if fragmented_comparison["status"] != LOCALITY_REGRESSED:
        failures.append("cross-file fragmentation did not become a locality regression")
    fragmented_decision = decomposition_decision(
        pre_snapshot=pre,
        post_snapshot=fragmented,
        comparison=fragmented_comparison,
        decomposition_evidence=[
            {
                "kind": "mixed_responsibilities",
                "evidence_identity": "sha256:mixed",
                "summary": "three responsibilities",
            }
        ],
    )
    if fragmented_decision["status"] != DECOMPOSITION_LOCALITY_RISK:
        failures.append("fragmentation regression was justified by lower entrypoint complexity")

    same_file = _snapshot(
        "sha256:repo-d",
        [
            _symbol("src/pkg/core.py", "authority", 1, 36),
            _symbol("src/pkg/core.py", "validate", 38, 90, depth=1),
            _symbol("src/pkg/core.py", "persist", 92, 140, depth=1),
        ],
        lines=36,
        branches=5,
        nesting=2,
        responsibilities=["validation", "persistence"],
        state_kind="proposed",
    )
    same_file_comparison = compare_locality(pre, same_file)
    if same_file_comparison["status"] != LOCALITY_TRADEOFF_REVIEW_REQUIRED:
        failures.append("same-file semantic extraction did not expose its navigation tradeoff")
    same_file_decision = decomposition_decision(
        pre_snapshot=pre,
        post_snapshot=same_file,
        comparison=same_file_comparison,
        decomposition_evidence=[
            {
                "kind": "mixed_responsibilities",
                "evidence_identity": "sha256:mixed-2",
                "summary": "validation and persistence are independently owned",
            }
        ],
    )
    if same_file_decision["status"] != DECOMPOSITION_JUSTIFIED:
        failures.append("bounded same-file semantic extraction could not be justified with non-size evidence")

    if any("score" in key for key in pre.get("dimensions", {})):
        failures.append("locality dimensions introduced an opaque score")
    if pre.get("claims", {}).get("composite_score_used") is not False:
        failures.append("snapshot did not explicitly reject composite scoring")

    result = {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "cases": {
            "size_only": size_only_decision["status"],
            "fragmented": fragmented_decision["status"],
            "same_file": same_file_decision["status"],
        },
    }
    if artifact_path is not None:
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path)
    args = parser.parse_args(argv)
    result = qualify(args.artifact)
    print(json.dumps(result, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
