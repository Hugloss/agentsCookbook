"""Derived, source-free diagnostics from verified benchmark agent traces."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any

from benchmarks.hashmarks_task_evidence import retrieval_candidate_matches
from benchmarks.tool_routing import (
    NATIVE_READ,
    NATIVE_SEARCH,
    TOOL_ROUTER,
    classify_call,
    classify_tool,
    is_subject_tool,
    matches_subject_operation,
    result_bytes,
)

from .bundle import verify_bundle


class TraceDiagnosticError(ValueError):
    pass


def _sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _relative_path(value: Any, workspace: str) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    root = Path(workspace)
    try:
        return str(path.relative_to(root)) if path.is_absolute() else str(path)
    except ValueError:
        return "<outside-workspace>"


def _tool_failure(status: Any, output: Any) -> str | None:
    if status not in {"error", "failed"}:
        return None
    rendered = str(output).lower()
    if "rejected permission" in rendered or "permission denied" in rendered:
        return "permission-denied"
    if "ripgrep execution failed" in rendered:
        return "search-backend-failed"
    if "file not found" in rendered:
        return "path-not-found"
    return "tool-error"


def _hashmarks_evidence(output: Any, expected: dict[str, str] | None) -> dict[str, Any]:
    try:
        packet = json.loads(output) if isinstance(output, str) else output
    except ValueError:
        packet = None
    if not isinstance(packet, dict):
        return {"packet_status": "unparseable"}
    retrieval = packet.get("retrieval")
    results = retrieval.get("results") if isinstance(retrieval, dict) else None
    rank = None
    if isinstance(results, list) and expected:
        for index, candidate in enumerate(results, 1):
            if retrieval_candidate_matches(candidate, expected):
                rank = index
                break
    ownership = packet.get("ownership")
    return {
        "packet_status": "parsed",
        "schema": packet.get("schema"),
        "retrieval_count": len(results) if isinstance(results, list) else None,
        "retrieval_truncated": (
            retrieval.get("truncated") if isinstance(retrieval, dict) else None
        ),
        "expected_target_rank": rank,
        "expected_target_observability": (
            "observed" if rank is not None else "absent-from-returned-candidates"
            if isinstance(results, list) and expected else "unknown"
        ),
        "ownership_status": (
            ownership.get("status") if isinstance(ownership, dict) else None
        ),
    }


def _opencode_calls(trace: dict[str, Any], receipt: dict[str, Any]) -> list[dict[str, Any]]:
    subject = receipt.get("condition", {}).get("subject")
    expected = (
        receipt.get("task", {}).get("oracle", {}).get("configuration", {}).get("expected")
    )
    expected = expected if isinstance(expected, dict) else None
    workspace = str(receipt.get("execution", {}).get("workspace_root", ""))
    calls: list[dict[str, Any]] = []
    for message in trace.get("messages", []):
        if not isinstance(message, dict):
            continue
        for part in message.get("parts", []):
            if not isinstance(part, dict) or part.get("type") != "tool":
                continue
            name = part.get("tool")
            state = part.get("state")
            state = state if isinstance(state, dict) else {}
            inputs = state.get("input")
            inputs = inputs if isinstance(inputs, dict) else {}
            status = state.get("status")
            output = state.get("error") or state.get("output")
            subject_call = is_subject_tool(name, subject)
            tool_class = classify_call(
                name,
                inputs,
                subject=subject,
            )
            row: dict[str, Any] = {
                "ordinal": len(calls) + 1,
                "tool": name,
                "tool_class": tool_class,
                "status": status,
                "failure": _tool_failure(status, output),
                "subject_call": subject_call,
                "input_sha256": _sha256(inputs),
                "input_fields": sorted(inputs),
            }
            if tool_class in {NATIVE_READ, NATIVE_SEARCH}:
                row["path_attempted"] = _relative_path(
                    inputs.get("filePath") or inputs.get("path"), workspace
                )
            if subject_call:
                row["result_bytes"] = result_bytes(output)
                if (
                    status == "completed"
                    and matches_subject_operation(
                        name,
                        subject="hashmarks",
                        operation="task_evidence",
                    )
                ):
                    row["hashmarks_evidence"] = _hashmarks_evidence(output, expected)
            if tool_class == TOOL_ROUTER:
                metadata = state.get("metadata")
                nested = (
                    metadata.get("toolCalls")
                    if isinstance(metadata, dict)
                    else None
                )
                row["routing_observability"] = (
                    "expanded" if isinstance(nested, list) else "opaque"
                )
            else:
                nested = None
            calls.append(row)
            if name == "execute" and isinstance(nested, list):
                    for call in nested:
                        if not isinstance(call, dict):
                            continue
                        nested_name = call.get("tool")
                        nested_status = call.get("status")
                        nested_result = call.get("result")
                        calls.append({
                            "ordinal": len(calls) + 1,
                            "tool": nested_name,
                            "tool_class": classify_tool(
                                nested_name,
                                subject=subject,
                            ),
                            "status": nested_status,
                            "failure": _tool_failure(nested_status, nested_result),
                            "subject_call": is_subject_tool(
                                nested_name,
                                subject,
                            ),
                            "input_sha256": None,
                            "input_fields": [],
                            "observability": "execute-metadata",
                            "result_bytes": None,
                        })
    return calls


def _last_assistant_text_present(trace: dict[str, Any]) -> bool | None:
    for message in reversed(trace.get("messages", [])):
        if not isinstance(message, dict):
            continue
        info = message.get("info")
        if not isinstance(info, dict) or info.get("role") != "assistant":
            continue
        parts = message.get("parts")
        if not isinstance(parts, list):
            return None
        return any(
            isinstance(part, dict)
            and part.get("type") == "text"
            and isinstance(part.get("text"), str)
            and bool(part["text"].strip())
            for part in parts
        )
    return None



def _numeric_summary(values: list[int | float]) -> dict[str, Any]:
    return {
        "observations": len(values),
        "mean": mean(values) if values else None,
        "median": median(values) if values else None,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
    }


def _repository_intelligence_quality(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate generic retrieval-quality diagnostics without ranking products."""

    hashmarks_calls: list[dict[str, Any]] = []
    for row in rows:
        for call in row.get("calls") or []:
            evidence = call.get("hashmarks_evidence")
            if isinstance(evidence, dict):
                hashmarks_calls.append(
                    {
                        "result_bytes": call.get("result_bytes"),
                        "evidence": evidence,
                    }
                )

    if not hashmarks_calls:
        return {
            "state": "not-observed",
            "claim_scope": "descriptive-diagnostic-only",
            "subjects": [],
        }

    packet_statuses = Counter(
        str(call["evidence"].get("packet_status"))
        for call in hashmarks_calls
        if isinstance(call["evidence"].get("packet_status"), str)
    )
    schemas = Counter(
        str(call["evidence"].get("schema"))
        for call in hashmarks_calls
        if isinstance(call["evidence"].get("schema"), str)
    )
    retrieval_counts = [
        int(value)
        for call in hashmarks_calls
        if isinstance(
            (value := call["evidence"].get("retrieval_count")),
            int,
        )
        and not isinstance(value, bool)
        and value >= 0
    ]
    result_sizes = [
        int(value)
        for call in hashmarks_calls
        if isinstance((value := call.get("result_bytes")), int)
        and not isinstance(value, bool)
        and value >= 0
    ]
    target_observability = Counter(
        str(call["evidence"].get("expected_target_observability"))
        for call in hashmarks_calls
        if isinstance(
            call["evidence"].get("expected_target_observability"),
            str,
        )
    )
    target_ranks = [
        int(value)
        for call in hashmarks_calls
        if isinstance(
            (value := call["evidence"].get("expected_target_rank")),
            int,
        )
        and not isinstance(value, bool)
        and value >= 1
    ]
    ownership = Counter(
        str(call["evidence"].get("ownership_status"))
        for call in hashmarks_calls
        if isinstance(call["evidence"].get("ownership_status"), str)
    )
    truncation = Counter(
        str(value).lower()
        for call in hashmarks_calls
        if isinstance(
            (value := call["evidence"].get("retrieval_truncated")),
            bool,
        )
    )
    truncation["unknown"] = len(hashmarks_calls) - sum(truncation.values())

    diagnostic_complete = 0
    for call in hashmarks_calls:
        evidence = call["evidence"]
        observable_target = evidence.get("expected_target_observability")
        if (
            evidence.get("packet_status") == "parsed"
            and isinstance(evidence.get("retrieval_count"), int)
            and not isinstance(evidence.get("retrieval_count"), bool)
            and isinstance(evidence.get("ownership_status"), str)
            and isinstance(call.get("result_bytes"), int)
            and not isinstance(call.get("result_bytes"), bool)
            and observable_target
            in {"observed", "absent-from-returned-candidates"}
        ):
            diagnostic_complete += 1

    evaluable_targets = (
        target_observability.get("observed", 0)
        + target_observability.get("absent-from-returned-candidates", 0)
    )
    ownership_observations = sum(ownership.values())
    rank_buckets = {
        "1": sum(rank == 1 for rank in target_ranks),
        "2-5": sum(2 <= rank <= 5 for rank in target_ranks),
        "6-10": sum(6 <= rank <= 10 for rank in target_ranks),
        "11+": sum(rank >= 11 for rank in target_ranks),
    }
    total_calls = len(hashmarks_calls)
    if diagnostic_complete == total_calls:
        sufficiency_state = "complete"
    elif diagnostic_complete:
        sufficiency_state = "partial"
    else:
        sufficiency_state = "insufficient"

    return {
        "state": "observed",
        "claim_scope": "descriptive-diagnostic-only",
        "subjects": [
            {
                "subject_id": "hashmarks",
                "operation": "task_evidence",
                "calls": total_calls,
                "packet_status_counts": dict(sorted(packet_statuses.items())),
                "schema_counts": dict(sorted(schemas.items())),
                "candidate_set_size": _numeric_summary(retrieval_counts),
                "result_payload_bytes": _numeric_summary(result_sizes),
                "retrieval_truncation": {
                    "true": truncation.get("true", 0),
                    "false": truncation.get("false", 0),
                    "unknown": truncation.get("unknown", 0),
                },
                "oracle_relative_target_observability": {
                    "counts": dict(sorted(target_observability.items())),
                    "evaluable_calls": evaluable_targets,
                    "observed_calls": target_observability.get("observed", 0),
                    "coverage_rate": (
                        target_observability.get("observed", 0)
                        / evaluable_targets
                        if evaluable_targets
                        else None
                    ),
                },
                "oracle_relative_target_rank": {
                    **_numeric_summary(target_ranks),
                    "buckets": rank_buckets,
                },
                "ownership": {
                    "observations": ownership_observations,
                    "status_counts": dict(sorted(ownership.items())),
                    "ambiguous_rate": (
                        ownership.get("ambiguous", 0) / ownership_observations
                        if ownership_observations
                        else None
                    ),
                    "unresolved_rate": (
                        ownership.get("unresolved", 0) / ownership_observations
                        if ownership_observations
                        else None
                    ),
                },
                "evidence_sufficiency": {
                    "state": sufficiency_state,
                    "complete_calls": diagnostic_complete,
                    "total_calls": total_calls,
                    "complete_rate": (
                        diagnostic_complete / total_calls if total_calls else None
                    ),
                    "required_fields": [
                        "parsed-packet",
                        "retrieval-count",
                        "ownership-status",
                        "result-bytes",
                        "oracle-target-observability",
                    ],
                },
                "interpretation": {
                    "target_rank": (
                        "aggregate oracle-relative benchmark observation only; "
                        "not a product acceptance threshold or optimization target"
                    ),
                    "ownership": (
                        "subject-reported packet status; benchmark does not "
                        "reinterpret ownership certainty"
                    ),
                    "candidate_set_and_payload": (
                        "descriptive retrieval-shape and transport-cost evidence"
                    ),
                },
            }
        ],
    }

def build_trace_diagnostics(results_root: Path) -> dict[str, Any]:
    """Inspect every verified result bundle; never turn an absent trace into no calls."""
    if not results_root.is_dir():
        raise TraceDiagnosticError(f"results directory is missing: {results_root}")
    rows: list[dict[str, Any]] = []
    for directory in sorted(results_root.iterdir()):
        if directory.name.startswith("."):
            continue
        valid, reason = verify_bundle(directory)
        if not valid:
            raise TraceDiagnosticError(f"invalid bundle {directory}: {reason}")
        receipt = json.loads((directory / "result.json").read_text(encoding="utf-8"))
        evidence = receipt["execution"]["artifacts"].get("agent_trace")
        if not isinstance(evidence, dict):
            trace_state = "missing"
            calls = None
        else:
            trace_path = directory / evidence["path"]
            try:
                trace = json.loads(trace_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                trace = None
            if isinstance(trace, dict) and isinstance(trace.get("messages"), list):
                trace_state = "opencode-export"
                calls = _opencode_calls(trace, receipt)
                final_text_present = _last_assistant_text_present(trace)
            else:
                trace_state = "unsupported-format"
                calls = None
                final_text_present = None
        if not isinstance(evidence, dict):
            final_text_present = None
        subject = receipt.get("condition", {}).get("subject")
        row = {
            "trial_id": receipt["trial_id"],
            "definition_id": receipt["definition_id"],
            "task_id": receipt.get("task", {}).get("id"),
            "condition_id": receipt.get("condition", {}).get("id"),
            "subject_id": subject,
            "replicate_id": receipt.get("execution", {}).get("replicate_id"),
            "status": receipt.get("status"),
            "reason": receipt.get("reason"),
            "trace_state": trace_state,
            "last_assistant_text_present": final_text_present,
            "terminal_tool_failure": (
                calls[-1]["failure"] if calls else None
            ),
            "trace_path": (
                f"results/{directory.name}/{evidence['path']}"
                if isinstance(evidence, dict) else None
            ),
            "trace_sha256": evidence.get("sha256") if isinstance(evidence, dict) else None,
            "session_export_attempts": receipt.get("measurements", {}).get("agent", {}).get("session_export_attempts"),
            "subject_invocation_observed": receipt.get("measurements", {}).get("agent", {}).get("subject_tool_invoked"),
            "calls": calls,
        }
        rows.append(row)
    subject_calls = Counter()
    tool_failures = Counter()
    target_absences = Counter()
    for row in rows:
        for call in row["calls"] or []:
            if call["subject_call"]:
                subject_calls[str(row["subject_id"])] += 1
            if call["failure"]:
                tool_failures[call["failure"]] += 1
            if (
                call.get("hashmarks_evidence", {}).get("expected_target_observability")
                == "absent-from-returned-candidates"
            ):
                target_absences[str(row["task_id"])] += 1
    return {
        "schema": "agents-cookbook-trace-diagnostics.v3",
        "authority": {"derived_only": True, "source": "verified-result-bundles"},
        "trials": rows,
        "summary": {
            "trials": len(rows),
            "trace_states": dict(sorted(Counter(row["trace_state"] for row in rows).items())),
            "tool_classes": dict(sorted(Counter(
                call["tool_class"]
                for row in rows
                for call in (row["calls"] or [])
            ).items())),
            "subject_calls": dict(sorted(subject_calls.items())),
            "tool_failures": dict(sorted(tool_failures.items())),
            "hashmarks_expected_target_absent_from_returned_candidates": dict(sorted(target_absences.items())),
            "repository_intelligence_quality": _repository_intelligence_quality(rows),
        },
    }
