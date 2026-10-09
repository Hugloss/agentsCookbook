"""Focused contracts for Harbor behavioral command-oracle projection."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from benchmarks.harness.harbor_behavioral import (
    HarborBehavioralError,
    behavioral_contract,
    behavioral_verifier,
    prepare_behavioral_workspace,
    workspace_manifest,
)
from benchmarks.harbor_matrix import (
    load_matrix,
    mode_contract,
    validate_projection,
)
from benchmarks.harness.suite import load_suite


ROOT = Path(__file__).resolve().parents[2]
SUITE = (
    ROOT
    / "benchmarks"
    / "suites"
    / "repository-intelligence"
    / "behavioral-v4"
)
CHANGE_IMPACT_MATRIX = (
    ROOT
    / "benchmarks"
    / "harbor"
    / "repository-intelligence-change-impact-ablation-v1.json"
)
POST_CHANGE_MATRIX = (
    ROOT
    / "benchmarks"
    / "harbor"
    / "repository-intelligence-post-change-ablation-v1.json"
)


class HarborBehavioralTests(unittest.TestCase):
    def test_changed_path_matrices_admit_frozen_behavioral_tasks(self) -> None:
        suite = load_suite(SUITE)
        for path, component, count in (
            (CHANGE_IMPACT_MATRIX, "change_impact", 4),
            (POST_CHANGE_MATRIX, "post_change", 4),
        ):
            with self.subTest(component=component):
                matrix = load_matrix(path)
                mode = mode_contract(matrix, "matrix")
                self.assertEqual(matrix["ablation"]["component"], component)
                self.assertEqual(len(mode.tasks), count)
                validate_projection(
                    matrix=matrix,
                    suite=suite,
                    mode=mode,
                    harnesses=tuple(matrix["harnesses"]),
                    tasks=mode.tasks,
                )

    def test_behavioral_contract_reuses_frozen_command_oracle(self) -> None:
        suite = load_suite(SUITE)

        edit = behavioral_contract(suite, suite.tasks["change_impact-00"])
        read_only = behavioral_contract(suite, suite.tasks["post_change-02"])

        self.assertEqual(edit["kind"], "command-lexigram")
        self.assertEqual(edit["task_id"], "change_impact-00")
        self.assertEqual(
            edit["allowed_change_globs"],
            ["benchmark_case/change_impact_00/src/core.py"],
        )
        self.assertEqual(read_only["task_id"], "post_change-02")
        self.assertEqual(read_only["allowed_change_globs"], [])

    def test_behavioral_contract_rejects_noncanonical_oracle_argv(self) -> None:
        suite = load_suite(SUITE)
        task = json.loads(json.dumps(suite.tasks["change_impact-00"]))
        task["oracle"]["configuration"]["grade_argv"] = [
            "{python}",
            "{suite}/other.py",
            "grade",
            "change_impact-00",
        ]

        with self.assertRaisesRegex(
            HarborBehavioralError,
            "canonical suite oracle argv",
        ):
            behavioral_contract(suite, task)

    def test_prepare_applies_verified_mutation_then_freezes_baseline(self) -> None:
        suite = load_suite(SUITE)
        task = suite.tasks["change_impact-00"]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            tests = root / "tests"
            workspace.mkdir()
            tests.mkdir()
            subprocess.run(
                ["git", "init", "-q", str(workspace)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            projection = prepare_behavioral_workspace(
                suite=suite,
                task=task,
                workspace=workspace,
                tests=tests,
                control_root=root,
            )

            core = (
                workspace
                / "benchmark_case/change_impact_00/src/core.py"
            )
            self.assertIn('return "old"', core.read_text(encoding="utf-8"))
            self.assertEqual(
                projection["mutation_identity"]["changed_paths"],
                sorted(task["mutation"]["changed_paths"]),
            )
            self.assertEqual(
                projection["schema"],
                "agentscookbook.harbor-behavioral-projection.v1",
            )
            self.assertTrue((tests / "oracle.py").is_file())
            self.assertTrue((tests / "cases.json").is_file())
            baseline = json.loads(
                (tests / "baseline.json").read_text(encoding="utf-8")
            )
            self.assertIn(
                "benchmark_case/change_impact_00/src/core.py",
                baseline,
            )
            frozen = json.loads(
                (tests / "projection.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                frozen["baseline_manifest_sha256"],
                projection["baseline_manifest_sha256"],
            )

    def test_workspace_manifest_excludes_git_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / ".git").mkdir()
            (workspace / ".git/config").write_text("secret", encoding="utf-8")
            (workspace / "a.txt").write_text("A", encoding="utf-8")

            manifest = workspace_manifest(workspace)

        self.assertEqual(set(manifest), {"a.txt"})

    def test_behavioral_verifier_uses_oracle_and_post_mutation_baseline(self) -> None:
        suite = load_suite(SUITE)
        contract = behavioral_contract(suite, suite.tasks["post_change-00"])

        script = behavioral_verifier(contract)

        self.assertIn("/tests/baseline.json", script)
        self.assertIn("/tests/oracle.py", script)
        self.assertIn("BENCHMARK_OBSERVATION_PATH", script)
        self.assertIn("contamination", script)
        self.assertIn('Path("/logs/verifier/reward.txt")', script)
        self.assertNotIn("reasoning_content", script)


if __name__ == "__main__":
    unittest.main()
