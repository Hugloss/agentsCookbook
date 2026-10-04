from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from benchmarks.adapters.opencode_native import OpenCodeNativeAgent
from benchmarks.adapters.registry import build_agent
from benchmarks.harness.model import TrialContext
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
    _matches_required, _required_call_result, _required_before_search,
    smoke_gate, main as tool_probe_score_main,
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

    def test_tool_probe_reuses_exact_reviewed_tasks_and_reviews(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "hashmarks-probe"
            evidence = prepare_tool_probe_suite(
                source_suite=SUITE, destination=destination, subject="hashmarks"
            )
            suite = load_suite(destination)
            self.assertEqual(len(suite.trial_definitions()), 9)
            self.assertEqual(evidence["required_tool"], "hashmarks_task_evidence")
            self.assertTrue(validate_oracle_reviews(suite, require_complete=True)["complete"])
            self.assertEqual(suite.tasks["locate-prefix-path-enumerator"],
                             load_suite(SUITE).tasks["locate-prefix-path-enumerator"])
            self.assertEqual(
                (destination / "tasks/locate-prefix-path-enumerator.json").read_bytes(),
                (SUITE / "tasks/locate-prefix-path-enumerator.json").read_bytes(),
            )
            self.assertEqual(suite.agents["opencode-native"]["configuration"]["diagnostic_required_tool"],
                             "hashmarks_task_evidence")
            self.assertTrue((destination / "score.py").is_file())
            self.assertIn(
                f"BENCHMARK_SUITE_PATH={destination}",
                (destination / ".env.example").read_text(encoding="utf-8"),
            )
            self.assertEqual(prepare_tool_probe_suite(
                source_suite=SUITE, destination=destination, subject="hashmarks", reuse=True
            ), evidence)

    def test_diagnostic_agent_adds_required_instruction_only_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            control = root / "control"
            workspace.mkdir()
            control.mkdir()
            (control / "opencode-native-evidence.json").write_text(json.dumps({
                "selected_server": "hashmarks",
                "opencode_executable_path": str(Path("/bin/opencode").resolve()),
                "opencode_executable_sha256": "c" * 64,
                "native_config_sha256": "a" * 64,
                "subject_exposure_sha256": "b" * 64,
                "native_subject_identity": {"executable_sha256": "d" * 64},
                "native_mcp_servers": [],
            }), encoding="utf-8")
            context = TrialContext(workspace, control, {"BENCHMARK_OPENCODE_AGENT": "build"})
            process = mock.Mock(elapsed_ms=1, stdout=b"", stderr=b"",
                                executable_missing=False, stdout_truncated=False)
            process.metrics.return_value = {}
            agent = OpenCodeNativeAgent(diagnostic_required_tool="hashmarks_task_evidence")
            with mock.patch("benchmarks.adapters.opencode_native._native_environment",
                            return_value={"OPENCODE_BIN": "/bin/opencode"}), mock.patch(
                "benchmarks.adapters.opencode_native._sha256_file",
                return_value="c" * 64,
            ), mock.patch(
                "benchmarks.adapters.opencode_native._runtime_call", return_value=(None, process)
            ):
                agent.run(context, "Reviewed task", None)
            prompt = (control / "opencode-prompt.txt").read_text(encoding="utf-8")
            self.assertIn("call hashmarks_task_evidence", prompt)
            self.assertTrue(prompt.endswith("Reviewed task"))

    def test_agent_definition_rejects_unknown_diagnostic_tool(self) -> None:
        agent = dict(load_suite(SUITE).agents["opencode-native"])
        agent["configuration"] = {"diagnostic_required_tool": "random_tool"}
        with self.assertRaisesRegex(ValueError, "unsupported diagnostic required tool"):
            build_agent(agent, budgets={"timeout_seconds": 600})

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
        self.assertEqual(_required_call_result([
            {"tool": required, "status": "completed", "result_bytes": None},
        ], "hashmarks", required), (True, None))
        self.assertFalse(_required_before_search([
            {"tool": "grep"},
            {"tool": required, "status": "completed", "result_bytes": 42},
        ], "hashmarks", required))
        self.assertTrue(_required_before_search([
            {"tool": required, "status": "completed", "result_bytes": 42},
            {"tool": "grep"},
        ], "hashmarks", required))

    def test_smoke_gate_requires_three_proven_early_calls(self) -> None:
        row = {"status": "PASS", "required_call_succeeded": True,
               "required_before_file_search": True}
        score = {"schema": "agents-cookbook-tool-probe-score.v2",
                 "subject": "hashmarks", "required_tool": "hashmarks_task_evidence",
                 "expected_trials": 3, "observed_trials": 3,
                 "required_tool_results": [dict(row, trial_id=f"trial-{n}", task_id="task")
                                           for n in range(3)]}
        smoke_gate(score, subject="hashmarks")
        score["required_tool_results"][1]["required_before_file_search"] = None
        with self.assertRaises(ValueError):
            smoke_gate(score, subject="hashmarks")

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
            self.assertEqual(score["schema"], "agents-cookbook-tool-probe-score.v2")
            self.assertEqual(score["required_call_successes"], 0)
            self.assertEqual(score["required_call_failures"], 1)
            self.assertEqual(score["required_call_unknown"], 1)
            self.assertTrue(score["required_tool_results"][0]["required_call_attempted"])
            self.assertEqual(score["required_before_file_search_failures"], 1)
            self.assertEqual(score["required_before_file_search_unknown"], 1)


if __name__ == "__main__":
    unittest.main()
