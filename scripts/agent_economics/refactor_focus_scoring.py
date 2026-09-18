import ast
from pathlib import Path

from .refactor_focus_analysis import AnalysisCache
from .refactor_focus_models import MatchRecord


def function_size_summary(
    path: Path,
    *,
    max_function_lines: int,
    analysis_cache: AnalysisCache,
) -> tuple[int, int]:
    tree = analysis_cache.get(path).tree
    if tree is None:
        return 0, 0

    over_limit_count = 0
    largest = 0
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        end_lineno = getattr(node, "end_lineno", node.lineno)
        line_count = max(1, end_lineno - node.lineno + 1)
        largest = max(largest, line_count)
        if line_count > max_function_lines:
            over_limit_count += 1
    return over_limit_count, largest


def matches_with_authority(
    matches: list[MatchRecord],
    authority: str,
) -> list[MatchRecord]:
    return [
        match for match in matches if match["evidence_authority"] == authority
    ]


def confirmed_matches_for(matches: list[MatchRecord]) -> list[MatchRecord]:
    return matches_with_authority(matches, "confirmed")


def supporting_matches_for(matches: list[MatchRecord]) -> list[MatchRecord]:
    return matches_with_authority(matches, "supporting")


def candidate_matches_for(matches: list[MatchRecord]) -> list[MatchRecord]:
    return matches_with_authority(matches, "candidate")


def correspondence_status_for(matches: list[MatchRecord]) -> str:
    if confirmed_matches_for(matches):
        return "confirmed"
    if supporting_matches_for(matches):
        return "supported"
    if candidate_matches_for(matches):
        return "ambiguous"
    return "missing"


def recommended_test_action_for(
    *,
    correspondence_status: str,
    corresponding_test_count: int,
    max_test_lines: int,
    file_line_threshold: int,
) -> str:
    if correspondence_status == "missing":
        return "manual_review_required"
    if correspondence_status in {"supported", "ambiguous"}:
        return "verify_test_correspondence_first"
    if max_test_lines > file_line_threshold:
        return "split_existing_test_file"
    if corresponding_test_count == 1:
        return "update_existing_test_file"
    return "keep_existing_test_file"


def recommended_strategy_for(
    *,
    source_lines: int,
    dependent_source_count: int,
    imports_out_count: int,
    correspondence_status: str,
    max_test_lines: int,
    file_line_threshold: int,
) -> str:
    if correspondence_status in {"missing", "supported", "ambiguous"}:
        return "recover_test_correspondence_first"
    if max_test_lines > file_line_threshold:
        return "split_source_and_tests_together"
    if dependent_source_count >= 5:
        return "wrapper_required"
    if imports_out_count >= 8:
        return "extract_shared_boundaries_first"
    if source_lines >= file_line_threshold + 250:
        return "extract_cohesive_helpers_first"
    return "small_safe_split"


def risk_score_for(
    *,
    source_lines: int,
    file_line_threshold: int,
    dependent_source_count: int,
    imports_out_count: int,
    corresponding_test_count: int,
    max_test_lines: int,
    function_over_limit_count: int,
    correspondence_status: str,
) -> int:
    score = 0
    score += max(1, (source_lines - file_line_threshold) // 50 + 1)
    score += min(dependent_source_count, 5)
    score += min(imports_out_count // 2, 4)
    score += min(function_over_limit_count * 2, 6)
    if corresponding_test_count == 0:
        score += 5
    if correspondence_status == "supported":
        score += 1
    elif correspondence_status == "ambiguous":
        score += 2
    if max_test_lines > file_line_threshold:
        score += 3
    return score
