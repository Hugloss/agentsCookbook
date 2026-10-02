"""Execute evidence-escalated oracle reviews with a distinct read-only reviewer."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from benchmarks.harness.identity import digest
from benchmarks.harness.oracle_reviews import (
    OracleReviewError,
    oracle_review_path,
    validate_oracle_reviews,
)
from benchmarks.harness.source import materialize_repository
from scripts.agent_economics.bounded_process import ProcessLimits, run_bounded


REVIEWER_AGENT = "plan-fact-auditor"
REVIEWER_ID = "opencode-plan-fact-auditor-independent"
DECISION_PREFIX = "BENCHMARK_ORACLE_DECISION="


def _review_prompt(task_id: str, task: dict[str, Any]) -> str:
    expected = task["oracle"]["configuration"].get("expected")
    task_digest = digest(task)
    decision_example = json.dumps(
        {
            "task_id": task_id,
            "task_digest": task_digest,
            "decision": "unique|ambiguous|invalid",
            "reason": "brief evidence",
        },
        separators=(",", ":"),
    )
    return f"""You are performing an independent benchmark-oracle source audit.

Inspect only this pinned repository checkout. Do not use or search for any
agentsCookbook oracle-review evidence, prior reviewer rationale, or prior answer.

Task id: {task_id}
Task digest: {task_digest}
Frozen benchmark prompt:
{task["prompt"]}

Expected semantic owner under review:
{json.dumps(expected, sort_keys=True)}

Decide whether the expected owner is the unique defensible semantic owner for
the frozen prompt. Inspect source and callers independently.

Decision rules:
- unique: the expected owner is uniquely defensible.
- ambiguous: another owner is also defensible.
- invalid: the expected owner is not defensible or the task cannot be audited.

Explain the source evidence briefly. End your response with exactly one line:
{DECISION_PREFIX}{decision_example}
"""


def _parse_decision(stdout: str, *, task_id: str, task_digest: str) -> dict[str, str]:
    matches = [
        line[len(DECISION_PREFIX) :].strip()
        for line in stdout.splitlines()
        if line.startswith(DECISION_PREFIX)
    ]
    if len(matches) != 1:
        raise OracleReviewError(
            "independent reviewer must emit exactly one benchmark oracle decision"
        )
    try:
        value = json.loads(matches[0])
    except ValueError as exc:
        raise OracleReviewError(
            "independent reviewer decision is not valid JSON"
        ) from exc
    if not isinstance(value, dict):
        raise OracleReviewError("independent reviewer decision must be one JSON object")
    if value.get("task_id") != task_id or value.get("task_digest") != task_digest:
        raise OracleReviewError("independent reviewer decision identity mismatch")
    if value.get("decision") not in {"unique", "ambiguous", "invalid"}:
        raise OracleReviewError("independent reviewer decision is invalid")
    reason = value.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise OracleReviewError("independent reviewer reason is missing")
    return {
        "task_id": task_id,
        "task_digest": task_digest,
        "decision": str(value["decision"]),
        "reason": reason.strip(),
    }


def _run_review(workspace: Path, prompt: str) -> dict[str, str]:
    result = run_bounded(
        repository_root=workspace,
        argv=("opencode", "run", "--agent", REVIEWER_AGENT, prompt),
        limits=ProcessLimits(
            timeout_seconds=600.0,
            max_stdout_bytes=1_000_000,
            max_stderr_bytes=200_000,
        ),
        environment={"AGENTS_COOKBOOK_RUN_DIR": ""},
        close_stdin=True,
    )
    if result.executable_missing:
        raise OracleReviewError(
            "OpenCode is required for independent oracle review; install it and "
            "run scripts/link-opencode-local.sh"
        )
    if (
        result.timed_out
        or result.stdout_truncated
        or result.stderr_truncated
        or result.return_code != 0
    ):
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        detail = f": {stderr[:1200]}" if stderr else ""
        raise OracleReviewError(
            "independent OpenCode oracle reviewer failed" + detail
        )
    return {
        "stdout": result.stdout.decode("utf-8", errors="strict"),
        "command_identity": result.command_identity,
    }


def _write_evidence(path: Path, evidence: dict[str, Any]) -> None:
    raw = (json.dumps(evidence, indent=2, sort_keys=True) + "\n").encode()
    fd, temporary = tempfile.mkstemp(prefix=".oracle-reviews-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def run_pending_oracle_reviews(
    suite,
    *,
    cache_root: Path | None = None,
) -> dict[str, Any]:
    """Run only reviews still required by the committed review-depth policy."""
    status = validate_oracle_reviews(suite, require_complete=False)
    pending = list(status["pending_tasks"])
    if not pending:
        return {
            "reviewed_tasks": [],
            "complete": True,
            "approved_tasks": status["approved_tasks"],
        }

    review_path = oracle_review_path(suite)
    evidence = json.loads(review_path.read_text(encoding="utf-8"))
    cache = (
        cache_root
        or Path(tempfile.gettempdir()) / "agentscookbook-oracle-review-cache"
    )
    reviewed: list[dict[str, str]] = []

    for task_id in pending:
        task = suite.tasks[task_id]
        row = evidence["tasks"][task_id]
        requirement = row["review_requirement"]
        minimum_reviews = int(requirement["minimum_independent_reviews"])
        if len(row["reviews"]) >= minimum_reviews:
            non_unique = [
                review
                for review in row["reviews"]
                if review.get("decision") != "unique"
            ]
            if non_unique:
                raise OracleReviewError(
                    f"{task_id} has a non-unique independent review; "
                    "repair or retire the task instead of adding another reviewer"
                )
            continue
        if REVIEWER_ID in {review.get("reviewer") for review in row["reviews"]}:
            raise OracleReviewError(
                f"independent reviewer already recorded for {task_id}"
            )

        with tempfile.TemporaryDirectory(
            prefix=f"agentscookbook-oracle-review-{task_id}-"
        ) as tmp:
            workspace = Path(tmp) / "repository"
            materialize_repository(
                repository=task["repository"],
                destination=workspace,
                cache_root=cache,
            )
            prompt = _review_prompt(task_id, task)
            runtime = _run_review(workspace, prompt)
            decision = _parse_decision(
                runtime["stdout"],
                task_id=task_id,
                task_digest=digest(task),
            )

        row["reviews"].append(
            {
                "reviewer": REVIEWER_ID,
                "task_digest": decision["task_digest"],
                "decision": decision["decision"],
                "reason": decision["reason"],
                "runtime": {
                    "host": "opencode",
                    "agent": REVIEWER_AGENT,
                    "command_identity": runtime["command_identity"],
                },
            }
        )
        reviewed.append(decision)

    _write_evidence(review_path, evidence)
    final = validate_oracle_reviews(suite, require_complete=False)
    return {
        "reviewed_tasks": reviewed,
        "approved_tasks": final["approved_tasks"],
        "pending_tasks": final["pending_tasks"],
        "complete": final["complete"],
    }
