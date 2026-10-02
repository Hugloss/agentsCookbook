"""Task-bound independent oracle review evidence for held-out campaigns."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from .identity import digest

if TYPE_CHECKING:
    from .suite import SuiteDefinition


class OracleReviewError(ValueError):
    pass


def validate_oracle_reviews(
    suite: SuiteDefinition, *, require_complete: bool,
) -> dict[str, Any]:
    path = suite.root / "qualification" / "oracle-reviews.json"
    if not path.is_file():
        if require_complete:
            raise OracleReviewError("oracle review evidence is missing")
        return {"present": False, "first_reviewed_tasks": 0, "approved_tasks": 0, "complete": False}
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
        if row.get("task_digest") != task_digest or row.get("repository") != task["repository"]:
            raise OracleReviewError(f"stale oracle review for {task_id}")
        if task["oracle"]["adapter"] == "repository-location-json":
            expected = task["oracle"]["configuration"]["expected"]
            if row.get("owner") != expected:
                raise OracleReviewError(f"oracle review owner differs for {task_id}")
        if not isinstance(row.get("alternatives"), list) or not isinstance(row.get("evidence"), str) or not row["evidence"].strip():
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
        if len(reviewers) < 2 or any(review["decision"] != "unique" for review in reviews):
            pending.append(task_id)
    if require_complete and pending:
        raise OracleReviewError(
            "independent oracle review incomplete for: " + ", ".join(pending)
        )
    return {
        "present": True,
        "first_reviewed_tasks": first_reviewed,
        "approved_tasks": len(suite.experiment["tasks"]) - len(pending),
        "pending_tasks": pending,
        "complete": not pending,
    }
