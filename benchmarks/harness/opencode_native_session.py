"""E253/E254: bind native OpenCode session export to observed provider transport.

Only exported *native session tool parts* can supply the ATIF projection.
Never manufacture a tool call from the gateway request or an agent answer.
The export remains a locally held host observation, NOT an independent
provider attestation or proof of native process origin.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping

from .host_input_attestation import canonical, verify_host_attestations
from .trusted_host_capture import TrustedModelRequestCapture
from .trusted_treatments import verify_manifest

SCHEMA = "agentscookbook.opencode-native-session-binding.v1"
MAX_EXPORT_BYTES = 16_777_216
HEX = set("0123456789abcdef")
# Only these directly observed native Hashmarks operation spellings are known.
SUBJECT_TOOLS = frozenset((
    "hashmarks_task_evidence", "hashmarks.task_evidence",
    "mcp__hashmarks__task_evidence", "tools.hashmarks.task_evidence",
    "hashmarks_find", "hashmarks.find",
    "mcp__hashmarks__find", "tools.hashmarks.find",
))


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _decode_tool_output(value: object) -> object:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError) as exc:
            raise ValueError("native-export-tool-result-not-json") from exc
    if not isinstance(value, (dict, list)):
        raise ValueError("native-export-tool-result-not-structured")
    return value


def inspect_native_export(raw: bytes, *, session_id: str,
                          title: str, workspace: Path,
                          expected_provider: str, expected_model: str,
                          expected_packet: object,
                          expected_call_id_sha256: str,
                          expected_packet_sha256: str) -> dict[str, Any]:
    """Exact source binding, before committing ATIF or a host signature."""
    if (not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_EXPORT_BYTES
            or not isinstance(session_id, str) or not session_id
            or not isinstance(title, str) or not title
            or not isinstance(expected_provider, str) or not expected_provider
            or not isinstance(expected_model, str) or not expected_model
            or not all(isinstance(d, str) and len(d) == 64 and set(d) <= HEX
                       for d in (expected_call_id_sha256, expected_packet_sha256))):
        raise ValueError("invalid-frozen-native-export-identity")
    try:
        document = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError("native-export-json-invalid") from exc
    if not isinstance(document, dict) or not isinstance(document.get("info"), dict):
        raise ValueError("native-session-header-missing")
    info = document["info"]
    if (info.get("id") != session_id or info.get("title") != title
            or info.get("directory") != str(workspace.resolve())):
        raise ValueError("native-session-id-title-or-workspace-drift")
    messages = document.get("messages")
    if not isinstance(messages, list) or not messages or len(messages) > 10_000:
        raise ValueError("native-session-messages-unavailable")
    calls: list[dict[str, Any]] = []
    final_seen = False
    for message in messages:
        if not isinstance(message, dict) or not isinstance(message.get("info"), dict):
            raise ValueError("malformed-native-message")
        identity = message["info"]
        if identity.get("role") != "assistant":
            continue
        if (identity.get("providerID") != expected_provider
                or identity.get("modelID") != expected_model):
            raise ValueError("native-provider-or-model-drift")
        parts = message.get("parts", [])
        if not isinstance(parts, list):
            raise ValueError("invalid-native-message-parts")
        for part in parts:
            if not isinstance(part, dict):
                raise ValueError("invalid-native-session-part")
            if part.get("type") == "text" and isinstance(part.get("text"), str) and part["text"].strip():
                final_seen = True
            if part.get("type") != "tool":
                continue
            name = part.get("tool")
            call_id = part.get("callID")
            state = part.get("state")
            if (name not in SUBJECT_TOOLS or not isinstance(call_id, str)
                    or not 0 < len(call_id) <= 512 or not isinstance(state, dict)
                    or state.get("status") != "completed"
                    or "output" not in state):
                raise ValueError("native-tool-or-call-not-authoritative")
            packet = _decode_tool_output(state["output"])
            calls.append({"tool_name": name, "call_id": call_id, "packet": packet})
    if not final_seen or len(calls) != 1:
        raise ValueError("missing-final-or-multiple-subject-native-calls")
    item = calls[0]
    if (_digest(item["call_id"].encode("utf-8")) != expected_call_id_sha256
            or canonical(item["packet"]) != canonical(expected_packet)
            or _digest(canonical(item["packet"])) != expected_packet_sha256):
        raise ValueError("native-tool-result-not-bound-to-observed-provider-input")
    atif = {
        "schema_version": "ATIF-v1.8",
        "steps": [{
            "source": "agent",
            "tool_calls": [{
                "tool_call_id": item["call_id"],
                "function_name": "mcp__hashmarks__" + (
                    "find" if item["tool_name"].endswith("find") else "task_evidence"
                ),
                "arguments": {},
            }],
            "observation": {"results": [{
                "source_call_id": item["call_id"],
                "content": item["packet"],
            }]},
        }],
    }
    return {
        "schema": SCHEMA, "session_id": session_id, "title": title,
        "export_sha256": _digest(raw), "packet_sha256": expected_packet_sha256,
        "call_id_sha256": expected_call_id_sha256,
        "atif": atif,
        "native_session_observed": True,
        "native_process_origin_proven": False,
        "independent_native_export_proven": False,
        "provider_model_attention_proven": False,
    }


def _write_new(path: Path, data: bytes) -> None:
    if path.is_symlink():
        raise ValueError("native-evidence-symlink-target")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def finalize_native_export(
    raw: bytes, *, capture: TrustedModelRequestCapture,
    session_id: str, title: str, workspace: Path, run_root: Path,
    expected_provider: str, expected_model: str,
    original_packet: object,
) -> dict[str, Any]:
    """Match native export to host transport, then publish create-only receipts.

    A host-owned raw native export precedes ATIF projection. ATIF is derived
    from that export, never synthesized from a provider/gateway request.
    No trusted external origin is inferred from local native session bytes.
    """
    records = capture._recorded
    if (len(records) != 1 or "transport" not in records[0]
            or not capture._transport_attempted):
        raise ValueError("no-complete-host-observed-provider-submission")
    record = records[0]
    inspected = inspect_native_export(
        raw, session_id=session_id, title=title, workspace=workspace,
        expected_provider=expected_provider, expected_model=expected_model,
        expected_packet=original_packet,
        expected_call_id_sha256=record["call_id_sha256"],
        expected_packet_sha256=record["packet_sha256"],
    )
    native = run_root / "native-session.json"
    trajectory = run_root / "trajectory.json"
    attestation = run_root / "host-attestation.json"
    if any(path.exists() or path.is_symlink() for path in (
        native, trajectory, attestation,
    )):
        raise ValueError("native-evidence-reuse-or-overwrite")
    _write_new(native, raw)
    _write_new(trajectory, canonical(inspected["atif"]) + b"\n")
    # Once source data is stored, reparse from saved bytes; no in-memory
    # replacement of the native export after admission.
    if native.read_bytes() != raw:
        raise ValueError("native-source-mutated-after-storage")
    report = capture.finalize(trajectory=trajectory, output=attestation)
    verified = verify_host_attestations(
        trajectory, attestation, capture._key,
        campaign_id=capture._manifest["design"]["campaign_id"],
        trial_id=capture._trial_id,
    )
    if (verified["delivery_state"] != "PROVEN"
            or verified["provider_submission_state"] != "SUBMITTED"):
        raise ValueError("native-host-atif-and-transport-reverification-failed")
    return {
        "schema": SCHEMA,
        "native_export_sha256": inspected["export_sha256"],
        "trajectory_sha256": _digest(trajectory.read_bytes()),
        "attestation_sha256": _digest(attestation.read_bytes()),
        "native_session_export_verified": True,
        "native_session_to_gateway_packet_bound": True,
        "signed_host_input_and_transport_verified": True,
        "host_receipt_finalized": report["host_input_receipt_written"],
        "native_process_origin_proven": False,
        "independent_native_export_proven": False,
        "causal_improvement_proven": False,
    }
