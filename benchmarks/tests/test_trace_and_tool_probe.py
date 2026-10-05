from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from benchmarks.__main__ import main as benchmark_main
from benchmarks.adapters.opencode_native import OpenCodeNativeAgent
from benchmarks.adapters.registry import build_agent
from benchmarks.harness.identity import digest
from benchmarks.harness.model import TrialContext
from benchmarks.harness.oracle_reviews import validate_oracle_reviews
from benchmarks.harness.suite import load_suite
from benchmarks.harness.trace_diagnostics import (
    _hashmarks_evidence,
    _last_assistant_text_present,
    _opencode_calls,
    build_trace_diagnostics,
)
from benchmarks.harness.subject_exposure import exposure_probe_required_tool
from benchmarks.tool_probe import prepare_tool_probe_suite
from benchmarks.tool_probe_score import (
    smoke_gate,
    main as tool_probe_score_main,
)
from benchmarks.tool_routing import (
    NATIVE_READ,
    NATIVE_SEARCH,
    OTHER,
    SHELL,
    SUBJECT_REPOSITORY_INTELLIGENCE,
    TOOL_ROUTER,
    catalog_admission,
    classify_call,
    classify_tool,
    matches_subject_operation,
    required_before_native_discovery,
    required_call_result,
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

    def test_tool_probe_generator_accepts_future_subject_contract_without_code_map(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            shutil.copytree(SUITE, source)
            (source / "subjects/futuremcp.json").write_text(
                json.dumps(
                    {
                        "id": "futuremcp",
                        "kind": "repository_intelligence",
                        "adapter": "future-adapter",
                        "identity": {"id": "futuremcp", "version": "1"},
                        "capabilities": ["search"],
                        "configuration": {},
                        "exposure_probe": {
                            "required_tool": "futuremcp_context",
                        },
                    }
                ),
                encoding="utf-8",
            )
            destination = root / "futuremcp-probe"

            evidence = prepare_tool_probe_suite(
                source_suite=source,
                destination=destination,
                subject="futuremcp",
                task_ids=("locate-prefix-path-enumerator",),
            )

            generated = load_suite(destination)
            self.assertEqual(evidence["subject"], "futuremcp")
            self.assertEqual(evidence["required_tool"], "futuremcp_context")
            self.assertEqual(
                generated.agents["opencode-native"]["configuration"][
                    "diagnostic_required_tool"
                ],
                "futuremcp_context",
            )
            self.assertEqual(
                generated.subjects["futuremcp"]["exposure_probe"],
                {"required_tool": "futuremcp_context"},
            )

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
                "native_subject_identity_sha256": digest(
                    {"executable_sha256": "d" * 64}
                ),
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

    def test_agent_definition_accepts_generic_diagnostic_tool(self) -> None:
        agent = dict(load_suite(SUITE).agents["opencode-native"])
        agent["configuration"] = {"diagnostic_required_tool": "futuremcp_context"}
        built = build_agent(agent, budgets={"timeout_seconds": 600})
        self.assertEqual(built.diagnostic_required_tool, "futuremcp_context")

    def test_agent_definition_rejects_invalid_diagnostic_tool(self) -> None:
        agent = dict(load_suite(SUITE).agents["opencode-native"])
        agent["configuration"] = {"diagnostic_required_tool": " futuremcp_context "}
        with self.assertRaisesRegex(ValueError, "canonical tool name"):
            build_agent(agent, budgets={"timeout_seconds": 600})

    def test_exposure_probe_contract_is_subject_data_not_product_code(self) -> None:
        suite = load_suite(SUITE)
        suite.subjects["futuremcp"] = {
            "id": "futuremcp",
            "kind": "repository_intelligence",
            "adapter": "future-adapter",
            "identity": {"id": "futuremcp", "version": "1"},
            "capabilities": ["search"],
            "configuration": {},
            "exposure_probe": {"required_tool": "futuremcp_context"},
        }
        self.assertEqual(
            exposure_probe_required_tool(suite, "futuremcp"),
            "futuremcp_context",
        )

    def test_host_neutral_tool_classes_cover_opencode_and_chatgpt_names(self) -> None:
        self.assertEqual(
            classify_tool("hashmarks_task_evidence", subject="hashmarks"),
            SUBJECT_REPOSITORY_INTELLIGENCE,
        )
        self.assertEqual(
            classify_tool("mcp__hashmarks__task_evidence", subject="hashmarks"),
            SUBJECT_REPOSITORY_INTELLIGENCE,
        )
        self.assertEqual(
            classify_tool("grep", subject="hashmarks"),
            NATIVE_SEARCH,
        )
        self.assertEqual(
            classify_tool("mcp__GitHub__search", subject="hashmarks"),
            NATIVE_SEARCH,
        )
        self.assertEqual(
            classify_tool("mcp__GitHub__fetch_file", subject="hashmarks"),
            NATIVE_READ,
        )
        self.assertEqual(
            classify_tool("functions.exec", subject="hashmarks"),
            TOOL_ROUTER,
        )
        self.assertEqual(
            classify_tool("container.exec", subject="hashmarks"),
            SHELL,
        )
        self.assertEqual(
            classify_tool("image_gen", subject="hashmarks"),
            OTHER,
        )

    def test_chatgpt_style_hashmarks_call_must_precede_native_repository_discovery(
        self,
    ) -> None:
        required = "hashmarks_task_evidence"
        self.assertTrue(
            required_before_native_discovery(
                [
                    {
                        "tool": "mcp__hashmarks__task_evidence",
                        "status": "completed",
                        "result_bytes": 42,
                    },
                    {"tool": "mcp__GitHub__search", "status": "completed"},
                    {"tool": "mcp__GitHub__fetch_file", "status": "completed"},
                ],
                subject="hashmarks",
                required_tool=required,
            )
        )
        self.assertFalse(
            required_before_native_discovery(
                [
                    {"tool": "mcp__GitHub__search", "status": "completed"},
                    {
                        "tool": "mcp__hashmarks__task_evidence",
                        "status": "completed",
                        "result_bytes": 42,
                    },
                ],
                subject="hashmarks",
                required_tool=required,
            )
        )

    def test_generic_repository_api_fetch_uses_call_inputs_for_routing_class(
        self,
    ) -> None:
        self.assertEqual(
            classify_call(
                "mcp__GitHub__fetch",
                {
                    "url": (
                        "https://api.github.com/repos/acme/repo/"
                        "git/trees/abc123?recursive=1"
                    )
                },
                subject="hashmarks",
            ),
            NATIVE_SEARCH,
        )
        self.assertEqual(
            classify_call(
                "mcp__GitHub__fetch",
                {
                    "url": (
                        "https://api.github.com/repos/acme/repo/"
                        "contents/src/owner.py"
                    )
                },
                subject="hashmarks",
            ),
            NATIVE_READ,
        )

    def test_opaque_router_before_hashmarks_makes_order_unknown(self) -> None:
        required = "hashmarks_task_evidence"
        self.assertIsNone(
            required_before_native_discovery(
                [
                    {
                        "tool": "functions.exec",
                        "tool_class": TOOL_ROUTER,
                        "routing_observability": "opaque",
                    },
                    {
                        "tool": "mcp__hashmarks__task_evidence",
                        "status": "completed",
                        "result_bytes": 42,
                    },
                    {
                        "tool": "mcp__GitHub__search",
                        "status": "completed",
                    },
                ],
                subject="hashmarks",
                required_tool=required,
            )
        )
        self.assertTrue(
            required_before_native_discovery(
                [
                    {
                        "tool": "functions.exec",
                        "tool_class": TOOL_ROUTER,
                        "routing_observability": "expanded",
                    },
                    {
                        "tool": "mcp__hashmarks__task_evidence",
                        "status": "completed",
                        "result_bytes": 42,
                    },
                    {
                        "tool": "mcp__GitHub__search",
                        "status": "completed",
                    },
                ],
                subject="hashmarks",
                required_tool=required,
            )
        )

    def test_catalog_admission_distinguishes_missing_hashmarks_from_routing_failure(
        self,
    ) -> None:
        blocked = catalog_admission(
            ["mcp__GitHub__search", "mcp__GitHub__fetch_file"],
            subject="hashmarks",
            required_tool="hashmarks_task_evidence",
        )
        self.assertEqual(blocked["status"], "ENVIRONMENT_BLOCKED")
        self.assertEqual(
            blocked["reason_codes"],
            ["required-subject-tool-missing"],
        )
        self.assertEqual(
            blocked["native_discovery_classes"],
            [NATIVE_READ, NATIVE_SEARCH],
        )

        ready = catalog_admission(
            [
                "mcp__hashmarks__task_evidence",
                "mcp__GitHub__search",
                "mcp__GitHub__fetch_file",
            ],
            subject="hashmarks",
            required_tool="hashmarks_task_evidence",
        )
        self.assertEqual(ready["status"], "READY")
        self.assertTrue(ready["required_tool_visible"])
        self.assertEqual(ready["reason_codes"], [])

        generic_fetch = catalog_admission(
            [
                "mcp__hashmarks__task_evidence",
                "mcp__GitHub__fetch",
            ],
            subject="hashmarks",
            required_tool="hashmarks_task_evidence",
        )
        self.assertEqual(generic_fetch["status"], "READY")
        self.assertEqual(
            generic_fetch["native_discovery_classes"],
            [NATIVE_READ, NATIVE_SEARCH],
        )

    def test_tool_routing_catalog_cli_is_model_free_admission(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            blocked_catalog = root / "blocked.json"
            blocked_catalog.write_text(
                json.dumps(
                    {
                        "tools": [
                            {"name": "mcp__GitHub__search"},
                            {"name": "mcp__GitHub__fetch_file"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = benchmark_main(
                    [
                        "tool-routing-catalog",
                        "--catalog",
                        str(blocked_catalog),
                        "--subject",
                        "hashmarks",
                        "--required-tool",
                        "hashmarks_task_evidence",
                    ]
                )
            self.assertEqual(code, 2)
            self.assertEqual(
                json.loads(stdout.getvalue())["reason_codes"],
                ["required-subject-tool-missing"],
            )

            ready_catalog = root / "ready.json"
            ready_catalog.write_text(
                json.dumps(
                    [
                        "mcp__hashmarks__task_evidence",
                        "mcp__GitHub__search",
                    ]
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = benchmark_main(
                    [
                        "tool-routing-catalog",
                        "--catalog",
                        str(ready_catalog),
                        "--subject",
                        "hashmarks",
                        "--required-tool",
                        "hashmarks_task_evidence",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stdout.getvalue())["status"], "READY")

    def test_required_tool_name_forms(self) -> None:
        self.assertTrue(
            matches_subject_operation(
                "tools.enola.explore",
                subject="enola",
                operation="explore",
            )
        )
        self.assertFalse(
            matches_subject_operation(
                "enola.query_facts",
                subject="enola",
                operation="explore",
            )
        )

    def test_required_call_outcomes_preserve_unknown_attempt_and_success(self) -> None:
        required = "hashmarks_task_evidence"
        self.assertEqual(
            required_call_result(
                None,
                subject="hashmarks",
                required_tool=required,
            ),
            (None, None),
        )
        self.assertEqual(
            required_call_result(
                [],
                subject="hashmarks",
                required_tool=required,
            ),
            (False, False),
        )
        self.assertEqual(
            required_call_result(
                [{"tool": required, "status": "error", "result_bytes": 50}],
                subject="hashmarks",
                required_tool=required,
            ),
            (True, False),
        )
        self.assertEqual(
            required_call_result(
                [{"tool": required, "status": "completed", "result_bytes": 42}],
                subject="hashmarks",
                required_tool=required,
            ),
            (True, True),
        )
        self.assertEqual(
            required_call_result(
                [{"tool": required, "status": "completed", "result_bytes": None}],
                subject="hashmarks",
                required_tool=required,
            ),
            (True, None),
        )
        self.assertFalse(
            required_before_native_discovery(
                [
                    {"tool": "grep"},
                    {
                        "tool": required,
                        "status": "completed",
                        "result_bytes": 42,
                    },
                ],
                subject="hashmarks",
                required_tool=required,
            )
        )
        self.assertTrue(
            required_before_native_discovery(
                [
                    {
                        "tool": required,
                        "status": "completed",
                        "result_bytes": 42,
                    },
                    {"tool": "grep"},
                ],
                subject="hashmarks",
                required_tool=required,
            )
        )

    def test_smoke_gate_requires_three_proven_early_calls(self) -> None:
        row = {"status": "PASS", "required_call_succeeded": True,
               "required_before_native_discovery": True}
        score = {"schema": "agents-cookbook-tool-probe-score.v3",
                 "subject": "hashmarks", "required_tool": "hashmarks_task_evidence",
                 "expected_trials": 3, "observed_trials": 3,
                 "required_tool_results": [dict(row, trial_id=f"trial-{n}", task_id="task")
                                           for n in range(3)]}
        smoke_gate(score, subject="hashmarks")
        score["required_tool_results"][1]["required_before_native_discovery"] = None
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
            self.assertEqual(score["schema"], "agents-cookbook-tool-probe-score.v3")
            self.assertEqual(score["required_call_successes"], 0)
            self.assertEqual(score["required_call_failures"], 1)
            self.assertEqual(score["required_call_unknown"], 1)
            self.assertTrue(score["required_tool_results"][0]["required_call_attempted"])
            self.assertEqual(score["required_before_native_discovery_failures"], 1)
            self.assertEqual(score["required_before_native_discovery_unknown"], 1)


if __name__ == "__main__":
    unittest.main()
