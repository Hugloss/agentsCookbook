"""Harbor matrices use the ordinary campaign store and recovery contract."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from benchmarks.__main__ import main
from benchmarks.harbor_matrix import HarborSettings
from benchmarks.matrix_profiles import harbor_suite, load_profile


class HarborSharedCampaignTests(unittest.TestCase):
    def test_registry_projects_six_and_fifty_four_trials(self) -> None:
        for name, count in (("harbor-smoke", 6), ("harbor-full", 54)):
            with self.subTest(name=name):
                suite, _ = harbor_suite(load_profile(name))
                self.assertEqual(len(suite.trial_definitions()), count)

    def _environment(self, root: Path):
        env = root / ".env"
        env.write_text("HASHMARKS_BENCH_SOURCE=/unused\nBENCHMARK_HARBOR_MODEL=provider/model\n")
        settings = HarborSettings(
            executable="harbor",
            model="provider/model",
            root=root,
            hashmarks_source=root,
            passthrough_env_keys=(),
        )

        def prepare(**kwargs):
            destination = kwargs["destination"]
            destination.mkdir(parents=True)
            (destination / "task.txt").write_text("frozen", encoding="utf-8")
            return destination

        patches = (
            mock.patch("benchmarks.harbor_commands.settings_from_config", return_value=settings),
            mock.patch("benchmarks.harbor_commands.observed_preflight", return_value={"ready": True}),
            mock.patch("benchmarks.harness.harbor_backend.prepare_task", side_effect=prepare),
        )
        return env, patches

    @staticmethod
    def _reward_trial(**kwargs):
        job_root = kwargs["run_root"] / "jobs" / kwargs["job_name"]
        job_root.mkdir(parents=True)
        reward = job_root / "reward.txt"
        reward.write_text("1\n", encoding="utf-8")
        return {
            "trial_id": kwargs["job_name"],
            **kwargs["row"],
            "model": kwargs["settings"].model,
            "status": "COMPLETE",
            "reward": 1.0,
            "reward_path": str(reward),
            "harbor_return_code": 0,
            "stderr_tail": "",
        }

    def _call(self, *args: str) -> tuple[int, dict | None]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            code = main(list(args))
        rendered = output.getvalue().strip()
        return code, json.loads(rendered) if rendered else None

    def test_run_report_and_resume_share_numbered_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            env, patches = self._environment(root)
            with patches[0], patches[1], patches[2], mock.patch(
                "benchmarks.harness.harbor_backend.execute_trial",
                side_effect=self._reward_trial,
            ) as execute:
                code, _ = self._call(
                    "run", "--new", "--matrix", "harbor-smoke",
                    "--env-file", str(env), "--root", str(root), "--no-json-results",
                )
                self.assertEqual(code, 0)
                self.assertEqual(execute.call_count, 6)
                code, report = self._call(
                    "report", "--matrix", "harbor-smoke", "--root", str(root),
                )
                self.assertEqual(code, 0)
                self.assertEqual(report["expected_trials"], 6)
                self.assertTrue(report["qualified"])
                self.assertEqual(
                    report["mechanism_attribution"]["summary"]["paired_observations"],
                    3,
                )
                code, mechanism = self._call(
                    "explain", "--matrix", "harbor-smoke", "--root", str(root),
                )
                self.assertEqual(code, 0)
                self.assertTrue(mechanism["campaign_qualified"])
                self.assertEqual(mechanism["summary"]["paired_observations"], 3)
                self.assertEqual(execute.call_count, 6)
                code, _ = self._call(
                    "run", "--resume", "--run-id", "000001",
                    "--matrix", "harbor-smoke", "--env-file", str(env),
                    "--root", str(root), "--no-json-results",
                )
                self.assertEqual(code, 0)
                self.assertEqual(execute.call_count, 6)
            self.assertTrue((root / "runs/000001/results/.campaign/authority.json").is_file())
            self.assertTrue((root / "runs/000001/reports/report.json").is_file())
            self.assertTrue((root / "runs/000001/reports/mechanism.json").is_file())

    def test_interrupted_launch_gets_new_job_name_on_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            env, patches = self._environment(root)
            jobs = []

            def interrupted_once(**kwargs):
                jobs.append(kwargs["job_name"])
                if len(jobs) == 1:
                    raise KeyboardInterrupt()
                return self._reward_trial(**kwargs)

            with patches[0], patches[1], patches[2], mock.patch(
                "benchmarks.harness.harbor_backend.execute_trial",
                side_effect=interrupted_once,
            ):
                with self.assertRaises(KeyboardInterrupt):
                    self._call(
                        "run", "--new", "--matrix", "harbor-smoke",
                        "--env-file", str(env), "--root", str(root),
                    )
                code, status = self._call(
                    "status", "--matrix", "harbor-smoke", "--root", str(root),
                )
                self.assertEqual(code, 0)
                self.assertEqual(status["interrupted_trials"], 1)
                code, _ = self._call(
                    "run", "--resume", "--run-id", "000001",
                    "--matrix", "harbor-smoke", "--env-file", str(env),
                    "--root", str(root), "--no-json-results",
                )
                self.assertEqual(code, 0)
                self.assertNotEqual(jobs[0], jobs[1])
                self.assertTrue(jobs[0].endswith("a000001"))
                self.assertTrue(jobs[1].endswith("a000002"))
                code, status = self._call(
                    "status", "--matrix", "harbor-smoke", "--root", str(root),
                )
                self.assertEqual(status["recovered_interruption_attempts"], 1)

    def test_completed_operational_failure_is_preserved_on_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            env, patches = self._environment(root)
            calls = []

            def one_missing_reward(**kwargs):
                calls.append(kwargs["job_name"])
                if len(calls) == 1:
                    return {
                        "trial_id": kwargs["job_name"],
                        **kwargs["row"],
                        "model": kwargs["settings"].model,
                        "status": "INCOMPLETE",
                        "reward": None,
                        "reward_path": None,
                        "harbor_return_code": 1,
                        "stderr_tail": "Harbor failed",
                    }
                return self._reward_trial(**kwargs)

            with patches[0], patches[1], patches[2], mock.patch(
                "benchmarks.harness.harbor_backend.execute_trial",
                side_effect=one_missing_reward,
            ):
                code, _ = self._call(
                    "run", "--new", "--matrix", "harbor-smoke",
                    "--env-file", str(env), "--root", str(root), "--no-json-results",
                )
                self.assertEqual(code, 2)
                self.assertEqual(len(calls), 6)
                code, report = self._call(
                    "report", "--matrix", "harbor-smoke", "--root", str(root),
                )
                self.assertEqual(code, 2)
                self.assertFalse(report["qualified"])
                self.assertEqual(report["incomplete"], 1)
                self.assertTrue(all(value is None for value in report["hashmarks_uplift"].values()))
                code, _ = self._call(
                    "run", "--resume", "--run-id", "000001",
                    "--matrix", "harbor-smoke", "--env-file", str(env),
                    "--root", str(root), "--no-json-results",
                )
                self.assertEqual(code, 2)
                self.assertEqual(len(calls), 6)

    def test_resume_rejects_changed_preflight_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            env, patches = self._environment(root)
            with patches[0], patches[2], mock.patch(
                "benchmarks.harbor_commands.observed_preflight",
                side_effect=({"ready": True}, {"ready": True, "harbor": "changed"}),
            ), mock.patch(
                "benchmarks.harness.harbor_backend.execute_trial",
                side_effect=self._reward_trial,
            ) as execute:
                self.assertEqual(self._call(
                    "run", "--new", "--matrix", "harbor-smoke",
                    "--env-file", str(env), "--root", str(root), "--no-json-results",
                )[0], 0)
                with self.assertRaisesRegex(SystemExit, "authority changed"):
                    self._call(
                        "run", "--resume", "--run-id", "000001",
                        "--matrix", "harbor-smoke", "--env-file", str(env),
                        "--root", str(root), "--no-json-results",
                    )
                self.assertEqual(execute.call_count, 6)

    def test_corrupt_reward_blocks_status_and_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            env, patches = self._environment(root)
            with patches[0], patches[1], patches[2], mock.patch(
                "benchmarks.harness.harbor_backend.execute_trial",
                side_effect=self._reward_trial,
            ):
                self.assertEqual(self._call(
                    "run", "--new", "--matrix", "harbor-smoke",
                    "--env-file", str(env), "--root", str(root), "--no-json-results",
                )[0], 0)
            receipt = next((root / "runs/000001/results").glob("*/reward.txt"))
            receipt.write_text("0\n", encoding="utf-8")
            report_path = root / "runs/000001/reports/report.json"
            score_path = root / "runs/000001/reports/score.json"
            self.assertTrue(report_path.is_file())
            self.assertTrue(score_path.is_file())
            code, status = self._call(
                "status", "--matrix", "harbor-smoke", "--root", str(root),
            )
            self.assertEqual(code, 2)
            self.assertEqual(len(status["corrupt_bundles"]), 1)
            self.assertFalse(report_path.exists())
            self.assertFalse(score_path.exists())
            code, report = self._call(
                "report", "--matrix", "harbor-smoke", "--root", str(root),
            )
            self.assertEqual(code, 2)
            self.assertFalse(report["qualified"])
            self.assertTrue(all(value is None for value in report["hashmarks_uplift"].values()))


if __name__ == "__main__":
    unittest.main()
