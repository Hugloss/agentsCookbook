"""Task-bound independent oracle review evidence for held-out campaigns."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .identity import digest

if TYPE_CHECKING:
    from .suite import SuiteDefinition


class OracleReviewError(ValueError):
    pass


def oracle_review_path(suite: SuiteDefinition) -> Path:
    """Return the configured review path, including the legacy fallback."""
    configured = suite.experiment.get("oracle_reviews")
    candidate = (
        suite.root / str(configured)
        if configured
        else suite.root / "qualification" / "oracle-reviews.json"
    ).resolve()
    try:
        candidate.relative_to(suite.root.resolve())
    except ValueError as exc:
        raise OracleReviewError("oracle review path escapes suite root") from exc
    return candidate


def oracle_reviews_declared(suite: SuiteDefinition) -> bool:
    path = oracle_review_path(suite)
    return "oracle_reviews" in suite.experiment or path.is_file()


def validate_oracle_reviews(
    suite: SuiteDefinition,
    *,
    require_complete: bool,
) -> dict[str, Any]:
    path = oracle_review_path(suite)
    if not path.is_file():
        if require_complete or "oracle_reviews" in suite.experiment:
            raise OracleReviewError("oracle review evidence is missing")
        return {
            "present": False,
            "first_reviewed_tasks": 0,
            "approved_tasks": 0,
            "complete": False,
        }
    try:
        evidence = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise OracleReviewError("oracle review evidence cannot be read") from exc
    if evidence.get("schema") != "agents-cookbook-oracle-reviews.v1":
        raise OracleReviewError("unknown oracle review evidence schema")
    rows = evidence.get("tasks")
    if not isinstance(rows, dict):
        raise OracleReviewError("oracle review task map is missing")
    pending = []
    first_reviewed = 0
    for task_id in suite.experiment["tasks"]:
        task = suite.tasks[task_id]
        row = rows.get(task_id)
        if not isinstance(row, dict):
            raise OracleReviewError(f"oracle review missing for {task_id}")
        task_digest = digest(task)
        if (
            row.get("task_digest") != task_digest
            or row.get("repository") != task["repository"]
        ):
            raise OracleReviewError(f"stale oracle review for {task_id}")
        if task["oracle"]["adapter"] == "repository-location-json":
            expected = task["oracle"]["configuration"]["expected"]
            if row.get("owner") != expected:
                raise OracleReviewError(f"oracle review owner differs for {task_id}")
        if (
            not isinstance(row.get("alternatives"), list)
            or not isinstance(row.get("evidence"), str)
            or not row["evidence"].strip()
        ):
            raise OracleReviewError(f"oracle review rationale missing for {task_id}")
        reviews = row.get("reviews")
        if not isinstance(reviews, list):
            raise OracleReviewError(f"oracle reviews malformed for {task_id}")
        reviewers = set()
        for review in reviews:
            if (
                not isinstance(review, dict)
                or not isinstance(review.get("reviewer"), str)
                or not review["reviewer"].strip()
                or review.get("task_digest") != task_digest
                or review.get("decision") not in {"unique", "ambiguous", "invalid"}
                or not isinstance(review.get("reason"), str)
                or not review["reason"].strip()
            ):
                raise OracleReviewError(f"invalid review record for {task_id}")
            if review["reviewer"] in reviewers:
                raise OracleReviewError(f"duplicate reviewer for {task_id}")
            reviewers.add(review["reviewer"])
        if reviewers:
            first_reviewed += 1
        if len(reviewers) < 2 or any(
            review["decision"] != "unique" for review in reviews
        ):
            pending.append(task_id)
    approved = len(suite.experiment["tasks"]) - len(pending)
    if require_complete and pending:
        raise OracleReviewError(
            "independent oracle review incomplete: "
            f"{approved}/{len(suite.experiment['tasks'])} tasks approved; "
            f"{len(pending)} still need a second independent review.\n"
            "Next: make benchmark-oracle-review\n"
            "Then: make benchmark-oracle-review-check"
        )
    return {
        "present": True,
        "first_reviewed_tasks": first_reviewed,
        "approved_tasks": approved,
        "pending_tasks": pending,
        "complete": not pending,
    }


def oracle_review_guide(suite: SuiteDefinition) -> str:
    """Return the next-action packet without granting review authority."""
    result = validate_oracle_reviews(suite, require_complete=False)
    total = len(suite.experiment["tasks"])
    approved = int(result["approved_tasks"])
    pending = list(result["pending_tasks"])
    path = oracle_review_path(suite)
    if not pending:
        return (
            f"Oracle review READY: {approved}/{total} tasks approved.\n"
            "Next: make benchmark-oracle-review-check\n"
            "Then: make benchmark"
        )

    evidence = json.loads(path.read_text(encoding="utf-8"))
    rows = evidence["tasks"]
    lines = [
        f"Oracle review BLOCKED: {approved}/{total} tasks approved; "
        f"{len(pending)} need another independent review.",
        "",
        "This command does not self-approve benchmark truth.",
        "Give the packet below to a distinct independent reviewer.",
        f"Record accepted decisions in: {path.relative_to(suite.root)}",
        "",
    ]
    for task_id in pending:
        task = suite.tasks[task_id]
        row = rows[task_id]
        owner = row.get("owner")
        owner_text = (
            f"{owner['path']}::{owner['symbol']}"
            if isinstance(owner, dict)
            else "repair oracle / no repository-location owner"
        )
        lines.extend(
            [
                f"- {task_id}",
                f"  repository: {task['repository']['url']}",
                f"  commit: {task['repository']['commit']}",
                f"  expected owner: {owner_text}",
                f"  existing independent reviews: {len(row.get('reviews', []))}",
            ]
        )
    lines.extend(
        [
            "",
            "Reviewer requirement: inspect the pinned source independently; "
            "do not copy the existing rationale.",
            "If any task has more than one defensible owner, mark it ambiguous "
            "and repair or retire the task instead of weakening grading.",
            "",
            "After recording the second independent reviews:",
            "  make benchmark-oracle-review-check",
            "  make benchmark",
        ]
    )
    return "\n".join(lines)
