"""Execute evidence-escalated oracle reviews with a distinct read-only reviewer."""

from __future__ import annotations

import ast
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


REVIEWER_AGENT = "plan"
REVIEWER_ID = "opencode-plan-independent-oracle-review"
DECISION_PREFIX = "BENCHMARK_ORACLE_DECISION="


def _verify_expected_owner(
    workspace: Path,
    task: dict[str, Any],
) -> dict[str, str] | None:
    """Prove the frozen expected location exists before spending reviewer tokens."""
    if task["oracle"]["adapter"] != "repository-location-json":
        return None
    expected = task["oracle"]["configuration"].get("expected")
    if not isinstance(expected, dict):
        raise OracleReviewError("repository-location oracle has no expected owner")
    path_value = expected.get("path")
    symbol_value = expected.get("symbol")
    if not isinstance(path_value, str) or not isinstance(symbol_value, str):
        raise OracleReviewError("repository-location expected owner is malformed")

    root = workspace.resolve()
    path = (root / path_value).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise OracleReviewError("expected owner path escapes pinned repository") from exc
    if not path.is_file():
        raise OracleReviewError(
            f"pinned expected owner path is missing before review: {path_value}"
        )

    terminal_symbol = symbol_value.rsplit(".", 1)[-1]
    if path.suffix == ".py":
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeError) as exc:
            raise OracleReviewError(
                f"cannot inspect pinned expected owner source: {path_value}"
            ) from exc
        names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
            )
        }
        if terminal_symbol not in names:
            raise OracleReviewError(
                "pinned expected owner symbol is missing before review: "
                f"{path_value}::{symbol_value}"
            )
    else:
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise OracleReviewError(
                f"cannot inspect pinned expected owner source: {path_value}"
            ) from exc
        if terminal_symbol not in source:
            raise OracleReviewError(
                "pinned expected owner symbol is missing before review: "
                f"{path_value}::{symbol_value}"
            )
    return {"path": path_value, "symbol": symbol_value}


def _review_prompt(
    task_id: str,
    task: dict[str, Any],
    *,
    expected_owner: dict[str, str] | None,
) -> str:
    task_digest = digest(task)
    decision_example: dict[str, Any] = {
        "task_id": task_id,
        "task_digest": task_digest,
        "decision": "unique|ambiguous|invalid",
        "reason": "brief evidence",
    }
    if expected_owner is not None:
        decision_example["observed_owner"] = expected_owner
    rendered_decision = json.dumps(decision_example, separators=(",", ":"))
    return f"""You are performing an independent benchmark-oracle source audit.

Inspect only this pinned repository checkout. Do not use or search for any
agentsCookbook oracle-review evidence, prior reviewer rationale, or prior answer.

Task id: {task_id}
Task digest: {task_digest}
Frozen benchmark prompt:
{task["prompt"]}

Expected semantic owner under review:
{json.dumps(expected_owner, sort_keys=True)}

The harness independently proved that expected path/symbol exists in this exact
pinned checkout. You must inspect that source and its callers yourself.

Decide whether the expected owner is the unique defensible semantic owner for
the frozen prompt.

Decision rules:
- unique: the expected owner is uniquely defensible.
- ambiguous: another owner is also defensible.
- invalid: the observed expected owner exists but is not semantically defensible.
- inability to inspect source is NOT an invalid oracle decision; emit no decision.

For repository-location tasks, observed_owner must exactly name the source
location you actually inspected. Explain the source evidence briefly. End your
response with exactly one line:
{DECISION_PREFIX}{rendered_decision}
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
            "OpenCode is required for independent oracle review; install it first"
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
