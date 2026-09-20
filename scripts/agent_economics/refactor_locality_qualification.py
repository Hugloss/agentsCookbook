from __future__ import annotations

import argparse
import json
from pathlib import Path

from .refactor_locality import (
    DECOMPOSITION_JUSTIFIED,
    DECOMPOSITION_LOCALITY_RISK,
    INSUFFICIENT_LOCALITY_EVIDENCE,
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
    structure_kind: str = "implementation",
    value_kind: str | None = None,
    value_identity: str | None = None,
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
        "structure_kind": structure_kind,
        "value_kind": value_kind or "",
        "value_evidence_identity": value_identity or "",
    }


def _snapshot(
    repo: str,
    symbols: list[dict[str, object]],
    *,
    source: str | None = None,
    lines: int,
    branches: int,
    nesting: int,
    responsibilities: list[str] | None = None,
    state_kind: str = "observed",
    provider: str = "hashmarks",
) -> dict[str, object]:
    return locality_snapshot(
        repository_identity=repo,
        target="src/pkg/core.py::authority",
        target_path="src/pkg/core.py",
        source_identity=source or f"sha256:{repo[-1]}-source",
        measurement_configuration_identity="sha256:locality-config-v1",
        provider=provider,
        provider_evidence_identity=f"sha256:{repo[-1]}-provider",
        symbols=symbols,
        verifier_paths=["tests/test_core.py"],
        responsibilities=responsibilities or ["authority"],
        authority_lines=lines,
        branch_points=branches,
        nesting_depth=nesting,
        state_kind=state_kind,
    )


def _decision(
    pre: dict[str, object],
    post: dict[str, object],
    evidence: list[dict[str, str]],
) -> tuple[dict[str, object], dict[str, object]]:
    comparison = compare_locality(pre, post)
    decision = decomposition_decision(
        pre_snapshot=pre,
        post_snapshot=post,
        comparison=comparison,
        decomposition_evidence=evidence,
    )
    return comparison, decision


def qualify(artifact_path: Path | None = None) -> dict[str, object]:
    failures: list[str] = []

    pre = _snapshot(
        "sha256:repo-a",
        [_symbol("src/pkg/core.py", "authority", 1, 225)],
        lines=225,
        branches=32,
        nesting=4,
    )

    # Lowering the target from 225 lines to 16 lines cannot by itself authorize
    # decomposition. The right outcome is to keep the cohesive authority.
    size_only_post = _snapshot(
        "sha256:repo-b",
        [_symbol("src/pkg/core.py", "authority", 1, 16)],
        lines=16,
        branches=1,
        nesting=1,
        state_kind="proposed",
    )
    _, size_only_decision = _decision(
        pre,
        size_only_post,
        [
            {
                "kind": "size_only",
                "evidence_identity": "sha256:loc",
                "summary": "225 lines to 16",
            }
        ],
    )
    if size_only_decision["status"] != KEEP_COHESIVE_AUTHORITY:
        failures.append("size-only reduction was treated as decomposition justification")

    # The easy path: create pass-through wrappers in separate files so the public
    # entry point looks tiny. No new layer has earned semantic value.
    fragmented = _snapshot(
        "sha256:repo-c",
        [
            _symbol("src/pkg/core.py", "authority", 1, 16),
            _symbol(
                "src/pkg/a.py",
                "check_a",
                1,
                8,
                depth=1,
                forwarding=True,
                structure_kind="wrapper",
            ),
            _symbol(
                "src/pkg/b.py",
                "check_b",
                1,
                8,
                depth=1,
                forwarding=True,
                structure_kind="shim",
            ),
            _symbol(
                "src/pkg/c.py",
                "check_c",
                1,
                8,
                depth=2,
                forwarding=True,
                structure_kind="delegate",
            ),
        ],
        lines=16,
        branches=1,
        nesting=1,
        responsibilities=["validation", "presentation", "translation"],
        state_kind="proposed",
    )
    fragmented_comparison, fragmented_decision = _decision(
        pre,
        fragmented,
        [
            {
                "kind": "mixed_responsibilities",
                "evidence_identity": "sha256:mixed",
                "summary": "three responsibilities",
            }
        ],
    )
    if fragmented_comparison["status"] != LOCALITY_REGRESSED:
        failures.append("wrapper/shim fragmentation did not become a locality regression")
    if fragmented_decision["status"] != DECOMPOSITION_LOCALITY_RISK:
        failures.append("wrapper/shim fragmentation was justified by lower entrypoint complexity")
    if len(fragmented_comparison.get("unjustified_new_structures", [])) != 3:
        failures.append("unearned wrapper/shim structures were not all surfaced")

    # Moving statements into one-use helpers is also not automatically useful.
    same_file_clutter = _snapshot(
        "sha256:repo-d",
        [
            _symbol("src/pkg/core.py", "authority", 1, 28),
            _symbol(
                "src/pkg/core.py",
                "_step_a",
                30,
                70,
                depth=1,
                structure_kind="forwarding_helper",
            ),
            _symbol(
                "src/pkg/core.py",
                "_step_b",
                72,
                112,
                depth=1,
                structure_kind="forwarding_helper",
            ),
        ],
        lines=28,
        branches=3,
        nesting=2,
        state_kind="proposed",
    )
    clutter_comparison, clutter_decision = _decision(
        pre,
        same_file_clutter,
        [
            {
                "kind": "mixed_responsibilities",
                "evidence_identity": "sha256:claimed-mixed",
                "summary": "claimed decomposition",
            }
        ],
    )
    if clutter_comparison["status"] != LOCALITY_REGRESSED:
        failures.append("single-use helper clutter did not become a locality regression")
    if clutter_decision["status"] != DECOMPOSITION_LOCALITY_RISK:
        failures.append("single-use helper clutter was accepted without structural value")

    # Semantic extraction may be useful, but every introduced symbol must state
    # the value it owns, and a locality tradeoff needs explicit evidence.
    same_file = _snapshot(
        "sha256:repo-e",
        [
            _symbol("src/pkg/core.py", "authority", 1, 36),
            _symbol(
                "src/pkg/core.py",
                "validate",
                38,
                90,
                depth=1,
                structure_kind="helper",
                value_kind="validation_boundary",
                value_identity="sha256:validation-boundary",
            ),
            _symbol(
                "src/pkg/core.py",
                "persist",
                92,
                140,
                depth=1,
                structure_kind="helper",
                value_kind="side_effect_isolation",
                value_identity="sha256:persistence-boundary",
            ),
        ],
        lines=36,
        branches=5,
        nesting=2,
        responsibilities=["validation", "persistence"],
        state_kind="proposed",
    )
    same_file_comparison, same_file_without_tradeoff = _decision(
        pre,
        same_file,
        [
            {
                "kind": "mixed_responsibilities",
                "evidence_identity": "sha256:mixed-2",
                "summary": "validation and persistence are independently owned",
            }
        ],
    )
    if same_file_comparison["status"] != LOCALITY_TRADEOFF_REVIEW_REQUIRED:
        failures.append("same-file semantic extraction did not expose navigation tradeoff")
    if same_file_without_tradeoff["status"] != INSUFFICIENT_LOCALITY_EVIDENCE:
        failures.append("locality tradeoff was accepted without explicit tradeoff evidence")
    _, same_file_decision = _decision(
        pre,
        same_file,
        [
            {
                "kind": "mixed_responsibilities",
                "evidence_identity": "sha256:mixed-2",
                "summary": "validation and persistence are independently owned",
            },
            {
                "kind": "bounded_locality_tradeoff",
                "evidence_identity": "sha256:tradeoff",
                "summary": "one additional same-file hop isolates validation and side effects",
            },
        ],
    )
    if same_file_decision["status"] != DECOMPOSITION_JUSTIFIED:
        failures.append("earned same-file semantic extraction could not be justified")

    # A forwarding layer can be legitimate only when it owns a real external
    # compatibility/protocol boundary and that value is evidence-bound. It still
    # remains visible as a locality tradeoff rather than a free improvement.
    compatibility = _snapshot(
        "sha256:repo-f",
        [
            _symbol("src/pkg/core.py", "authority", 1, 180),
            _symbol(
                "src/pkg/core.py",
                "legacy_entry",
                182,
                186,
                depth=1,
                forwarding=True,
                structure_kind="shim",
                value_kind="compatibility_boundary",
                value_identity="sha256:public-api-contract",
            ),
        ],
        lines=180,
        branches=24,
        nesting=3,
        state_kind="proposed",
    )
    compatibility_comparison = compare_locality(pre, compatibility)
    if compatibility_comparison["status"] != LOCALITY_TRADEOFF_REVIEW_REQUIRED:
        failures.append("evidence-bound compatibility shim was hidden as a free improvement")
    if compatibility_comparison.get("unjustified_new_structures"):
        failures.append("evidence-bound compatibility shim was incorrectly unearned")

    # Measurement provider/configuration drift is incomparable.
    wrong_provider = _snapshot(
        "sha256:repo-g",
        [_symbol("src/pkg/core.py", "authority", 1, 200)],
        lines=200,
        branches=20,
        nesting=3,
        state_kind="proposed",
        provider="different-provider",
    )
    if compare_locality(pre, wrong_provider)["status"] != INSUFFICIENT_LOCALITY_EVIDENCE:
        failures.append("provider drift remained comparable")

    if any("score" in key for key in pre.get("dimensions", {})):
        failures.append("locality dimensions introduced an opaque score")
    if pre.get("claims", {}).get("composite_score_used") is not False:
        failures.append("snapshot did not explicitly reject composite scoring")

    result = {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "cases": {
            "size_only": size_only_decision["status"],
            "fragmented_wrappers": fragmented_decision["status"],
            "same_file_clutter": clutter_decision["status"],
            "same_file_semantic": same_file_decision["status"],
            "compatibility_shim": compatibility_comparison["status"],
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
