from collections import defaultdict, deque
from pathlib import Path

from .refactor_focus_analysis import AnalysisCache
from .refactor_focus_imports import (
    internal_imports_for_file,
    parse_dynamic_loaded_source_modules,
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


def build_direct_test_owners(
    *,
    test_files: list[Path],
    all_test_python_files: list[Path],
    module_to_path: dict[str, Path],
    source_root: Path,
    tests_root: Path,
    package_name: str,
    tests_package_name: str,
    analysis_cache: AnalysisCache,
) -> dict[Path, set[Path]]:
    owners: dict[Path, set[Path]] = defaultdict(set)
    test_modules_to_path = {
        module_path_for_file(path=path, root=tests_root, package_name=tests_package_name): path
        for path in all_test_python_files
    }
    helper_source_modules: dict[Path, set[str]] = {}

    for path in all_test_python_files:
        direct_imports = internal_imports_for_file(
            path=path,
            root=tests_root,
            current_package_name=tests_package_name,
            package_names={package_name},
            analysis_cache=analysis_cache,
        )
        dynamic_imports = parse_dynamic_loaded_source_modules(
            path=path,
            source_root=source_root,
            package_name=package_name,
            analysis_cache=analysis_cache,
        )
        helper_source_modules[path] = direct_imports | dynamic_imports

    for test_file in test_files:
        for module in internal_imports_for_file(
            path=test_file,
            root=tests_root,
            current_package_name=tests_package_name,
            package_names={package_name},
            analysis_cache=analysis_cache,
        ):
            owner_path = module_to_path.get(module)
            if owner_path is not None:
                owners[owner_path].add(test_file)

        helper_modules = internal_imports_for_file(
            path=test_file,
            root=tests_root,
            current_package_name=tests_package_name,
            package_names={tests_package_name},
            analysis_cache=analysis_cache,
        )
        for helper_module in helper_modules:
            helper_path = test_modules_to_path.get(helper_module)
            if helper_path is None:
                continue
            for source_module in helper_source_modules.get(helper_path, set()):
                owner_path = module_to_path.get(source_module)
                if owner_path is not None:
                    owners[owner_path].add(test_file)

    return {path: tests for path, tests in owners.items() if tests}


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
) -> None:
    key = test_path.as_posix()
    candidate_priority = MATCH_PRIORITY.get(match_type, 100)
    existing = matches_by_path.get(key)
    if existing is not None:
        existing_priority = MATCH_PRIORITY.get(existing["match_type"], 100)
        if existing_priority <= candidate_priority:
            return
    match_record: MatchRecord = {
        "test_path": report_path(path=test_path, anchor=test_path_anchor),
        "test_lines": test_lines_by_path.get(test_path, 0),
        "match_type": match_type,
        "evidence_authority": MATCH_AUTHORITY.get(match_type, "candidate"),
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
