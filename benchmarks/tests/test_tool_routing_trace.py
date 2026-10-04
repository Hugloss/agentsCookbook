from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from benchmarks.__main__ import main as benchmark_main
from benchmarks.tool_routing_trace import (
    TRACE_SCHEMA,
    exit_code,
    score_trace,
)


_READY_CATALOG = {
    "tools": [
        {"name": "mcp__hashmarks__task_evidence"},
        {"name": "mcp__GitHub__search"},
        {"name": "mcp__GitHub__fetch_file"},
    ]
}


def _trace(calls: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema": TRACE_SCHEMA,
        "host": "chatgpt",
        "calls": calls,
    }


class ToolRoutingTraceTests(unittest.TestCase):
    def test_hashmarks_before_native_search_is_pass(self) -> None:
        score = score_trace(
            catalog_payload=_READY_CATALOG,
            trace_payload=_trace(
                [
                    {
                        "tool": "mcp__hashmarks__task_evidence",
                        "status": "completed",
                        "output": {"schema": "hashmarks.task-evidence.v2"},
                    },
                    {
                        "tool": "mcp__GitHub__search",
                        "status": "completed",
                    },
                ]
            ),
            subject="hashmarks",
        )

        self.assertEqual(score["outcome"], "PASS")
        self.assertEqual(score["routing_evaluation"]["outcome"], "PASS")
        self.assertTrue(
            score["routing_evaluation"]["required_before_native_discovery"]
        )
        self.assertEqual(
            score["routing_evaluation"]["first_native_discovery_tool"],
            "mcp__GitHub__search",
        )
        self.assertEqual(score["calls"][0]["result_basis"], "captured-output")
        self.assertGreater(score["calls"][0]["result_bytes"], 0)
        self.assertEqual(exit_code(score), 0)

    def test_native_search_before_hashmarks_is_fail(self) -> None:
        score = score_trace(
            catalog_payload=_READY_CATALOG,
            trace_payload=_trace(
                [
                    {
                        "tool": "mcp__GitHub__search",
                        "status": "completed",
                    },
                    {
                        "tool": "mcp__hashmarks__task_evidence",
                        "status": "completed",
                        "output": {"schema": "hashmarks.task-evidence.v2"},
                    },
                ]
            ),
            subject="hashmarks",
        )

        self.assertEqual(score["outcome"], "FAIL")
        self.assertFalse(
            score["routing_evaluation"]["required_before_native_discovery"]
        )
        self.assertEqual(exit_code(score), 1)

    def test_missing_hashmarks_catalog_is_environment_blocked_not_fail(self) -> None:
        score = score_trace(
            catalog_payload={
                "tools": [
                    {"name": "mcp__GitHub__search"},
                    {"name": "mcp__GitHub__fetch_file"},
                ]
            },
            trace_payload=_trace(
                [
                    {
                        "tool": "mcp__GitHub__search",
                        "status": "completed",
                    }
                ]
            ),
            subject="hashmarks",
        )

        self.assertEqual(score["outcome"], "ENVIRONMENT_BLOCKED")
        self.assertEqual(
            score["catalog_admission"]["reason_codes"],
            ["required-subject-tool-missing"],
        )
        self.assertEqual(exit_code(score), 2)

    def test_opaque_router_before_hashmarks_is_unknown(self) -> None:
        score = score_trace(
            catalog_payload=_READY_CATALOG,
            trace_payload=_trace(
                [
                    {"tool": "functions.exec", "status": "completed"},
                    {
                        "tool": "mcp__hashmarks__task_evidence",
                        "status": "completed",
                        "output": {"schema": "hashmarks.task-evidence.v2"},
                    },
                    {
                        "tool": "mcp__GitHub__search",
                        "status": "completed",
                    },
                ]
            ),
            subject="hashmarks",
        )

        self.assertEqual(score["outcome"], "UNKNOWN")
        self.assertIsNone(
            score["routing_evaluation"]["required_before_native_discovery"]
        )
        self.assertEqual(
            score["calls"][0]["routing_observability"],
            "opaque",
        )
        self.assertEqual(exit_code(score), 3)

    def test_expanded_router_preserves_observable_child_order(self) -> None:
        score = score_trace(
            catalog_payload=_READY_CATALOG,
            trace_payload=_trace(
                [
                    {
                        "tool": "functions.exec",
                        "status": "completed",
                        "nested_calls": [
                            {
                                "tool": "mcp__hashmarks__task_evidence",
                                "status": "completed",
                                "output": {
                                    "schema": "hashmarks.task-evidence.v2"
                                },
                            },
                            {
                                "tool": "mcp__GitHub__search",
                                "status": "completed",
                            },
                        ],
                    }
                ]
            ),
            subject="hashmarks",
        )

        self.assertEqual(score["outcome"], "PASS")
        self.assertEqual(score["call_count"], 3)
        self.assertEqual(
            [row["ordinal"] for row in score["calls"]],
            [1, 2, 3],
        )
        self.assertEqual(
            score["calls"][0]["routing_observability"],
            "expanded",
        )

    def test_completed_hashmarks_without_observable_result_is_unknown(self) -> None:
        score = score_trace(
            catalog_payload=_READY_CATALOG,
            trace_payload=_trace(
                [
                    {
                        "tool": "mcp__hashmarks__task_evidence",
                        "status": "completed",
                    },
                    {
                        "tool": "mcp__GitHub__search",
                        "status": "completed",
                    },
                ]
            ),
            subject="hashmarks",
        )

        self.assertEqual(score["outcome"], "UNKNOWN")
        self.assertTrue(
            score["routing_evaluation"]["required_call_attempted"]
        )
        self.assertIsNone(
            score["routing_evaluation"]["required_call_succeeded"]
        )

    def test_capture_cannot_supply_derived_routing_authority(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "derived routing fields owned by the scorer",
        ):
            score_trace(
                catalog_payload=_READY_CATALOG,
                trace_payload=_trace(
                    [
                        {
                            "tool": "mcp__GitHub__search",
                            "tool_class": "other",
                            "status": "completed",
                        }
                    ]
                ),
                subject="hashmarks",
            )

    def test_trace_cli_writes_canonical_score_and_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            catalog = root / "catalog.json"
            trace = root / "trace.json"
            output = root / "score.json"
            catalog.write_text(
                json.dumps(_READY_CATALOG),
                encoding="utf-8",
            )
            trace.write_text(
                json.dumps(
                    _trace(
                        [
                            {
                                "tool": "mcp__hashmarks__task_evidence",
                                "status": "completed",
                                "result_bytes": 42,
                            },
                            {
                                "tool": "mcp__GitHub__search",
                                "status": "completed",
                            },
                        ]
                    )
                ),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = benchmark_main(
                    [
                        "tool-routing-trace",
                        "--catalog",
                        str(catalog),
                        "--trace",
                        str(trace),
                        "--subject",
                        "hashmarks",
                        "--output",
                        str(output),
                    ]
                )

            self.assertEqual(code, 0)
            self.assertEqual(stdout.getvalue().strip(), str(output))
            score = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(score["outcome"], "PASS")
            self.assertTrue(score["catalog_sha256"].startswith("sha256:"))
            self.assertTrue(score["trace_sha256"].startswith("sha256:"))


if __name__ == "__main__":
    unittest.main()
