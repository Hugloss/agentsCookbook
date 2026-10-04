"""Standalone host-neutral tool-routing trace qualification."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from benchmarks.tool_probe import REQUIRED_TOOLS
from benchmarks.tool_routing import (
    catalog_admission,
    catalog_tool_names,
    evaluate_routing_calls,
    normalize_calls,
)

TRACE_SCHEMA = "agents-cookbook-tool-routing-trace.v1"
SCORE_SCHEMA = "agents-cookbook-tool-routing-trace-score.v1"

_DERIVED_CALL_FIELDS = frozenset({
    "ordinal",
    "tool_class",
    "result_basis",
    "routing_observability",
})


def _digest(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _validate_call(call: object, *, path: str) -> dict[str, object]:
    if not isinstance(call, dict):
        raise ValueError(f"{path} must be an object")
    tool = call.get("tool")
    if not isinstance(tool, str) or not tool.strip():
        raise ValueError(f"{path}.tool must be a nonempty string")
    forbidden = sorted(_DERIVED_CALL_FIELDS.intersection(call))
    if forbidden:
        raise ValueError(
            f"{path} contains derived routing fields owned by the scorer: {forbidden}"
        )
    status = call.get("status")
    if status is not None and (
        not isinstance(status, str) or not status.strip()
    ):
        raise ValueError(f"{path}.status must be a nonempty string when present")
    if "input" in call and "inputs" in call:
        raise ValueError(f"{path} must not contain both input and inputs")
    if "output" in call and "result" in call:
        raise ValueError(f"{path} must not contain both output and result")
    declared = call.get("result_bytes")
    if declared is not None and (
        not isinstance(declared, int) or isinstance(declared, bool) or declared < 0
    ):
        raise ValueError(f"{path}.result_bytes must be a nonnegative integer")
    nested = call.get("nested_calls")
    if nested is not None:
        if not isinstance(nested, list):
            raise ValueError(f"{path}.nested_calls must be a list")
        for index, child in enumerate(nested):
            _validate_call(child, path=f"{path}.nested_calls[{index}]")
    return call


def validate_trace(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise ValueError("tool-routing trace must be a JSON object")
    if payload.get("schema") != TRACE_SCHEMA:
        raise ValueError(f"tool-routing trace schema must be {TRACE_SCHEMA}")
    host = payload.get("host")
    if not isinstance(host, str) or not host.strip():
        raise ValueError("tool-routing trace host must be a nonempty string")
    calls = payload.get("calls")
    if not isinstance(calls, list):
        raise ValueError("tool-routing trace calls must be a list")
    for index, call in enumerate(calls):
        _validate_call(call, path=f"calls[{index}]")
    return payload


def score_trace(
    *,
    catalog_payload: object,
    trace_payload: object,
    subject: str,
) -> dict[str, Any]:
    if subject not in REQUIRED_TOOLS:
        raise ValueError(f"unsupported tool-routing subject: {subject}")
    trace = validate_trace(trace_payload)
    catalog_names = catalog_tool_names(catalog_payload)
    required_tool = REQUIRED_TOOLS[subject]
    admission = catalog_admission(
        catalog_names,
        subject=subject,
        required_tool=required_tool,
    )
    raw_calls = trace["calls"]
    assert isinstance(raw_calls, list)
    calls = normalize_calls(raw_calls, subject=subject)
    evaluation = evaluate_routing_calls(
        calls,
        subject=subject,
        required_tool=required_tool,
    )

    if admission["status"] == "READY":
        outcome = evaluation["outcome"]
    else:
        outcome = "ENVIRONMENT_BLOCKED"

    return {
        "schema": SCORE_SCHEMA,
        "authority": {
            "diagnostic_only": True,
            "heldout_comparable": False,
            "model_execution_owner": "external",
            "routing_classification_owner": "agents-cookbook",
        },
        "host": trace["host"],
        "subject": subject,
        "required_tool": required_tool,
        "outcome": outcome,
        "catalog_admission": admission,
        "catalog_sha256": _digest(catalog_payload),
        "trace_sha256": _digest(trace_payload),
        "call_count": len(calls),
        "calls": calls,
        "routing_evaluation": evaluation,
    }


def exit_code(score: dict[str, Any]) -> int:
    outcome = score.get("outcome")
    if outcome == "PASS":
        return 0
    if outcome == "FAIL":
        return 1
    if outcome == "ENVIRONMENT_BLOCKED":
        return 2
    if outcome == "UNKNOWN":
        return 3
    raise ValueError(f"unsupported tool-routing outcome: {outcome!r}")
