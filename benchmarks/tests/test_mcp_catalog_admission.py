from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from benchmarks.harness.mcp_catalog import probe_mcp_tool_catalog
from benchmarks.harness.model import McpExposure, TrialContext


class McpCatalogAdmissionTests(unittest.TestCase):
    def _context(self, root: Path) -> TrialContext:
        workspace = root / "workspace"
        control = root / "control"
        workspace.mkdir()
        control.mkdir()
        return TrialContext(
            workspace=workspace,
            control_root=control,
            environment={"PATH": "/native/bin"},
        )

    def _exposure(self, root: Path) -> McpExposure:
        return McpExposure(
            name="futuremcp",
            command="/tools/futuremcp",
            args=("mcp",),
            cwd=root / "workspace",
            semantic_identity={
                "name": "futuremcp",
                "transport": "stdio",
            },
            environment={"FUTURE_MCP_MODE": "benchmark"},
        )

    def _process(self, tools: list[str], *, next_cursor: object = None):
        initialize = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "futuremcp", "version": "1"},
            },
        }
        listed = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": [{"name": name} for name in tools],
            },
        }
        if next_cursor is not None:
            listed["result"]["nextCursor"] = next_cursor
        stdout = (
            json.dumps(initialize, separators=(",", ":"))
            + "\n"
            + json.dumps(listed, separators=(",", ":"))
            + "\n"
        ).encode()
        return SimpleNamespace(
            executable_missing=False,
            timed_out=False,
            stdout_truncated=False,
            stderr_truncated=False,
            return_code=0,
            stdout=stdout,
            stderr=b"",
        )

    def test_required_operation_is_proven_from_raw_mcp_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            context = self._context(root)
            exposure = self._exposure(root)
            with mock.patch(
                "benchmarks.harness.mcp_catalog.run_bounded",
                return_value=self._process(["context", "references"]),
            ) as bounded:
                proof = probe_mcp_tool_catalog(
                    context=context,
                    exposure=exposure,
                    subject_id="futuremcp",
                    required_tool="futuremcp_context",
                )

        self.assertTrue(proof["required_tool_visible"])
        self.assertEqual(proof["required_operation"], "context")
        self.assertEqual(proof["tool_names"], ["context", "references"])
        self.assertEqual(proof["tool_count"], 2)
        self.assertEqual(len(proof["catalog_sha256"]), 64)
        self.assertEqual(
            bounded.call_args.kwargs["environment"],
            {
                "PATH": "/native/bin",
                "FUTURE_MCP_MODE": "benchmark",
            },
        )
        payload = bounded.call_args.kwargs["stdin_bytes"].decode()
        self.assertIn('"method":"initialize"', payload)
        self.assertIn('"method":"notifications/initialized"', payload)
        self.assertIn('"method":"tools/list"', payload)

    @unittest.skipIf(os.name == "nt", "select cannot inspect stdin pipes on Windows")
    def test_catalog_keeps_stdio_open_until_server_responds(self) -> None:
        server = """
import json, select, sys
requests = [json.loads(sys.stdin.buffer.readline()) for _ in range(3)]
if [request['method'] for request in requests] != [
    'initialize', 'notifications/initialized', 'tools/list'
]:
    raise SystemExit(2)
if select.select([sys.stdin], [], [], 0)[0]:
    raise SystemExit(0)  # This server discards queued requests on early EOF.
for response in (
    {'jsonrpc': '2.0', 'id': 1, 'result': {'protocolVersion': '2024-11-05'}},
    {'jsonrpc': '2.0', 'id': 2, 'result': {'tools': [{'name': 'context'}]}},
):
    print(json.dumps(response), flush=True)
sys.stdin.buffer.read()  # Exit after the client has received both responses.
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            context = self._context(root)
            exposure = McpExposure(
                name="futuremcp",
                command=sys.executable,
                args=("-u", "-c", server),
                cwd=context.workspace,
                semantic_identity={"transport": "stdio"},
            )
            proof = probe_mcp_tool_catalog(
                context=context,
                exposure=exposure,
                subject_id="futuremcp",
                required_tool="futuremcp_context",
            )
        self.assertEqual(proof["tool_names"], ["context"])

    def test_process_exits_without_initialize_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            context = self._context(root)
            exposure = McpExposure(
                name="futuremcp",
                command=sys.executable,
                args=("-c", "raise SystemExit(0)"),
                cwd=context.workspace,
                semantic_identity={"transport": "stdio"},
            )
            with self.assertRaisesRegex(ValueError, "no initialize response"):
                probe_mcp_tool_catalog(
                    context=context,
                    exposure=exposure,
                    subject_id="futuremcp",
                    required_tool="futuremcp_context",
                )

    def test_missing_required_operation_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch(
                "benchmarks.harness.mcp_catalog.run_bounded",
                return_value=self._process(["search", "references"]),
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    "required operation is not exposed: context",
                ):
                    probe_mcp_tool_catalog(
                        context=self._context(root),
                        exposure=self._exposure(root),
                        subject_id="futuremcp",
                        required_tool="futuremcp_context",
                    )

    def test_paginated_catalog_is_not_silently_treated_as_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch(
                "benchmarks.harness.mcp_catalog.run_bounded",
                return_value=self._process(["search"], next_cursor="page-2"),
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    "complete catalog proof is unavailable",
                ):
                    probe_mcp_tool_catalog(
                        context=self._context(root),
                        exposure=self._exposure(root),
                        subject_id="futuremcp",
                        required_tool="futuremcp_context",
                    )

    def test_non_stdio_subject_cannot_claim_stdio_catalog_proof(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exposure = self._exposure(root)
            exposure = McpExposure(
                name=exposure.name,
                command=exposure.command,
                args=exposure.args,
                cwd=exposure.cwd,
                semantic_identity={
                    "name": "futuremcp",
                    "transport": "http",
                },
                environment=exposure.environment,
            )
            with self.assertRaisesRegex(ValueError, "supports stdio only"):
                probe_mcp_tool_catalog(
                    context=self._context(root),
                    exposure=exposure,
                    subject_id="futuremcp",
                    required_tool="futuremcp_context",
                )


if __name__ == "__main__":
    unittest.main()
