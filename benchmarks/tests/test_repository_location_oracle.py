from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from benchmarks.adapters.oracles import RepositoryLocationOracle
from benchmarks.harness.model import Observation, TrialContext
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
                "execution": {
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
                "execution": {
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
