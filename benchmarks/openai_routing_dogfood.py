"""Multi-task external OpenAI routing dogfood campaign."""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from benchmarks.openai_responses_routing_probe import (
    OpenAIRoutingProbeError,
    preflight_probe,
    run_probe,
)

_MANIFEST_SCHEMA = "agents-cookbook-openai-routing-dogfood-manifest.v1"
_SUMMARY_SCHEMA = "agents-cookbook-openai-routing-dogfood-summary.v1"
_MAX_TASKS = 32
_MAX_REPEATS = 5
_FORBIDDEN_PROMPT_TERMS = (
    "hashmarks",
    "task_evidence",
    "mcp__",
    "grep",
)


class OpenAIRoutingDogfoodError(RuntimeError):
    pass


def _digest_bytes(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def load_manifest(path: Path, *, workspace: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise OpenAIRoutingDogfoodError(
            f"routing dogfood manifest is unreadable: {exc}"
        ) from exc
    if not isinstance(payload, dict) or payload.get("schema") != _MANIFEST_SCHEMA:
        raise OpenAIRoutingDogfoodError(
            f"routing dogfood manifest schema must be {_MANIFEST_SCHEMA}"
        )
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        raise OpenAIRoutingDogfoodError("routing dogfood manifest name is required")
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise OpenAIRoutingDogfoodError("routing dogfood manifest tasks are required")
    if len(tasks) > _MAX_TASKS:
        raise OpenAIRoutingDogfoodError(
            f"routing dogfood manifest exceeds {_MAX_TASKS} tasks"
        )

    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    workspace = workspace.resolve()
    for index, raw_task in enumerate(tasks):
        if not isinstance(raw_task, dict):
            raise OpenAIRoutingDogfoodError(f"tasks[{index}] must be an object")
        task_id = raw_task.get("id")
        prompt = raw_task.get("prompt")
        expected_paths = raw_task.get("expected_paths")
        if not isinstance(task_id, str) or re.fullmatch(
            r"[a-z0-9][a-z0-9-]{0,79}",
            task_id,
        ) is None:
            raise OpenAIRoutingDogfoodError(
                f"tasks[{index}].id must be a stable lowercase slug"
            )
        if task_id in seen:
            raise OpenAIRoutingDogfoodError(
                f"duplicate routing dogfood task id: {task_id}"
            )
        seen.add(task_id)
        if not isinstance(prompt, str) or not prompt.strip():
            raise OpenAIRoutingDogfoodError(
                f"tasks[{index}].prompt must be nonempty"
            )
        if len(prompt) > 2_000:
            raise OpenAIRoutingDogfoodError(
                f"tasks[{index}].prompt exceeds 2000 characters"
            )
        lowered = prompt.casefold()
        forbidden = [
            term
            for term in _FORBIDDEN_PROMPT_TERMS
            if term in lowered
        ]
        if forbidden:
            raise OpenAIRoutingDogfoodError(
                f"tasks[{index}].prompt names routing/tool authority: {forbidden}"
            )
        if not isinstance(expected_paths, list) or not expected_paths:
            raise OpenAIRoutingDogfoodError(
                f"tasks[{index}].expected_paths must be a nonempty list"
            )
        paths: list[str] = []
        for value in expected_paths:
            if not isinstance(value, str) or not value.strip():
                raise OpenAIRoutingDogfoodError(
                    f"tasks[{index}].expected_paths contains an invalid path"
                )
            relative = value.strip()
            target = (workspace / relative).resolve()
            try:
                target.relative_to(workspace)
            except ValueError as exc:
                raise OpenAIRoutingDogfoodError(
                    f"tasks[{index}] expected path escapes workspace: {relative}"
                ) from exc
            if not target.is_file():
                raise OpenAIRoutingDogfoodError(
                    f"tasks[{index}] expected path does not exist: {relative}"
                )
            paths.append(relative)
        normalized.append(
            {
                "id": task_id,
                "prompt": prompt.strip(),
                "expected_paths": paths,
            }
        )
    return {
        "schema": _MANIFEST_SCHEMA,
        "name": name.strip(),
        "manifest_sha256": _digest_bytes(raw),
        "tasks": normalized,
    }


def preflight_campaign(
    *,
    manifest_path: Path,
    workspace: Path,
    handoff_path: Path,
    tunnel_client: Path,
    tunnel_id: str,
    model: str,
    openai_api_key: str,
    control_plane_api_key: str,
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path, workspace=workspace)
    probe = preflight_probe(
        workspace=workspace,
        handoff_path=handoff_path,
        tunnel_client=tunnel_client,
        tunnel_id=tunnel_id,
        model=model,
        openai_api_key=openai_api_key,
        control_plane_api_key=control_plane_api_key,
    )
    return {
        "schema": "agents-cookbook-openai-routing-dogfood-preflight.v1",
        "status": "READY",
        "manifest": {
            "name": manifest["name"],
            "sha256": manifest["manifest_sha256"],
            "task_count": len(manifest["tasks"]),
        },
        "probe": probe,
    }


def _usage_total(receipt: dict[str, Any]) -> int:
    total = 0
    openai = receipt.get("openai")
    usage = openai.get("usage") if isinstance(openai, dict) else None
    if not isinstance(usage, list):
        return 0
    for row in usage:
        if isinstance(row, dict):
            value = row.get("total_tokens")
            if isinstance(value, int) and not isinstance(value, bool):
                total += value
    return total


def _answer_path_match(
    final_text: object,
    expected_paths: list[str],
) -> bool:
    if not isinstance(final_text, str):
        return False
    lowered = final_text.casefold()
    return any(path.casefold() in lowered for path in expected_paths)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_campaign(
    *,
    manifest_path: Path,
    workspace: Path,
    handoff_path: Path,
    tunnel_client: Path,
    tunnel_id: str,
    model: str,
    repeats: int,
    output_dir: Path,
    openai_api_key: str,
    control_plane_api_key: str,
    probe_runner: Callable[..., dict[str, Any]] = run_probe,
) -> dict[str, Any]:
    if not 1 <= repeats <= _MAX_REPEATS:
        raise OpenAIRoutingDogfoodError(
            f"repeats must be between 1 and {_MAX_REPEATS}"
        )
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise OpenAIRoutingDogfoodError(
            f"dogfood output directory already exists: {output_dir}"
        )

    preflight = preflight_campaign(
        manifest_path=manifest_path,
        workspace=workspace,
        handoff_path=handoff_path,
        tunnel_client=tunnel_client,
        tunnel_id=tunnel_id,
        model=model,
        openai_api_key=openai_api_key,
        control_plane_api_key=control_plane_api_key,
    )
    manifest = load_manifest(manifest_path, workspace=workspace)
    output_dir.mkdir(parents=True, exist_ok=False)
    _write_json(output_dir / "preflight.json", preflight)
    _write_json(
        output_dir / "manifest.json",
        {
            "schema": manifest["schema"],
            "name": manifest["name"],
            "manifest_sha256": manifest["manifest_sha256"],
            "tasks": manifest["tasks"],
        },
    )

    rows: list[dict[str, Any]] = []
    outcome_counts: Counter[str] = Counter()
    first_tool_counts: Counter[str] = Counter()
    total_tokens = 0

    for task in manifest["tasks"]:
        for repeat in range(repeats):
            trial_id = f"{task['id']}-r{repeat + 1:02d}"
            trial_dir = output_dir / "trials" / trial_id
            started = time.monotonic()
            try:
                receipt = probe_runner(
                    workspace=workspace,
                    handoff_path=handoff_path,
                    tunnel_client=tunnel_client,
                    tunnel_id=tunnel_id,
                    model=model,
                    prompt=task["prompt"],
                    openai_api_key=openai_api_key,
                    control_plane_api_key=control_plane_api_key,
                )
            except OpenAIRoutingProbeError as exc:
                elapsed_ms = int(round((time.monotonic() - started) * 1000))
                error = {
                    "schema": "agents-cookbook-openai-routing-dogfood-error.v1",
                    "trial_id": trial_id,
                    "task_id": task["id"],
                    "repeat": repeat + 1,
                    "elapsed_ms": elapsed_ms,
                    "error": str(exc),
                }
                _write_json(trial_dir / "error.json", error)
                rows.append(
                    {
                        "trial_id": trial_id,
                        "task_id": task["id"],
                        "repeat": repeat + 1,
                        "outcome": "INCOMPLETE",
                        "answer_path_match": False,
                        "elapsed_ms": elapsed_ms,
                        "tokens": 0,
                        "first_tool": None,
                    }
                )
                outcome_counts["INCOMPLETE"] += 1
                continue

            elapsed_ms = int(round((time.monotonic() - started) * 1000))
            score = receipt.get("score")
            if not isinstance(score, dict) or not isinstance(
                score.get("outcome"),
                str,
            ):
                raise OpenAIRoutingDogfoodError(
                    f"trial {trial_id} returned no routing outcome"
                )
            outcome = score["outcome"]
            trace = receipt.get("trace")
            calls = trace.get("calls") if isinstance(trace, dict) else None
            first_tool = None
            if isinstance(calls, list) and calls and isinstance(calls[0], dict):
                value = calls[0].get("tool")
                if isinstance(value, str):
                    first_tool = value
                    first_tool_counts[value] += 1
            path_match = _answer_path_match(
                receipt.get("final_text"),
                task["expected_paths"],
            )
            tokens = _usage_total(receipt)
            total_tokens += tokens
            outcome_counts[outcome] += 1

            for filename in ("catalog", "trace", "score"):
                payload = receipt.get(filename)
                if not isinstance(payload, dict):
                    raise OpenAIRoutingDogfoodError(
                        f"trial {trial_id} has no {filename} artifact"
                    )
                _write_json(trial_dir / f"{filename}.json", payload)
            _write_json(trial_dir / "receipt.json", receipt)
            rows.append(
                {
                    "trial_id": trial_id,
                    "task_id": task["id"],
                    "repeat": repeat + 1,
                    "outcome": outcome,
                    "answer_path_match": path_match,
                    "elapsed_ms": elapsed_ms,
                    "tokens": tokens,
                    "first_tool": first_tool,
                }
            )

    pass_count = outcome_counts["PASS"]
    fail_count = outcome_counts["FAIL"]
    scoreable = pass_count + fail_count
    summary = {
        "schema": _SUMMARY_SCHEMA,
        "status": (
            "COMPLETE"
            if outcome_counts["INCOMPLETE"] == 0
            else "INCOMPLETE"
        ),
        "manifest": {
            "name": manifest["name"],
            "sha256": manifest["manifest_sha256"],
            "task_count": len(manifest["tasks"]),
            "repeats": repeats,
        },
        "authority": {
            "diagnostic_only": True,
            "heldout_comparable": False,
            "parallel_trials": False,
            "automatic_retry": False,
        },
        "trials": rows,
        "aggregate": {
            "total_trials": len(rows),
            "outcomes": dict(sorted(outcome_counts.items())),
            "scoreable_trials": scoreable,
            "hashmarks_first_rate": (
                pass_count / scoreable if scoreable else None
            ),
            "answer_path_matches": sum(
                row["answer_path_match"] is True for row in rows
            ),
            "answer_path_match_rate": (
                sum(row["answer_path_match"] is True for row in rows) / len(rows)
                if rows
                else None
            ),
            "first_tool_counts": dict(sorted(first_tool_counts.items())),
            "total_tokens": total_tokens,
            "total_elapsed_ms": sum(row["elapsed_ms"] for row in rows),
        },
    }
    _write_json(output_dir / "summary.json", summary)
    return summary


def campaign_exit_code(summary: dict[str, Any]) -> int:
    aggregate = summary.get("aggregate")
    outcomes = aggregate.get("outcomes") if isinstance(aggregate, dict) else None
    if not isinstance(outcomes, dict):
        raise OpenAIRoutingDogfoodError("dogfood summary outcomes are unavailable")
    if int(outcomes.get("INCOMPLETE", 0)) > 0:
        return 3
    if int(outcomes.get("ENVIRONMENT_BLOCKED", 0)) > 0:
        return 2
    if int(outcomes.get("UNKNOWN", 0)) > 0:
        return 3
    if int(outcomes.get("FAIL", 0)) > 0:
        return 1
    return 0
