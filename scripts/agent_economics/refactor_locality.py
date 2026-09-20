from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

SNAPSHOT_SCHEMA = "agentscookbook-refactor-locality-snapshot/v1"
COMPARISON_SCHEMA = "agentscookbook-refactor-locality-comparison/v1"
DECISION_SCHEMA = "agentscookbook-refactor-locality-decision/v1"

KEEP_COHESIVE_AUTHORITY = "KEEP_COHESIVE_AUTHORITY"
DECOMPOSITION_JUSTIFIED = "DECOMPOSITION_JUSTIFIED"
DECOMPOSITION_LOCALITY_RISK = "DECOMPOSITION_LOCALITY_RISK"
INSUFFICIENT_LOCALITY_EVIDENCE = "INSUFFICIENT_LOCALITY_EVIDENCE"

LOCALITY_PRESERVED_OR_IMPROVED = "LOCALITY_PRESERVED_OR_IMPROVED"
LOCALITY_TRADEOFF_REVIEW_REQUIRED = "LOCALITY_TRADEOFF_REVIEW_REQUIRED"
LOCALITY_REGRESSED = "LOCALITY_REGRESSED"

JUSTIFYING_EVIDENCE_KINDS = frozenset(
    {
        "mixed_responsibilities",
        "ownership_ambiguity",
        "verification_locality_failure",
        "unsafe_change_coupling",
        "duplicated_authority",
        "hidden_side_effects",
        "change_isolation_failure",
    }
)

LOCALITY_DIMENSIONS = (
    "symbol_count",
    "file_count",
    "max_navigation_depth",
    "forwarding_only_symbol_count",
    "context_lines",
    "verifier_file_count",
    "edit_file_count",
    "evidence_file_count",
    "cross_file_symbol_count",
)

HARD_REGRESSION_DIMENSIONS = frozenset(
    {
        "file_count",
        "forwarding_only_symbol_count",
        "context_lines",
        "edit_file_count",
        "evidence_file_count",
        "cross_file_symbol_count",
    }
)


def _identity(payload: Mapping[str, object]) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _normalized_paths(values: Sequence[object]) -> list[str]:
    return sorted({str(value) for value in values if _nonempty(value)})


def locality_snapshot(
    *,
    repository_identity: str,
    target: str,
    target_path: str,
    source_identity: str,
    measurement_configuration_identity: str,
    symbols: Sequence[Mapping[str, object]],
    verifier_paths: Sequence[str],
    responsibilities: Sequence[str] = (),
    unresolved_evidence: Sequence[str] = (),
    authority_lines: int | None = None,
    branch_points: int | None = None,
    nesting_depth: int | None = None,
    state_kind: str = "observed",
) -> dict[str, object]:
    """Build transparent locality evidence from an explicit symbol/navigation set."""
    required = (
        repository_identity,
        target,
        target_path,
        source_identity,
        measurement_configuration_identity,
    )
    if any(not _nonempty(value) for value in required):
        raise ValueError("snapshot identities and target fields must be non-empty")
    if state_kind not in {"observed", "proposed"}:
        raise ValueError("state_kind must be observed or proposed")

    normalized_symbols: list[dict[str, object]] = []
    for row in symbols:
        path = str(row.get("path") or "")
        qualname = str(row.get("qualname") or "")
        line_start = row.get("line_start")
        line_end = row.get("line_end")
        navigation_depth = row.get("navigation_depth", 0)
        if (
            not _nonempty(path)
            or not _nonempty(qualname)
            or not isinstance(line_start, int)
            or isinstance(line_start, bool)
            or not isinstance(line_end, int)
            or isinstance(line_end, bool)
            or line_start < 1
            or line_end < line_start
            or not isinstance(navigation_depth, int)
            or isinstance(navigation_depth, bool)
            or navigation_depth < 0
        ):
            raise ValueError("symbols must contain valid path/qualname/span/depth evidence")
        normalized_symbols.append(
            {
                "path": path,
                "qualname": qualname,
                "line_start": line_start,
                "line_end": line_end,
                "navigation_depth": navigation_depth,
                "forwarding_only": bool(row.get("forwarding_only", False)),
                "edit_required": bool(row.get("edit_required", False)),
                "evidence_required": bool(row.get("evidence_required", True)),
            }
        )
    normalized_symbols.sort(key=lambda row: (str(row["path"]), str(row["qualname"])))
    if not normalized_symbols:
        raise ValueError("at least one symbol reference is required")

    verifier_files = _normalized_paths(list(verifier_paths))
    responsibility_rows = sorted({str(value) for value in responsibilities if _nonempty(value)})
    unresolved = sorted({str(value) for value in unresolved_evidence if _nonempty(value)})
    symbol_files = {str(row["path"]) for row in normalized_symbols}
    edit_files = {str(row["path"]) for row in normalized_symbols if row["edit_required"]}
    evidence_files = {
        str(row["path"]) for row in normalized_symbols if row["evidence_required"]
    } | set(verifier_files)
    context_lines = sum(
        int(row["line_end"]) - int(row["line_start"]) + 1 for row in normalized_symbols
    )
    dimensions = {
        "symbol_count": len(normalized_symbols),
        "file_count": len(symbol_files),
        "max_navigation_depth": max(int(row["navigation_depth"]) for row in normalized_symbols),
        "forwarding_only_symbol_count": sum(1 for row in normalized_symbols if row["forwarding_only"]),
        "context_lines": context_lines,
        "verifier_file_count": len(verifier_files),
        "edit_file_count": len(edit_files),
        "evidence_file_count": len(evidence_files),
        "cross_file_symbol_count": sum(1 for row in normalized_symbols if row["path"] != target_path),
    }
    structural_signals = {
        "authority_lines": authority_lines,
        "branch_points": branch_points,
        "nesting_depth": nesting_depth,
        "responsibility_count": len(responsibility_rows),
    }
    semantic = {
        "schema": SNAPSHOT_SCHEMA,
        "repository_identity": repository_identity,
        "target": target,
        "target_path": target_path,
        "source_identity": source_identity,
        "measurement_configuration_identity": measurement_configuration_identity,
        "state_kind": state_kind,
        "symbols": normalized_symbols,
        "verifier_paths": verifier_files,
        "responsibilities": responsibility_rows,
        "unresolved_evidence": unresolved,
        "dimensions": dimensions,
        "structural_signals": structural_signals,
    }
    return {
        **semantic,
        "evidence_identity": _identity(semantic),
        "claims": {
            "composite_score_used": False,
            "size_alone_justifies_decomposition": False,
            "edit_authorized": False,
        },
    }


def compare_locality(
    pre_snapshot: Mapping[str, object],
    post_snapshot: Mapping[str, object],
) -> dict[str, object]:
    unresolved: list[str] = []
    if pre_snapshot.get("schema") != SNAPSHOT_SCHEMA or post_snapshot.get("schema") != SNAPSHOT_SCHEMA:
        unresolved.append("valid-locality-snapshots")
    if pre_snapshot.get("target") != post_snapshot.get("target"):
        unresolved.append("same-semantic-target")
    if pre_snapshot.get("measurement_configuration_identity") != post_snapshot.get("measurement_configuration_identity"):
        unresolved.append("comparable-measurement-configuration")
    if pre_snapshot.get("repository_identity") == post_snapshot.get("repository_identity"):
        unresolved.append("distinct-repository-state")
    for label, snapshot in (("pre", pre_snapshot), ("post", post_snapshot)):
        if snapshot.get("unresolved_evidence"):
            unresolved.append(f"{label}-snapshot-completeness")
        if not _nonempty(snapshot.get("evidence_identity")):
            unresolved.append(f"{label}-snapshot-identity")

    pre_dimensions = pre_snapshot.get("dimensions")
    post_dimensions = post_snapshot.get("dimensions")
    if not isinstance(pre_dimensions, Mapping) or not isinstance(post_dimensions, Mapping):
        unresolved.append("locality-dimensions")
        pre_dimensions = {}
        post_dimensions = {}

    deltas: dict[str, int] = {}
    worsened: list[str] = []
    improved: list[str] = []
    hard_regressions: list[str] = []
    for dimension in LOCALITY_DIMENSIONS:
        pre_value = pre_dimensions.get(dimension)
        post_value = post_dimensions.get(dimension)
        if (
            not isinstance(pre_value, int)
            or isinstance(pre_value, bool)
            or not isinstance(post_value, int)
            or isinstance(post_value, bool)
        ):
            unresolved.append(f"dimension:{dimension}")
            continue
        delta = post_value - pre_value
        deltas[dimension] = delta
        if delta > 0:
            worsened.append(dimension)
            if dimension in HARD_REGRESSION_DIMENSIONS:
                hard_regressions.append(dimension)
        elif delta < 0:
            improved.append(dimension)

    unresolved = sorted(set(unresolved))
    if unresolved:
        status = INSUFFICIENT_LOCALITY_EVIDENCE
    elif hard_regressions:
        status = LOCALITY_REGRESSED
    elif worsened:
        status = LOCALITY_TRADEOFF_REVIEW_REQUIRED
    else:
        status = LOCALITY_PRESERVED_OR_IMPROVED

    semantic = {
        "schema": COMPARISON_SCHEMA,
        "target": pre_snapshot.get("target"),
        "pre_repository_identity": pre_snapshot.get("repository_identity"),
        "post_repository_identity": post_snapshot.get("repository_identity"),
        "pre_snapshot_identity": pre_snapshot.get("evidence_identity"),
        "post_snapshot_identity": post_snapshot.get("evidence_identity"),
        "measurement_configuration_identity": pre_snapshot.get("measurement_configuration_identity"),
        "deltas": deltas,
        "worsened_dimensions": sorted(worsened),
        "improved_dimensions": sorted(improved),
        "hard_regressions": sorted(hard_regressions),
        "status": status,
        "unresolved_evidence": unresolved,
    }
    return {
        **semantic,
        "evidence_identity": _identity(semantic),
        "claims": {
            "composite_score_used": False,
            "lower_entrypoint_loc_is_improvement_proof": False,
            "locality_preserved": status == LOCALITY_PRESERVED_OR_IMPROVED,
        },
    }


def decomposition_decision(
    *,
    pre_snapshot: Mapping[str, object],
    post_snapshot: Mapping[str, object],
    comparison: Mapping[str, object],
    decomposition_evidence: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    normalized_evidence = sorted(
        [
            {
                "kind": str(row.get("kind") or ""),
                "evidence_identity": str(row.get("evidence_identity") or ""),
                "summary": str(row.get("summary") or ""),
            }
            for row in decomposition_evidence
        ],
        key=lambda row: (row["kind"], row["evidence_identity"], row["summary"]),
    )
    invalid_evidence = [
        row
        for row in normalized_evidence
        if not _nonempty(row["kind"]) or not _nonempty(row["evidence_identity"])
    ]
    justifying = [
        row for row in normalized_evidence if row["kind"] in JUSTIFYING_EVIDENCE_KINDS
    ]
    size_only = bool(normalized_evidence) and not justifying
    comparison_status = comparison.get("status")
    comparison_bound = (
        comparison.get("pre_snapshot_identity") == pre_snapshot.get("evidence_identity")
        and comparison.get("post_snapshot_identity") == post_snapshot.get("evidence_identity")
    )

    if invalid_evidence or not comparison_bound or comparison_status == INSUFFICIENT_LOCALITY_EVIDENCE:
        status = INSUFFICIENT_LOCALITY_EVIDENCE
    elif comparison_status == LOCALITY_REGRESSED:
        status = DECOMPOSITION_LOCALITY_RISK
    elif not justifying:
        status = KEEP_COHESIVE_AUTHORITY
    elif comparison_status in {
        LOCALITY_PRESERVED_OR_IMPROVED,
        LOCALITY_TRADEOFF_REVIEW_REQUIRED,
    }:
        status = DECOMPOSITION_JUSTIFIED
    else:
        status = INSUFFICIENT_LOCALITY_EVIDENCE

    semantic = {
        "schema": DECISION_SCHEMA,
        "target": pre_snapshot.get("target"),
        "pre_snapshot_identity": pre_snapshot.get("evidence_identity"),
        "post_snapshot_identity": post_snapshot.get("evidence_identity"),
        "comparison_identity": comparison.get("evidence_identity"),
        "decomposition_evidence": normalized_evidence,
        "status": status,
    }
    return {
        **semantic,
        "evidence_identity": _identity(semantic),
        "claims": {
            "size_only_signal": size_only,
            "size_alone_justifies_decomposition": False,
            "edit_authorized": False,
            "merge_authorized": False,
            "composite_score_used": False,
        },
        "required_next_evidence": (
            [{"kind": "resolve-locality-evidence"}]
            if status == INSUFFICIENT_LOCALITY_EVIDENCE
            else (
                [{"kind": "revise-decomposition-to-preserve-locality"}]
                if status == DECOMPOSITION_LOCALITY_RISK
                else []
            )
        ),
    }


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _write(path: Path | None, payload: Mapping[str, object]) -> None:
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if path is None:
        print(rendered, end="")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Compare refactor locality without reducing it to a score."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    snapshot_parser = sub.add_parser("snapshot", help="Canonicalize explicit locality facts.")
    snapshot_parser.add_argument("input", type=Path)
    snapshot_parser.add_argument("--artifact", type=Path)
    compare_parser = sub.add_parser("compare", help="Compare pre/post locality snapshots.")
    compare_parser.add_argument("pre", type=Path)
    compare_parser.add_argument("post", type=Path)
    compare_parser.add_argument(
        "--evidence",
        type=Path,
        help="Optional decomposition evidence JSON array/object.",
    )
    compare_parser.add_argument("--artifact", type=Path)
    args = parser.parse_args(argv)

    if args.command == "snapshot":
        raw = _load(args.input)
        payload = locality_snapshot(**raw)  # type: ignore[arg-type]
        _write(args.artifact, payload)
        return

    pre = _load(args.pre)
    post = _load(args.post)
    comparison = compare_locality(pre, post)
    if args.evidence is None:
        _write(args.artifact, comparison)
        return
    raw_evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    if isinstance(raw_evidence, dict):
        rows = raw_evidence.get("decomposition_evidence", [])
    else:
        rows = raw_evidence
    if not isinstance(rows, list):
        raise ValueError("decomposition evidence must be a JSON array")
    decision = decomposition_decision(
        pre_snapshot=pre,
        post_snapshot=post,
        comparison=comparison,
        decomposition_evidence=[row for row in rows if isinstance(row, dict)],
    )
    _write(args.artifact, {"comparison": comparison, "decision": decision})


if __name__ == "__main__":
    main()
