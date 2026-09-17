from collections.abc import Callable
from typing import Literal, TypedDict

Emit = Callable[..., None]
ExitCode = Callable[[int], None]
EvidenceAuthority = Literal["confirmed", "supporting", "candidate"]


class MatchRecord(TypedDict):
    test_path: str
    test_lines: int
    match_type: str
    evidence_authority: EvidenceAuthority


class FocusRow(TypedDict):
    source_path: str
    source_lines: int
    matches: list[MatchRecord]
    confirmed_matches: list[MatchRecord]
    supporting_matches: list[MatchRecord]
    candidate_matches: list[MatchRecord]
    corresponding_test_count: int
    supporting_test_count: int
    candidate_test_count: int
    has_corresponding_tests: bool
    correspondence_status: str
    test_sync_required_if_split: bool
    max_test_lines: int
    oversized_test_count: int
    dependent_source_count: int
    imports_out_count: int
    function_over_limit_count: int
    largest_function_lines: int
    risk_score: int
    recommended_test_action: str
    recommended_strategy: str


MATCH_AUTHORITY: dict[str, EvidenceAuthority] = {
    # Direct structural evidence may establish a source/test relationship.
    "import_exact": "confirmed",
    "support_loader": "confirmed",
    # Conventions and inferred dependency paths are useful, but require inspection.
    "transitive_owner": "supporting",
    "mirrored_path": "supporting",
    "direct_name": "supporting",
    # Path-token overlap is discovery only.
    "feature_fallback": "candidate",
}

# Prefer stronger evidence when more than one matcher finds the same test path.
MATCH_PRIORITY = {
    "import_exact": 0,
    "support_loader": 1,
    "transitive_owner": 2,
    "mirrored_path": 3,
    "direct_name": 4,
    "feature_fallback": 5,
}

MIN_FEATURE_TOKEN_OVERLAP = 2
DEFAULT_EXCLUDE_DIRS = {
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".hypothesis",
    ".tox",
    ".nox",
    ".eggs",
    "build",
    "dist",
    "htmlcov",
    "coverage",
    ".ipynb_checkpoints",
    "docs/_build",
    ".idea",
    ".vscode",
}
