from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

from .refactor_focus_analysis import AnalysisCache
from .refactor_focus_imports import (
    internal_imports_for_file,
    parse_dynamic_loaded_source_module_evidence,
)
from .refactor_focus_models import (
    MATCH_AUTHORITY,
    MATCH_PRIORITY,
    MIN_FEATURE_TOKEN_OVERLAP,
    MatchRecord,
)
from .refactor_focus_paths import (
    module_path_for_file,
    path_feature_tokens,
    report_path,
)


@dataclass(frozen=True)
class TestOwnershipEvidence:
    source_path: Path
    test_path: Path
    match_type: str
    provenance: str


def build_test_ownership_evidence(
    *,
    test_files: list[Path],
    all_test_python_files: list[Path],
    module_to_path: dict[str, Path],
    source_root: Path,
    tests_root: Path,
    package_name: str,
    tests_package_name: str,
    analysis_cache: AnalysisCache,
    repository_root: Path,
    helper_max_depth: int = 2,
) -> list[TestOwnershipEvidence]:
    """Recover confirmed source/test relationships through Python imports.

    Direct static and literal dynamic imports are confirmed. Test-helper chains are
    also confirmed when every hop is a statically resolved test-package import and
    the chain stays within ``helper_max_depth``.
    """

    test_module_to_path = {
        module_path_for_file(
            path=path,
            root=tests_root,
            package_name=tests_package_name,
        ): path
        for path in all_test_python_files
    }
    test_imports_by_path: dict[Path, set[Path]] = {}
    source_static_by_path: dict[Path, set[str]] = {}
    source_dynamic_by_path: dict[Path, dict[str, set[str]]] = {}

    for path in all_test_python_files:
        test_imports_by_path[path] = {
            resolved
            for module in internal_imports_for_file(
                path=path,
                root=tests_root,
                current_package_name=tests_package_name,
                package_names={tests_package_name},
                analysis_cache=analysis_cache,
            )
            if (resolved := test_module_to_path.get(module)) is not None
            and resolved != path
        }
        source_static_by_path[path] = internal_imports_for_file(
            path=path,
            root=tests_root,
            current_package_name=tests_package_name,
            package_names={package_name},
            analysis_cache=analysis_cache,
        )
        source_dynamic_by_path[path] = parse_dynamic_loaded_source_module_evidence(
            path=path,
            source_root=source_root,
            package_name=package_name,
            analysis_cache=analysis_cache,
        )

    evidence: list[TestOwnershipEvidence] = []
    seen: set[tuple[Path, Path, str, str]] = set()

    def append(
        *,
        source_module: str,
        test_file: Path,
        match_type: str,
        provenance: str,
    ) -> None:
        source_path = module_to_path.get(source_module)
        if source_path is None:
            return
        key = (source_path, test_file, match_type, provenance)
        if key in seen:
            return
        seen.add(key)
        evidence.append(
            TestOwnershipEvidence(
                source_path=source_path,
                test_path=test_file,
                match_type=match_type,
                provenance=provenance,
            )
        )

    for test_file in test_files:
        test_report = report_path(path=test_file, anchor=repository_root)
        for source_module in sorted(source_static_by_path.get(test_file, set())):
            append(
                source_module=source_module,
                test_file=test_file,
                match_type="import_exact",
                provenance=f"static_import:test={test_report}:source={source_module}",
            )
        for source_module, kinds in sorted(source_dynamic_by_path.get(test_file, {}).items()):
            append(
                source_module=source_module,
                test_file=test_file,
                match_type="dynamic_import_literal",
                provenance=(
                    f"dynamic_import:test={test_report}:source={source_module}:"
                    f"kind={','.join(sorted(kinds))}"
                ),
            )

        if helper_max_depth <= 0:
            continue
        queue: deque[tuple[Path, int, tuple[Path, ...]]] = deque(
            (helper, 1, (helper,))
            for helper in sorted(test_imports_by_path.get(test_file, set()))
        )
        seen_helpers: set[Path] = set()
        while queue:
            helper, depth, chain = queue.popleft()
            if helper in seen_helpers or depth > helper_max_depth:
                continue
            seen_helpers.add(helper)
            chain_report = "->".join(
                report_path(path=path, anchor=repository_root) for path in chain
            )
            for source_module in sorted(source_static_by_path.get(helper, set())):
                append(
                    source_module=source_module,
                    test_file=test_file,
                    match_type="support_loader",
                    provenance=(
                        f"helper_chain:test={test_report}:helpers={chain_report}:"
                        f"depth={depth}:source={source_module}:kind=static_import"
                    ),
                )
            for source_module, kinds in sorted(source_dynamic_by_path.get(helper, {}).items()):
                append(
                    source_module=source_module,
                    test_file=test_file,
                    match_type="support_loader",
                    provenance=(
                        f"helper_chain:test={test_report}:helpers={chain_report}:"
                        f"depth={depth}:source={source_module}:"
                        f"kind={','.join(sorted(kinds))}"
                    ),
                )
            if depth >= helper_max_depth:
                continue
            for child in sorted(test_imports_by_path.get(helper, set())):
                if child not in seen_helpers:
                    queue.append((child, depth + 1, (*chain, child)))

    return evidence


def ownership_map_from_evidence(
    evidence: list[TestOwnershipEvidence],
) -> dict[Path, set[Path]]:
    owners: dict[Path, set[Path]] = defaultdict(set)
    for item in evidence:
        owners[item.source_path].add(item.test_path)
    return dict(owners)


def transitive_owner_matches(
    *,
    source_file: Path,
    source_module: str,
    source_import_index: dict[str, set[Path]],
    source_module_by_path: dict[Path, str],
    direct_test_owners: dict[Path, set[Path]],
    max_depth: int = 2,
) -> set[Path]:
    matches: set[Path] = set()
    seen_modules = {source_module}
    queue: deque[tuple[str, int]] = deque([(source_module, 0)])

    while queue:
        current_module, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for importer_path in source_import_index.get(current_module, set()):
            owner_tests = direct_test_owners.get(importer_path, set())
            for test_path in owner_tests:
                if transitive_feature_overlap(
                    source_file=source_file,
                    test_file=test_path,
                ):
                    matches.add(test_path)
            next_module = source_module_by_path.get(importer_path)
            if next_module is None or next_module in seen_modules:
                continue
            seen_modules.add(next_module)
            queue.append((next_module, depth + 1))

    return matches


def transitive_feature_overlap(*, source_file: Path, test_file: Path) -> bool:
    source_tokens = path_feature_tokens(source_file)
    test_tokens = path_feature_tokens(test_file)
    return len(source_tokens & test_tokens) >= 1


def add_match(
    *,
    matches_by_path: dict[str, MatchRecord],
    test_path: Path,
    match_type: str,
    test_lines_by_path: dict[Path, int],
    test_path_anchor: Path,
    provenance: str,
) -> None:
    key = test_path.as_posix()
    candidate_priority = MATCH_PRIORITY.get(match_type, 100)
    existing = matches_by_path.get(key)
    if existing is not None:
        existing_priority = MATCH_PRIORITY.get(existing["match_type"], 100)
        if existing_priority < candidate_priority:
            return
        if existing_priority == candidate_priority:
            if provenance != existing["provenance"]:
                parts = {part for part in existing["provenance"].split(" | ") if part}
                parts.add(provenance)
                existing["provenance"] = " | ".join(sorted(parts))
            return
    match_record: MatchRecord = {
        "test_path": report_path(path=test_path, anchor=test_path_anchor),
        "test_lines": test_lines_by_path.get(test_path, 0),
        "match_type": match_type,
        "evidence_authority": MATCH_AUTHORITY.get(match_type, "candidate"),
        "provenance": provenance,
    }
    matches_by_path[key] = match_record


def mirrored_test_candidates(
    *,
    source_file: Path,
    source_root: Path,
    tests_root: Path,
) -> list[Path]:
    relative = source_file.relative_to(source_root)
    parent = tests_root / relative.parent
    return [
        parent / f"test_{source_file.stem}.py",
        parent / f"{source_file.stem}_test.py",
    ]


def direct_name_test_candidates(
    *,
    source_file: Path,
    test_files: list[Path],
) -> list[Path]:
    names = {
        f"test_{source_file.stem}.py",
        f"{source_file.stem}_test.py",
    }
    return [path for path in test_files if path.name in names]


def feature_fallback_matches(
    *,
    source_path: Path,
    source_root: Path,
    tests_root: Path,
    test_files: list[Path],
) -> list[Path]:
    source_relative = source_path.relative_to(source_root)
    source_tokens = path_feature_tokens(source_relative)
    if not source_tokens:
        return []

    candidates: list[tuple[int, Path]] = []
    for test_file in test_files:
        test_relative = test_file.relative_to(tests_root)
        test_tokens = path_feature_tokens(test_relative)
        overlap = len(source_tokens & test_tokens)
        if overlap >= MIN_FEATURE_TOKEN_OVERLAP:
            candidates.append((overlap, test_file))

    return [
        path
        for _, path in sorted(
            candidates,
            key=lambda item: (-item[0], item[1].as_posix()),
        )
    ]
