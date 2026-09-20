from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

SNAPSHOT_SCHEMA = "agentscookbook-refactor-locality-snapshot/v1"
COMPARISON_SCHEMA = "agentscookbook-refactor-locality-comparison/v1"
DECISION_SCHEMA = "agentscookbook-refactor-locality-decision/v1"
HASHMARKS_STRUCTURAL_LOCALITY_SCHEMA = "hashmarks.structural-locality.v1"

KEEP_COHESIVE_AUTHORITY = "KEEP_COHESIVE_AUTHORITY"
DECOMPOSITION_JUSTIFIED = "DECOMPOSITION_JUSTIFIED"
DECOMPOSITION_LOCALITY_RISK = "DECOMPOSITION_LOCALITY_RISK"
INSUFFICIENT_LOCALITY_EVIDENCE = "INSUFFICIENT_LOCALITY_EVIDENCE"

LOCALITY_PRESERVED_OR_IMPROVED = "LOCALITY_PRESERVED_OR_IMPROVED"
LOCALITY_TRADEOFF_REVIEW_REQUIRED = "LOCALITY_TRADEOFF_REVIEW_REQUIRED"
LOCALITY_REGRESSED = "LOCALITY_REGRESSED"

TRADEOFF_EVIDENCE_KIND = "bounded_locality_tradeoff"

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

# Every introduced symbol/layer must earn its existence with one of these
# semantic values. Merely lowering LOC/branches/nesting is intentionally absent.
STRUCTURAL_VALUE_KINDS = frozenset(
    {
        "semantic_responsibility_owner",
        "independent_policy_owner",
        "validation_boundary",
        "data_contract_owner",
        "side_effect_isolation",
        "resource_lifetime_owner",
        "change_isolation",
        "duplicated_authority_removed",
        "shared_reuse",
        "direct_test_seam",
        "stable_external_boundary",
        "compatibility_boundary",
        "protocol_adapter",
    }
)

# These shapes are especially easy for an agent to introduce just to satisfy a
# size/complexity target. They are not forbidden, but require explicit value.
EASY_PATH_STRUCTURE_KINDS = frozenset(
    {
        "wrapper",
        "shim",
        "adapter",
        "facade",
        "proxy",
        "delegate",
        "forwarding_helper",
        "reexport",
        "alias_module",
        "manager",
        "service",
    }
)

FORWARDING_BOUNDARY_VALUES = frozenset(
    {
        "stable_external_boundary",
        "compatibility_boundary",
        "protocol_adapter",
    }
)

LOCALITY_DIMENSIONS = (
    "symbol_count",
    "file_count",
    "max_navigation_depth",
    "forwarding_only_symbol_count",
    "context_lines",
    "verifier_file_count",
    "cross_file_symbol_count",
    "unresolved_call_count",
    "target_meaningful_caller_count",
)

HARD_REGRESSION_DIMENSIONS = frozenset(
    {
        "file_count",
        "context_lines",
        "cross_file_symbol_count",
        "unresolved_call_count",
    }
)


def _identity(payload: Mapping[str, object]) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _hashmarks_identity(payload: Mapping[str, object]) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _normalized_paths(values: Sequence[object]) -> list[str]:
    return sorted({str(value) for value in values if _nonempty(value)})


def _union_line_count(symbols: Sequence[Mapping[str, object]]) -> int:
    by_path: dict[str, list[tuple[int, int]]] = {}
    for row in symbols:
        by_path.setdefault(str(row["path"]), []).append(
            (int(row["line_start"]), int(row["line_end"]))
        )
    total = 0
    for spans in by_path.values():
        current_start: int | None = None
        current_end: int | None = None
        for start, end in sorted(spans):
            if current_start is None:
                current_start, current_end = start, end
                continue
            assert current_end is not None
            if start <= current_end + 1:
                current_end = max(current_end, end)
                continue
            total += current_end - current_start + 1
            current_start, current_end = start, end
        if current_start is not None and current_end is not None:
            total += current_end - current_start + 1
    return total


def locality_snapshot(
    *,
    repository_identity: str,
    target: str,
    target_path: str,
    source_identity: str,
    measurement_configuration_identity: str,
    provider: str,
    provider_evidence_identity: str,
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
        provider,
        provider_evidence_identity,
    )
    if any(not _nonempty(value) for value in required):
        raise ValueError("snapshot identities, provider, and target fields must be non-empty")
    if state_kind not in {"observed", "proposed"}:
        raise ValueError("state_kind must be observed or proposed")

    normalized_symbols: list[dict[str, object]] = []
    for row in symbols:
        path = str(row.get("path") or "")
        qualname = str(row.get("qualname") or "")
        line_start = row.get("line_start")
        line_end = row.get("line_end")
        navigation_depth = row.get("navigation_depth", 0)
        structure_kind = str(row.get("structure_kind") or "implementation")
        value_kind = str(row.get("value_kind") or "")
        value_evidence_identity = str(row.get("value_evidence_identity") or "")
        meaningful_caller_count = row.get("meaningful_caller_count", 0)
        direct_verifier_count = row.get("direct_verifier_count", 0)
        caller_count_complete = bool(row.get("caller_count_complete", False))
        value_evidence_provider = str(row.get("value_evidence_provider") or "")
        value_repository_identity = str(row.get("value_repository_identity") or "")
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
            or not _nonempty(structure_kind)
            or not isinstance(meaningful_caller_count, int)
            or isinstance(meaningful_caller_count, bool)
            or meaningful_caller_count < 0
            or not isinstance(direct_verifier_count, int)
            or isinstance(direct_verifier_count, bool)
            or direct_verifier_count < 0
        ):
            raise ValueError("symbols must contain valid path/qualname/span/depth/kind evidence")
        value_fields = (
            bool(value_kind),
            bool(value_evidence_identity),
            bool(value_evidence_provider),
            bool(value_repository_identity),
        )
        if len(set(value_fields)) != 1:
            raise ValueError(
                "structural value kind, identity, provider, and repository identity "
                "must either all be set or all be empty"
            )
        if value_kind and value_kind not in STRUCTURAL_VALUE_KINDS:
            raise ValueError(f"unsupported structural value kind: {value_kind}")
        if value_kind and value_repository_identity != repository_identity:
            raise ValueError("structural value evidence must bind the measured repository identity")
        normalized_symbols.append(
            {
                "path": path,
                "qualname": qualname,
                "line_start": line_start,
                "line_end": line_end,
                "navigation_depth": navigation_depth,
                "structure_kind": structure_kind,
                "forwarding_only": bool(row.get("forwarding_only", False)),
                "edit_required": bool(row.get("edit_required", False)),
                "evidence_required": bool(row.get("evidence_required", True)),
                "value_kind": value_kind or None,
                "value_evidence_identity": value_evidence_identity or None,
                "meaningful_caller_count": meaningful_caller_count,
                "direct_verifier_count": direct_verifier_count,
                "caller_count_complete": caller_count_complete,
                "value_evidence_provider": value_evidence_provider or None,
                "value_repository_identity": value_repository_identity or None,
            }
        )
    normalized_symbols.sort(key=lambda row: (str(row["path"]), str(row["qualname"])))
    if not normalized_symbols:
        raise ValueError("at least one symbol reference is required")
    symbol_identities = [
        (str(row["path"]), str(row["qualname"])) for row in normalized_symbols
    ]
    if len(symbol_identities) != len(set(symbol_identities)):
        raise ValueError("symbol references must be unique by path and qualname")
    if not any(
        row["path"] == target_path and row["navigation_depth"] == 0
        for row in normalized_symbols
    ):
        raise ValueError("snapshot must include the target authority at navigation depth 0")

    verifier_files = _normalized_paths(list(verifier_paths))
    responsibility_rows = sorted(
        {str(value) for value in responsibilities if _nonempty(value)}
    )
    unresolved = sorted(
        {str(value) for value in unresolved_evidence if _nonempty(value)}
    )
    symbol_files = {str(row["path"]) for row in normalized_symbols}
    edit_files = {
        str(row["path"]) for row in normalized_symbols if row["edit_required"]
    }
    evidence_files = {
        str(row["path"]) for row in normalized_symbols if row["evidence_required"]
    } | set(verifier_files)
    dimensions = {
        "symbol_count": len(normalized_symbols),
        "file_count": len(symbol_files),
        "max_navigation_depth": max(
            int(row["navigation_depth"]) for row in normalized_symbols
        ),
        "forwarding_only_symbol_count": sum(
            1 for row in normalized_symbols if row["forwarding_only"]
        ),
        "context_lines": _union_line_count(normalized_symbols),
        "verifier_file_count": len(verifier_files),
        "edit_file_count": len(edit_files),
        "evidence_file_count": len(evidence_files),
        "cross_file_symbol_count": sum(
            1 for row in normalized_symbols if row["path"] != target_path
        ),
        "unresolved_call_count": 0,
        "target_meaningful_caller_count": next(
            (
                int(row["meaningful_caller_count"])
                for row in normalized_symbols
                if row["path"] == target_path and row["navigation_depth"] == 0
            ),
            0,
        ),
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
        "provider": provider,
        "provider_evidence_identity": provider_evidence_identity,
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
            "independent_structural_provider": False,
        },
    }


def _symbol_map(snapshot: Mapping[str, object]) -> dict[tuple[str, str], Mapping[str, object]]:
    raw = snapshot.get("symbols")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
        return {}
    result: dict[tuple[str, str], Mapping[str, object]] = {}
    for row in raw:
        if not isinstance(row, Mapping):
            continue
        key = (str(row.get("path") or ""), str(row.get("qualname") or ""))
        if all(key):
            result[key] = row
    return result


def _structural_value_is_credible(row: Mapping[str, object]) -> bool:
    value_kind = row.get("value_kind")
    value_identity = row.get("value_evidence_identity")
    structure_kind = str(row.get("structure_kind") or "implementation")
    forwarding_only = bool(row.get("forwarding_only", False))
    caller_count = row.get("meaningful_caller_count", 0)
    verifier_count = row.get("direct_verifier_count", 0)
    if (
        not isinstance(value_kind, str)
        or value_kind not in STRUCTURAL_VALUE_KINDS
        or not _nonempty(value_identity)
    ):
        return False
    if forwarding_only and value_kind not in FORWARDING_BOUNDARY_VALUES:
        return False
    if value_kind == "shared_reuse" and (
        not isinstance(caller_count, int)
        or isinstance(caller_count, bool)
        or caller_count < 2
    ):
        return False
    if value_kind == "direct_test_seam" and (
        not isinstance(verifier_count, int)
        or isinstance(verifier_count, bool)
        or verifier_count < 1
    ):
        return False
    if structure_kind in {
        "shim",
        "proxy",
        "delegate",
        "forwarding_helper",
        "reexport",
        "alias_module",
    } and value_kind not in FORWARDING_BOUNDARY_VALUES:
        return False
    if structure_kind == "adapter" and value_kind not in {
        "protocol_adapter",
        "stable_external_boundary",
        "compatibility_boundary",
    }:
        return False
    return True


def _introduced_structure_evidence(
    pre_snapshot: Mapping[str, object],
    post_snapshot: Mapping[str, object],
) -> tuple[list[dict[str, object]], list[str], list[str], list[dict[str, str]]]:
    pre_symbols = _symbol_map(pre_snapshot)
    post_symbols = _symbol_map(post_snapshot)
    introduced: list[dict[str, object]] = []
    unjustified: list[str] = []
    easy_path: list[str] = []
    anti_patterns: list[dict[str, str]] = []
    for key in sorted(set(post_symbols) - set(pre_symbols)):
        row = post_symbols[key]
        path, qualname = key
        structure_kind = str(row.get("structure_kind") or "implementation")
        value_kind = row.get("value_kind")
        value_identity = row.get("value_evidence_identity")
        forwarding_only = bool(row.get("forwarding_only", False))
        earned = _structural_value_is_credible(row)
        identity = f"{path}::{qualname}"
        if not earned:
            unjustified.append(identity)
        if structure_kind in EASY_PATH_STRUCTURE_KINDS or forwarding_only:
            easy_path.append(identity)
        if not earned and structure_kind in EASY_PATH_STRUCTURE_KINDS:
            anti_patterns.append(
                {
                    "symbol": identity,
                    "code": "unearned-easy-path-layer",
                }
            )
        if forwarding_only and not earned:
            anti_patterns.append(
                {
                    "symbol": identity,
                    "code": "forwarder-without-external-boundary",
                }
            )
        if (
            structure_kind == "implementation"
            and not earned
            and int(row.get("meaningful_caller_count", 0)) <= 1
        ):
            anti_patterns.append(
                {
                    "symbol": identity,
                    "code": "single-use-extraction-without-semantic-value",
                }
            )
        introduced.append(
            {
                "path": path,
                "qualname": qualname,
                "structure_kind": structure_kind,
                "forwarding_only": forwarding_only,
                "value_kind": value_kind,
                "value_evidence_identity": value_identity,
                "meaningful_caller_count": row.get("meaningful_caller_count", 0),
                "direct_verifier_count": row.get("direct_verifier_count", 0),
                "earned_structural_value": earned,
            }
        )
    return (
        introduced,
        sorted(unjustified),
        sorted(easy_path),
        sorted(anti_patterns, key=lambda row: (row["symbol"], row["code"])),
    )


def compare_locality(
    pre_snapshot: Mapping[str, object],
    post_snapshot: Mapping[str, object],
) -> dict[str, object]:
    unresolved: list[str] = []
    if (
        pre_snapshot.get("schema") != SNAPSHOT_SCHEMA
        or post_snapshot.get("schema") != SNAPSHOT_SCHEMA
    ):
        unresolved.append("valid-locality-snapshots")
    if pre_snapshot.get("target") != post_snapshot.get("target"):
        unresolved.append("same-semantic-target")
    if (
        pre_snapshot.get("measurement_configuration_identity")
        != post_snapshot.get("measurement_configuration_identity")
    ):
        unresolved.append("comparable-measurement-configuration")
    if pre_snapshot.get("provider") != post_snapshot.get("provider"):
        unresolved.append("same-measurement-provider")
    same_repository = (
        pre_snapshot.get("repository_identity")
        == post_snapshot.get("repository_identity")
    )
    proposed_post = post_snapshot.get("state_kind") == "proposed"
    distinct_source = (
        pre_snapshot.get("source_identity") != post_snapshot.get("source_identity")
    )
    if same_repository and not (proposed_post and distinct_source):
        unresolved.append("distinct-observed-state-or-proposal")
    for label, snapshot in (("pre", pre_snapshot), ("post", post_snapshot)):
        if snapshot.get("unresolved_evidence"):
            unresolved.append(f"{label}-snapshot-completeness")
        if not _nonempty(snapshot.get("evidence_identity")):
            unresolved.append(f"{label}-snapshot-identity")
        if not _nonempty(snapshot.get("provider_evidence_identity")):
            unresolved.append(f"{label}-provider-evidence")

    pre_dimensions = pre_snapshot.get("dimensions")
    post_dimensions = post_snapshot.get("dimensions")
    if not isinstance(pre_dimensions, Mapping) or not isinstance(
        post_dimensions, Mapping
    ):
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

    introduced, unjustified, easy_path, anti_patterns = _introduced_structure_evidence(
        pre_snapshot, post_snapshot
    )
    if unjustified:
        hard_regressions.append("unjustified-new-structure")

    unresolved = sorted(set(unresolved))
    hard_regressions = sorted(set(hard_regressions))
    if unresolved:
        status = INSUFFICIENT_LOCALITY_EVIDENCE
    elif hard_regressions:
        status = LOCALITY_REGRESSED
    elif worsened or easy_path:
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
        "measurement_configuration_identity": pre_snapshot.get(
            "measurement_configuration_identity"
        ),
        "provider": pre_snapshot.get("provider"),
        "deltas": deltas,
        "worsened_dimensions": sorted(worsened),
        "improved_dimensions": sorted(improved),
        "hard_regressions": hard_regressions,
        "introduced_structures": introduced,
        "unjustified_new_structures": unjustified,
        "easy_path_structures": easy_path,
        "structural_anti_patterns": anti_patterns,
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
            "all_new_structure_earned_value": not unjustified,
            "wrappers_shims_are_default_solution": False,
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
        row
        for row in normalized_evidence
        if row["kind"] in JUSTIFYING_EVIDENCE_KINDS
    ]
    tradeoff_bound = any(
        row["kind"] == TRADEOFF_EVIDENCE_KIND for row in normalized_evidence
    )
    size_only = bool(normalized_evidence) and not justifying
    comparison_status = comparison.get("status")
    comparison_bound = (
        comparison.get("pre_snapshot_identity")
        == pre_snapshot.get("evidence_identity")
        and comparison.get("post_snapshot_identity")
        == post_snapshot.get("evidence_identity")
    )
    structural_value_complete = not bool(
        comparison.get("unjustified_new_structures")
    )

    if (
        invalid_evidence
        or not comparison_bound
        or comparison_status == INSUFFICIENT_LOCALITY_EVIDENCE
    ):
        status = INSUFFICIENT_LOCALITY_EVIDENCE
    elif not structural_value_complete or comparison_status == LOCALITY_REGRESSED:
        status = DECOMPOSITION_LOCALITY_RISK
    elif not justifying:
        status = KEEP_COHESIVE_AUTHORITY
    elif comparison_status == LOCALITY_PRESERVED_OR_IMPROVED:
        status = DECOMPOSITION_JUSTIFIED
    elif (
        comparison_status == LOCALITY_TRADEOFF_REVIEW_REQUIRED
        and tradeoff_bound
    ):
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
            "all_new_structure_earned_value": structural_value_complete,
            "edit_authorized": False,
            "merge_authorized": False,
            "composite_score_used": False,
            "prefer_deletion_or_consolidation_before_new_layers": True,
        },
        "required_next_evidence": (
            [{"kind": "resolve-locality-evidence"}]
            if status == INSUFFICIENT_LOCALITY_EVIDENCE
            else (
                [
                    {
                        "kind": "revise-decomposition-to-remove-unearned-structure",
                        "symbols": comparison.get(
                            "unjustified_new_structures", []
                        ),
                    }
                ]
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
        description=(
            "Compare refactor locality without a score and require every new "
            "structural layer to earn its existence."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)
    snapshot_parser = sub.add_parser(
        "snapshot", help="Canonicalize explicit locality facts."
    )
    snapshot_parser.add_argument("input", type=Path)
    snapshot_parser.add_argument("--artifact", type=Path)
    compare_parser = sub.add_parser(
        "compare", help="Compare pre/post locality snapshots."
    )
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
        decomposition_evidence=[
            row for row in rows if isinstance(row, dict)
        ],
    )
    _write(args.artifact, {"comparison": comparison, "decision": decision})


if __name__ == "__main__":
    main()
