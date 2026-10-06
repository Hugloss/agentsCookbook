"""Model-free MCP stdio tool-catalog admission proof."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from benchmarks.harness.identity import canonical_json
from benchmarks.harness.model import McpExposure, TrialContext
from scripts.agent_economics.bounded_process import ProcessLimits, run_bounded


MCP_PROTOCOL_VERSION = "2024-11-05"
MCP_CATALOG_TIMEOUT_SECONDS = 10
MCP_CATALOG_MAX_OUTPUT_BYTES = 1_000_000


def _request_bytes() -> bytes:
    messages = (
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "agents-cookbook-benchmark-admission",
                    "version": "1",
                },
            },
        },
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        },
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        },
    )
    return b"".join(
        json.dumps(
            message,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
        for message in messages
    )


def _response_by_id(raw: bytes) -> dict[int, dict[str, Any]]:
    responses: dict[int, dict[str, Any]] = {}
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("MCP catalog stdout is not valid UTF-8") from exc
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"MCP catalog stdout line {number} is not JSON-RPC"
            ) from exc
        if not isinstance(value, dict):
            raise ValueError(
                f"MCP catalog stdout line {number} is not a JSON object"
            )
        response_id = value.get("id")
        if response_id not in {1, 2}:
            continue
        if response_id in responses:
            raise ValueError(f"MCP catalog emitted duplicate response id {response_id}")
        responses[int(response_id)] = value
    return responses


def _result(response: dict[str, Any], *, label: str) -> dict[str, Any]:
    error = response.get("error")
    if error is not None:
        raise ValueError(f"MCP {label} failed: {error!r}")
    result = response.get("result")
    if not isinstance(result, dict):
        raise ValueError(f"MCP {label} response has no object result")
    return result


def probe_mcp_tool_catalog(
    *,
    context: TrialContext,
    exposure: McpExposure,
    subject_id: str,
    required_tool: str,
) -> dict[str, Any]:
    """Prove the admitted stdio MCP server exposes the frozen required operation."""
    if exposure.name != subject_id:
        raise ValueError(
            f"MCP exposure subject differs from contract: {exposure.name} != {subject_id}"
        )
    transport = exposure.semantic_identity.get("transport")
    if transport != "stdio":
        raise ValueError(
            f"MCP catalog admission supports stdio only, got {transport!r}"
        )
    prefix = subject_id + "_"
    if not required_tool.startswith(prefix):
        raise ValueError(
            f"required tool must use the {prefix} prefix"
        )
    required_operation = required_tool[len(prefix):]
    if not required_operation:
        raise ValueError("required MCP operation is empty")

    result = run_bounded(
        repository_root=context.workspace,
        argv=(exposure.command, *exposure.args),
        cwd=exposure.cwd,
        environment={**context.environment, **exposure.environment},
        limits=ProcessLimits(
            timeout_seconds=MCP_CATALOG_TIMEOUT_SECONDS,
            max_stdout_bytes=MCP_CATALOG_MAX_OUTPUT_BYTES,
            max_stderr_bytes=MCP_CATALOG_MAX_OUTPUT_BYTES,
        ),
        inherit_environment=False,
        stdin_bytes=_request_bytes(),
    )
    if result.executable_missing:
        raise ValueError("MCP catalog executable is missing")
    if result.timed_out:
        raise ValueError("MCP catalog probe timed out")
    if result.stdout_truncated or result.stderr_truncated:
        raise ValueError("MCP catalog probe output exceeded admission bounds")
    if result.return_code not in {0, None}:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        detail = f": {stderr[-1000:]}" if stderr else ""
        raise ValueError(
            f"MCP catalog process exited {result.return_code}{detail}"
        )

    responses = _response_by_id(result.stdout)
    if 1 not in responses:
        raise ValueError("MCP catalog emitted no initialize response")
    if 2 not in responses:
        raise ValueError("MCP catalog emitted no tools/list response")

    initialize = _result(responses[1], label="initialize")
    negotiated = initialize.get("protocolVersion")
    if not isinstance(negotiated, str) or not negotiated:
        raise ValueError("MCP initialize response has no protocolVersion")

    tools_result = _result(responses[2], label="tools/list")
    if tools_result.get("nextCursor") not in {None, ""}:
        raise ValueError(
            "MCP tools/list is paginated; complete catalog proof is unavailable"
        )
    tools = tools_result.get("tools")
    if not isinstance(tools, list):
        raise ValueError("MCP tools/list result has no tools list")

    names: list[str] = []
    for index, tool in enumerate(tools):
        if not isinstance(tool, dict):
            raise ValueError(f"MCP tool {index} is not an object")
        name = tool.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"MCP tool {index} has no nonempty name")
        names.append(name)
    if len(names) != len(set(names)):
        raise ValueError("MCP tools/list contains duplicate tool names")
    ordered = sorted(names)
    visible = required_operation in set(ordered)
    if not visible:
        raise ValueError(
            f"MCP required operation is not exposed: {required_operation}"
        )

    catalog_identity = {
        "subject_id": subject_id,
        "required_tool": required_tool,
        "required_operation": required_operation,
        "protocol_version": negotiated,
        "tool_names": ordered,
    }
    return {
        **catalog_identity,
        "required_tool_visible": True,
        "tool_count": len(ordered),
        "catalog_sha256": hashlib.sha256(
            canonical_json(catalog_identity)
        ).hexdigest(),
    }
