from __future__ import annotations

import unittest

from benchmarks.adapters.codex import _metrics


class SubjectToolMeasurementTests(unittest.TestCase):
    def test_codex_reports_exact_subject_operation_names_as_complete(self) -> None:
        events = [
            {
                "type": "item.completed",
                "item": {
                    "type": "mcp_tool_call",
                    "server": "futuremcp",
                    "tool": "context",
                    "result": {"ok": True},
                    "error": None,
                    "status": "completed",
                },
            },
            {
                "type": "turn.completed",
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 2,
                    "cached_input_tokens": 0,
                },
            },
        ]

        metrics = _metrics(events, subject_server="futuremcp")

        self.assertTrue(metrics["subject_tool_invoked"])
        self.assertEqual(metrics["subject_mcp_calls"], 1)
        self.assertEqual(metrics["subject_tool_names"], ["context"])
        self.assertEqual(metrics["subject_tool_observability"], "complete")
        evidence = metrics["subject_tool_result_evidence"]
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["operation"], "context")
        self.assertEqual(evidence[0]["status"], "completed")
        self.assertGreater(evidence[0]["result_bytes"], 0)
        self.assertFalse(evidence[0]["error_present"])
        self.assertEqual(
            evidence[0]["outcome"],
            "successful-result-observed",
        )


if __name__ == "__main__":
    unittest.main()
