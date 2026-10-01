from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from benchmarks.adapters.oracles import (
    REPOSITORY_LOCATION_NORMALIZATION_POLICY,
    REPOSITORY_LOCATION_SCORING_POLICY,
    RepositoryLocationOracle,
)
from benchmarks.adapters.registry import build_oracle
from benchmarks.harness.identity import execution_evidence_id
from benchmarks.harness.model import Observation, TrialContext
from benchmarks.harness.regrade import regrade_repository_location_receipt
from benchmarks.harness.report import _aggregate_condition


EXPECTED = {
    "path": "hashmarks/codemap/repository_index_store.py",
    "symbol": "paths_under",
}


class RepositoryLocationOracleTests(unittest.TestCase):
    def _context(self, root: Path) -> TrialContext:
        workspace = root / "workspace"
        control = root / "control"
        target = workspace / EXPECTED["path"]
        target.parent.mkdir(parents=True)
        target.write_text("pass\n", encoding="utf-8")
        control.mkdir()
        return TrialContext(workspace, control, {})

    def _oracle(self) -> RepositoryLocationOracle:
        return RepositoryLocationOracle(
            "repository-location-test",
            "2",
            EXPECTED,
        )

    def _grade(self, context: TrialContext, final_message: str) -> Observation:
        return self._oracle().grade(
            context,
            Observation({"final_message": final_message}, ""),
        )

    def test_registry_builds_repository_location_oracle(self) -> None:
        oracle = build_oracle(
            {
                "adapter": "repository-location-json",
                "identity": {"id": "location", "version": "2"},
                "configuration": {"expected": EXPECTED},
            },
            timeout_seconds=30,
        )
        self.assertIsInstance(oracle, RepositoryLocationOracle)

    def test_bare_json_is_semantically_correct_and_format_compliant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context = self._context(Path(tmp))
            grade = self._grade(
                context,
                '{"path":"hashmarks/codemap/repository_index_store.py",'
                '"symbol":"paths_under"}',
            )
            self.assertTrue(grade.payload["passed"])
            self.assertTrue(grade.payload["semantic_success"])
            self.assertTrue(grade.payload["format_compliant"])
            self.assertTrue(grade.payload["semantic_gradeable"])
            self.assertEqual(grade.payload["semantic_status"], "CORRECT")
            self.assertEqual(
                grade.payload["normalization_policy"],
                REPOSITORY_LOCATION_NORMALIZATION_POLICY,
            )
            self.assertEqual(
                grade.payload["scoring_policy"],
                REPOSITORY_LOCATION_SCORING_POLICY,
            )
            self.assertEqual(grade.payload["normalized_actual"], EXPECTED)

    def test_single_json_fence_preserves_semantics_but_not_format_compliance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context = self._context(Path(tmp))
            grade = self._grade(
                context,
                '```json\n'
                '{"path":"hashmarks/codemap/repository_index_store.py",'
                '"symbol":"paths_under"}\n'
                '```',
            )
            self.assertTrue(grade.payload["passed"])
            self.assertTrue(grade.payload["semantic_success"])
            self.assertFalse(grade.payload["format_compliant"])
            self.assertIn("json-fence-unwrapped", grade.payload["normalizations"])

    def test_qualified_symbol_normalizes_to_terminal_symbol(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context = self._context(Path(tmp))
            grade = self._grade(
                context,
                '{"path":"hashmarks/codemap/repository_index_store.py",'
                '"symbol":"WorkspaceMapStore.paths_under"}',
            )
            self.assertTrue(grade.payload["semantic_success"])
            self.assertEqual(
                grade.payload["normalized_actual"]["symbol"],
                "paths_under",
            )
            self.assertIn(
                "qualified-symbol-to-terminal",
                grade.payload["normalizations"],
            )

    def test_workspace_absolute_path_normalizes_to_repository_relative(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context = self._context(Path(tmp))
            absolute = (context.workspace / EXPECTED["path"]).resolve()
            grade = self._grade(
                context,
                json.dumps(
                    {
                        "path": str(absolute),
                        "symbol": "paths_under",
                    }
                ),
            )
            self.assertTrue(grade.payload["semantic_success"])
            self.assertIn(
                "workspace-absolute-path-to-relative",
                grade.payload["normalizations"],
            )
            self.assertEqual(grade.payload["normalized_actual"], EXPECTED)

    def test_wrong_location_remains_semantic_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context = self._context(Path(tmp))
            grade = self._grade(
                context,
                '{"path":"hashmarks/codemap/repository_file_discovery.py",'
                '"symbol":"_iter_admitted_repository_files"}',
            )
            self.assertFalse(grade.payload["passed"])
            self.assertFalse(grade.payload["semantic_success"])
            self.assertTrue(grade.payload["semantic_gradeable"])
            self.assertEqual(grade.payload["semantic_status"], "INCORRECT")
            self.assertTrue(grade.payload["format_compliant"])

    def test_prose_around_json_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context = self._context(Path(tmp))
            grade = self._grade(
                context,
                'Here is the answer: {"path":"hashmarks/codemap/'
                'repository_index_store.py","symbol":"paths_under"}',
            )
            self.assertFalse(grade.payload["semantic_success"])
            self.assertFalse(grade.payload["semantic_gradeable"])
            self.assertEqual(grade.payload["semantic_status"], "UNSCORABLE")
            self.assertFalse(grade.payload["format_compliant"])
            self.assertIn("actual_text", grade.payload)

    def test_malformed_json_fence_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context = self._context(Path(tmp))
            grade = self._grade(
                context,
                '```json\n'
                '{"path":"hashmarks/codemap/repository_index_store.py",'
                '"symbol":"paths_under"}',
            )
            self.assertFalse(grade.payload["semantic_success"])
            self.assertFalse(grade.payload["format_compliant"])

    def test_multiple_objects_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context = self._context(Path(tmp))
            grade = self._grade(
                context,
                '{"path":"hashmarks/codemap/repository_index_store.py",'
                '"symbol":"paths_under"}\n{}',
            )
            self.assertFalse(grade.payload["semantic_success"])
            self.assertFalse(grade.payload["format_compliant"])

    def test_report_separates_semantic_success_from_format_compliance(self) -> None:
        receipts = [
            {
                "status": "PASS",
                "execution": {},
                "scoring": {
                    "oracle_grade": {
                        "semantic_success": True,
                        "format_compliant": False,
                    }
                },
                "authority": {"subject": {"available": False}},
                "measurements": {"agent": {}},
            },
            {
                "status": "FAIL",
                "execution": {},
                "scoring": {
                    "oracle_grade": {
                        "semantic_success": False,
                        "format_compliant": True,
                    }
                },
                "authority": {"subject": {"available": False}},
                "measurements": {"agent": {}},
            },
        ]
        report = _aggregate_condition(receipts)
        self.assertEqual(report["task_success_rate"], 0.5)
        self.assertEqual(report["semantic_success_rate"], 0.5)
        self.assertEqual(report["semantic_success_denominator"], 2)
        self.assertEqual(report["format_compliance_rate"], 0.5)
        self.assertEqual(report["format_compliance_denominator"], 2)

    def test_execution_evidence_identity_ignores_scoring_only_task_changes(
        self,
    ) -> None:
        task_v1 = {
            "id": "locate",
            "version": 1,
            "family": "python-localization",
            "repository": {"url": "x", "commit": "a", "tree": "b"},
            "prompt": "find it",
            "mode": "read_only",
            "mutation": None,
            "budgets": {"timeout_seconds": 1},
            "contamination": {
                "allowed_change_globs": [],
                "allowed_generated_globs": [],
            },
            "oracle": {"adapter": "expected-json"},
        }
        task_v2 = {
            **task_v1,
            "version": 2,
            "oracle": {"adapter": "repository-location-json"},
        }
        kwargs = {
            "condition": {"id": "bare", "agent": "a", "subject": "none"},
            "trial": 0,
            "seed": 1,
            "subject_identity": {"available": True},
            "agent_identity": {"available": True},
            "harness_identity": {"commit": "h"},
            "environment_identity": {"env": "e"},
            "mutation_identity": None,
        }
        self.assertEqual(
            execution_evidence_id(task=task_v1, **kwargs),
            execution_evidence_id(task=task_v2, **kwargs),
        )

    def test_offline_regrade_reuses_frozen_execution_without_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context = self._context(Path(tmp))
            receipt = {
                "execution": {
                    "evidence_identity": "a" * 64,
                    "workspace_root": str(context.workspace),
                    "agent_answer": (
                        "```json\n"
                        '{"path":"hashmarks/codemap/repository_index_store.py",'
                        '"symbol":"WorkspaceMapStore.paths_under"}\n'
                        "```"
                    ),
                }
            }
            first = regrade_repository_location_receipt(receipt, self._oracle())
            second = regrade_repository_location_receipt(receipt, self._oracle())
            self.assertEqual(first, second)
            self.assertEqual(first["execution_evidence_id"], "a" * 64)
            self.assertTrue(first["oracle_grade"]["semantic_success"])
            self.assertFalse(first["oracle_grade"]["format_compliant"])
            self.assertIn(
                "qualified-symbol-to-terminal",
                first["oracle_grade"]["normalizations"],
            )

            changed_oracle = RepositoryLocationOracle(
                "repository-location-test",
                "3",
                {
                    "path": "hashmarks/codemap/repository_index_store.py",
                    "symbol": "different_symbol",
                },
            )
            changed = regrade_repository_location_receipt(receipt, changed_oracle)
            self.assertEqual(changed["execution_evidence_id"], "a" * 64)
            self.assertNotEqual(
                changed["projection_identity"],
                first["projection_identity"],
            )
            self.assertFalse(changed["oracle_grade"]["semantic_success"])

    def test_path_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context = self._context(Path(tmp))
            grade = self._grade(
                context,
                '{"path":"../outside.py","symbol":"paths_under"}',
            )
            self.assertFalse(grade.payload["semantic_success"])
            self.assertTrue(grade.payload["format_compliant"])
            self.assertIn("escapes", grade.payload["reason"])


if __name__ == "__main__":
    unittest.main()
