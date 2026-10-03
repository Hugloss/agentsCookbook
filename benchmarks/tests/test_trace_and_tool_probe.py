from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from benchmarks.harness.oracle_reviews import validate_oracle_reviews
from benchmarks.harness.suite import load_suite
from benchmarks.harness.trace_diagnostics import (
    _hashmarks_evidence,
    _last_assistant_text_present,
    _opencode_calls,
    build_trace_diagnostics,
)
from benchmarks.tool_probe import prepare_tool_probe_suite
from benchmarks.tool_probe_score import (
    _matches_required, _required_call_result, main as tool_probe_score_main,
)


SUITE = (
    Path(__file__).resolve().parents[1]
    / "suites/repository-intelligence/heldout-v1"
)


class TraceAndToolProbeTests(unittest.TestCase):
    def test_trace_projection_separates_denial_from_retrieval_absence(self) -> None:
        packet = {
            "schema": "hashmarks.task-evidence.v2",
            "retrieval": {"results": [{"path": "other.py", "name": "other"}]},
            "ownership": {"status": "ambiguous"},
        }
        receipt = {
            "condition": {"subject": "hashmarks"},
            "execution": {"workspace_root": "/trial/workspace"},
            "task": {"oracle": {"configuration": {"expected": {
                "path": "owner.py", "symbol": "owner"
            }}}},
        }
        trace = {"messages": [{"parts": [
            {"type": "tool", "tool": "hashmarks_task_evidence", "state": {
                "status": "completed", "input": {"task": "find owner"},
                "output": json.dumps(packet),
            }},
            {"type": "tool", "tool": "read", "state": {
                "status": "error", "input": {"filePath": "/trial/workspace/owner.py"},
                "output": "The user rejected permission to use this specific tool call.",
            }},
        ]}]}
        calls = _opencode_calls(trace, receipt)
        self.assertEqual(calls[0]["hashmarks_evidence"]["expected_target_rank"], None)
        self.assertEqual(
            calls[0]["hashmarks_evidence"]["expected_target_observability"],
            "absent-from-returned-candidates",
        )
        self.assertEqual(calls[1]["failure"], "permission-denied")
        self.assertEqual(calls[1]["path_attempted"], "owner.py")
        self.assertNotIn("output", calls[0])
        self.assertEqual(
            _hashmarks_evidence("not json", {"path": "owner.py", "symbol": "owner"}),
            {"packet_status": "unparseable"},
        )
        self.assertFalse(_last_assistant_text_present({"messages": [
            {"info": {"role": "assistant"}, "parts": [{"type": "tool"}]},
        ]}))
        self.assertTrue(_last_assistant_text_present({"messages": [
            {"info": {"role": "assistant"}, "parts": [{"type": "text", "text": "answer"}]},
        ]}))

    def test_verified_bundle_projection_does_not_guess_unknown_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trial = root / ("a" * 64)
            trial.mkdir()
            (trial / "result.json").write_text(json.dumps({
                "trial_id": trial.name, "definition_id": "definition",
                "condition": {"id": "enola", "subject": "enola"},
                "task": {"id": "task"},
                "execution": {"artifacts": {}},
                "measurements": {"agent": {}},
            }), encoding="utf-8")
            with mock.patch(
                "benchmarks.harness.trace_diagnostics.verify_bundle",
                return_value=(True, None),
            ):
                result = build_trace_diagnostics(root)
            self.assertEqual(result["summary"]["trace_states"], {"missing": 1})
            self.assertIsNone(result["trials"][0]["calls"])
            self.assertEqual(result["summary"]["subject_calls"], {})

    def test_tool_probe_is_separate_and_pending_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "hashmarks-probe"
            evidence = prepare_tool_probe_suite(
                source_suite=SUITE, destination=destination, subject="hashmarks"
            )
            suite = load_suite(destination)
            self.assertEqual(len(suite.trial_definitions()), 9)
            self.assertEqual(evidence["required_tool"], "hashmarks_task_evidence")
            self.assertFalse(
                validate_oracle_reviews(suite, require_complete=False)["complete"]
            )
            self.assertIn(
                "call hashmarks_task_evidence",
                suite.tasks["locate-prefix-path-enumerator"]["prompt"],
            )
            self.assertTrue((destination / "score.py").is_file())
            self.assertIn(
                f"BENCHMARK_SUITE_PATH={destination}",
                (destination / ".env.example").read_text(encoding="utf-8"),
            )

    def test_required_tool_name_forms(self) -> None:
        self.assertTrue(_matches_required(
            "tools.enola.explore", "enola", "enola_explore"
        ))
        self.assertFalse(_matches_required(
            "enola.query_facts", "enola", "enola_explore"
        ))

    def test_required_call_outcomes_preserve_unknown_attempt_and_success(self) -> None:
        required = "hashmarks_task_evidence"
        self.assertEqual(_required_call_result(None, "hashmarks", required), (None, None))
        self.assertEqual(_required_call_result([], "hashmarks", required), (False, False))
        self.assertEqual(_required_call_result([
            {"tool": required, "status": "error", "result_bytes": 50},
        ], "hashmarks", required), (True, False))
        self.assertEqual(_required_call_result([
            {"tool": required, "status": "completed", "result_bytes": 42},
        ], "hashmarks", required), (True, True))

    def test_tool_probe_score_reports_attempt_failure_and_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "hashmarks-probe"
            prepare_tool_probe_suite(
                source_suite=SUITE, destination=destination, subject="hashmarks"
            )
            definition = load_suite(destination).trial_definitions()[0]["definition_id"]
            output = Path(tmp) / "score.json"
            trials = [
                {"trial_id": "a", "definition_id": definition, "task_id": "one",
                 "status": "PASS", "calls": [{"tool": "hashmarks_task_evidence",
                 "status": "error", "result_bytes": 12}]},
                {"trial_id": "b", "definition_id": definition, "task_id": "one",
                 "status": "INCOMPLETE", "calls": None},
            ]
            argv = ["score.py", "--results", str(Path(tmp) / "results"),
                    "--output", str(output), "--agent", "opencode-native",
                    "--definition-id", definition]
            with mock.patch("sys.argv", argv), mock.patch(
                "benchmarks.tool_probe_score.build_report",
                return_value={"expected_trials": 2, "observed_trials": 2,
                              "status_counts": {"PASS": 1, "INCOMPLETE": 1}},
            ), mock.patch(
                "benchmarks.tool_probe_score.build_trace_diagnostics",
                return_value={"trials": trials},
            ):
                self.assertEqual(tool_probe_score_main(destination), 0)
            score = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(score["required_call_successes"], 0)
            self.assertEqual(score["required_call_failures"], 1)
            self.assertEqual(score["required_call_unknown"], 1)
            self.assertTrue(score["required_tool_results"][0]["required_call_attempted"])


if __name__ == "__main__":
    unittest.main()
