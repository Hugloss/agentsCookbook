import json
import time
from pathlib import Path

from .refactor_focus_analysis import AnalysisCache
from .refactor_focus_imports import (
    build_import_index,
    internal_imports_for_file,
)
from .refactor_focus_matching import (
    add_match,
    build_direct_test_owners,
    direct_name_test_candidates,
    feature_fallback_matches,
    mirrored_test_candidates,
    transitive_owner_matches,
)
from .refactor_focus_models import Emit, ExitCode, FocusRow, MatchRecord
from .refactor_focus_paths import (
    collect_python_files,
    common_path_anchor,
    iso_utc_now,
    module_path_for_file,
    report_path,
)
from .refactor_focus_scoring import (
    candidate_matches_for,
    confirmed_matches_for,
    supporting_matches_for,
    correspondence_status_for,
    function_size_summary,
    recommended_strategy_for,
    recommended_test_action_for,
    risk_score_for,
)


def refactor_focus_audit(
    *,
    emit: Emit,
    exit_code: ExitCode,
    source_root: Path,
    tests_root: Path,
    artifact_path: Path,
    repository_root: Path | None = None,
    package_name: str | None = None,
    tests_package_name: str | None = None,
    file_line_threshold: int = 800,
    function_line_threshold: int = 80,
    top_n: int = 3,
    transitive_max_depth: int = 2,
) -> None:
    started = time.perf_counter()
    source_root = source_root.resolve()
    tests_root = tests_root.resolve()
    effective_repository_root = (
        repository_root.resolve()
        if repository_root is not None
        else common_path_anchor([source_root, tests_root])
    )
    effective_package_name = package_name or source_root.name
    effective_tests_package_name = tests_package_name or tests_root.name

    emit(
        "INFO",
        "refactor_focus_audit_start",
        repository_root=effective_repository_root.as_posix(),
        source_root=source_root.as_posix(),
        tests_root=tests_root.as_posix(),
        package_name=effective_package_name,
        tests_package_name=effective_tests_package_name,
        file_line_threshold=file_line_threshold,
        function_line_threshold=function_line_threshold,
        top_n=top_n,
        transitive_max_depth=transitive_max_depth,
    )

    if not source_root.exists():
        emit(
            "ERROR",
            "refactor_focus_audit_invalid_source_root",
            source_root=source_root.as_posix(),
        )
        exit_code(1)
        return

    if file_line_threshold < 1 or function_line_threshold < 1 or top_n < 1:
        emit(
            "ERROR",
            "refactor_focus_audit_invalid_limits",
            file_line_threshold=file_line_threshold,
            function_line_threshold=function_line_threshold,
            top_n=top_n,
        )
        exit_code(2)
        return

    if transitive_max_depth < 0:
        emit(
            "ERROR",
            "refactor_focus_audit_invalid_transitive_depth",
            transitive_max_depth=transitive_max_depth,
        )
        exit_code(2)
        return

    source_files = collect_python_files(source_root)
    all_test_python_files = collect_python_files(tests_root)
    test_files = [
        path
        for path in all_test_python_files
        if path.name.startswith("test_") or path.name.endswith("_test.py")
    ]
    test_files_set = set(test_files)
    analysis_cache = AnalysisCache()
    unique_python_files = sorted(set(source_files) | set(all_test_python_files))
    analysis_cache.prewarm(unique_python_files)

    emit(
        "INFO",
        "refactor_focus_audit_discovery_complete",
        source_files_scanned=len(source_files),
        test_files_scanned=len(test_files),
    )

    test_lines_by_path = {path: analysis_cache.get(path).line_count for path in test_files}
    source_module_by_path = {
        path: module_path_for_file(
            path=path,
            root=source_root,
            package_name=effective_package_name,
        )
        for path in source_files
    }
    test_module_by_path = {
        path: module_path_for_file(
            path=path,
            root=tests_root,
            package_name=effective_tests_package_name,
        )
        for path in all_test_python_files
    }
    module_to_path = {
        **{module: path for path, module in source_module_by_path.items()},
        **{module: path for path, module in test_module_by_path.items()},
    }

    test_import_index = build_import_index(
        files=test_files,
        root=tests_root,
        current_package_name=effective_tests_package_name,
        package_names={effective_package_name},
        analysis_cache=analysis_cache,
    )
    source_import_index = build_import_index(
        files=source_files,
        root=source_root,
        current_package_name=effective_package_name,
        package_names={effective_package_name},
        analysis_cache=analysis_cache,
    )
    direct_test_owners = build_direct_test_owners(
        test_files=test_files,
        all_test_python_files=all_test_python_files,
        module_to_path=module_to_path,
        source_root=source_root,
        tests_root=tests_root,
        package_name=effective_package_name,
        tests_package_name=effective_tests_package_name,
        analysis_cache=analysis_cache,
    )

    rows: list[FocusRow] = []
    oversized_source_count = 0

    for source_file in source_files:
        source_lines = analysis_cache.get(source_file).line_count
        if source_lines <= file_line_threshold:
            continue

        oversized_source_count += 1
        matches_by_path: dict[str, MatchRecord] = {}

        for candidate in mirrored_test_candidates(
            source_file=source_file,
            source_root=source_root,
            tests_root=tests_root,
        ):
            if candidate in test_files_set:
                add_match(
                    matches_by_path=matches_by_path,
                    test_path=candidate,
                    match_type="mirrored_path",
                    test_lines_by_path=test_lines_by_path,
                    test_path_anchor=effective_repository_root,
                )

        for candidate in direct_name_test_candidates(
            source_file=source_file,
            test_files=test_files,
        ):
            add_match(
                matches_by_path=matches_by_path,
                test_path=candidate,
                match_type="direct_name",
                test_lines_by_path=test_lines_by_path,
                test_path_anchor=effective_repository_root,
            )

        module_path = source_module_by_path[source_file]

        for test_file in sorted(test_import_index.get(module_path, set())):
            add_match(
                matches_by_path=matches_by_path,
                test_path=test_file,
                match_type="import_exact",
                test_lines_by_path=test_lines_by_path,
                test_path_anchor=effective_repository_root,
            )

        for test_file in sorted(direct_test_owners.get(source_file, set())):
            add_match(
                matches_by_path=matches_by_path,
                test_path=test_file,
                match_type="support_loader",
                test_lines_by_path=test_lines_by_path,
                test_path_anchor=effective_repository_root,
            )

        for test_file in transitive_owner_matches(
            source_file=source_file,
            source_module=module_path,
            source_import_index=source_import_index,
            source_module_by_path=source_module_by_path,
            direct_test_owners=direct_test_owners,
            max_depth=transitive_max_depth,
        ):
            add_match(
                matches_by_path=matches_by_path,
                test_path=test_file,
                match_type="transitive_owner",
                test_lines_by_path=test_lines_by_path,
                test_path_anchor=effective_repository_root,
            )

        for test_file in feature_fallback_matches(
            source_path=source_file,
            source_root=source_root,
            tests_root=tests_root,
            test_files=test_files,
        ):
            add_match(
                matches_by_path=matches_by_path,
                test_path=test_file,
                match_type="feature_fallback",
                test_lines_by_path=test_lines_by_path,
                test_path_anchor=effective_repository_root,
            )

        matches = [matches_by_path[key] for key in sorted(matches_by_path)]
        confirmed_matches = confirmed_matches_for(matches)
        supporting_matches = supporting_matches_for(matches)
        candidate_matches = candidate_matches_for(matches)
        max_test_lines = max(
            (match["test_lines"] for match in confirmed_matches),
            default=0,
        )
        oversized_test_count = sum(
            1
            for match in confirmed_matches
            if match["test_lines"] > file_line_threshold
        )
        correspondence_status = correspondence_status_for(matches)
        function_over_limit_count, largest_function_lines = function_size_summary(
            source_file,
            max_function_lines=function_line_threshold,
            analysis_cache=analysis_cache,
        )

        dependent_sources = {
            path
            for path in source_import_index.get(module_path, set())
            if path != source_file
        }
        imports_out_count = len(
            internal_imports_for_file(
                path=source_file,
                root=source_root,
                current_package_name=effective_package_name,
                package_names={effective_package_name},
                analysis_cache=analysis_cache,
            ),
        )

        recommended_test_action = recommended_test_action_for(
            correspondence_status=correspondence_status,
            corresponding_test_count=len(confirmed_matches),
            max_test_lines=max_test_lines,
            file_line_threshold=file_line_threshold,
        )
        recommended_strategy = recommended_strategy_for(
            source_lines=source_lines,
            dependent_source_count=len(dependent_sources),
            imports_out_count=imports_out_count,
            correspondence_status=correspondence_status,
            max_test_lines=max_test_lines,
            file_line_threshold=file_line_threshold,
        )
        risk_score = risk_score_for(
            source_lines=source_lines,
            file_line_threshold=file_line_threshold,
            dependent_source_count=len(dependent_sources),
            imports_out_count=imports_out_count,
            corresponding_test_count=len(confirmed_matches),
            max_test_lines=max_test_lines,
            function_over_limit_count=function_over_limit_count,
            correspondence_status=correspondence_status,
        )

        row: FocusRow = {
            "source_path": report_path(
                path=source_file,
                anchor=effective_repository_root,
            ),
            "source_lines": source_lines,
            "matches": matches,
            "confirmed_matches": confirmed_matches,
            "supporting_matches": supporting_matches,
            "candidate_matches": candidate_matches,
            "corresponding_test_count": len(confirmed_matches),
            "supporting_test_count": len(supporting_matches),
            "candidate_test_count": len(candidate_matches),
            "has_corresponding_tests": bool(confirmed_matches),
            "correspondence_status": correspondence_status,
            "test_sync_required_if_split": bool(confirmed_matches),
            "max_test_lines": max_test_lines,
            "oversized_test_count": oversized_test_count,
            "dependent_source_count": len(dependent_sources),
            "imports_out_count": imports_out_count,
            "function_over_limit_count": function_over_limit_count,
            "largest_function_lines": largest_function_lines,
            "risk_score": risk_score,
            "recommended_test_action": recommended_test_action,
            "recommended_strategy": recommended_strategy,
        }
        rows.append(row)

        emit(
            "INFO",
            "refactor_focus_candidate",
            source_path=row["source_path"],
            source_lines=row["source_lines"],
            correspondence_status=row["correspondence_status"],
            corresponding_test_count=row["corresponding_test_count"],
            supporting_test_count=row["supporting_test_count"],
            candidate_test_count=row["candidate_test_count"],
            max_test_lines=row["max_test_lines"],
            risk_score=row["risk_score"],
            recommended_test_action=row["recommended_test_action"],
            recommended_strategy=row["recommended_strategy"],
        )

    correspondence_rank = {
        "confirmed": 0,
        "supported": 1,
        "ambiguous": 2,
        "missing": 3,
    }
    rows.sort(
        key=lambda row: (
            correspondence_rank.get(row["correspondence_status"], 99),
            -row["risk_score"],
            -row["source_lines"],
            row["source_path"],
        ),
    )

    selected_rows = rows[:top_n]
    selected_test_lines: dict[str, int] = {}
    for row in selected_rows:
        for match in row["matches"]:
            selected_test_lines.setdefault(match["test_path"], match["test_lines"])
    evidence_files_selected = len(selected_rows) + len(selected_test_lines)
    evidence_lines_selected = sum(row["source_lines"] for row in selected_rows) + sum(
        selected_test_lines.values()
    )
    candidate_reduction = (
        1.0 - (len(selected_rows) / oversized_source_count)
        if oversized_source_count
        else 0.0
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    economics = {
        **analysis_cache.metrics(),
        "elapsed_ms": elapsed_ms,
        "candidate_reduction": candidate_reduction,
        "evidence_files_selected": evidence_files_selected,
        "evidence_lines_selected": evidence_lines_selected,
        "transitive_max_depth": transitive_max_depth,
    }
    payload = {
        "generated_at": iso_utc_now(),
        "repository_root": effective_repository_root.as_posix(),
        "source_root": report_path(
            path=source_root,
            anchor=effective_repository_root,
        ),
        "tests_root": report_path(
            path=tests_root,
            anchor=effective_repository_root,
        ),
        "package_name": effective_package_name,
        "tests_package_name": effective_tests_package_name,
        "thresholds": {
            "file_lines": file_line_threshold,
            "function_lines": function_line_threshold,
            "transitive_max_depth": transitive_max_depth,
        },
        "source_files_scanned": len(source_files),
        "test_files_scanned": len(test_files),
        "test_python_files_scanned": len(all_test_python_files),
        "oversized_source_count": oversized_source_count,
        "selected_count": len(selected_rows),
        "economics": economics,
        "rows": selected_rows,
    }

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    emit(
        "INFO",
        "refactor_focus_audit_saved",
        path=artifact_path.as_posix(),
        selected_count=len(selected_rows),
    )
    emit(
        "INFO",
        "refactor_focus_audit_finished",
        source_files_scanned=len(source_files),
        test_files_scanned=len(test_files),
        oversized_source_count=oversized_source_count,
        selected_count=len(selected_rows),
        files_read=economics["files_read"],
        bytes_read=economics["bytes_read"],
        ast_parses=economics["ast_parses"],
        elapsed_ms=economics["elapsed_ms"],
        evidence_lines_selected=economics["evidence_lines_selected"],
    )
    exit_code(0)
