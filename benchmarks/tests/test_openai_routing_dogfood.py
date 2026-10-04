from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from benchmarks.openai_responses_routing_probe import OpenAIRoutingProbeError
from benchmarks.openai_routing_dogfood import (
    OpenAIRoutingDogfoodError,
    OpenAIRoutingSettings,
    allocate_run_directory,
    campaign_exit_code,
    list_dogfood_runs,
    load_manifest,
    routing_run_root,
    run_campaign,
    run_saved_campaign,
    select_dogfood_run,
)


def _workspace(root: Path) -> Path:
    root.mkdir()
    for path in (
        "benchmarks/tool_routing.py",
        "benchmarks/tool_routing_trace.py",
    ):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# fixture\n", encoding="utf-8")
    return root


def _manifest(path: Path, *, forbidden: bool = False) -> Path:
    prompt = (
        "Use Hashmarks task_evidence to locate the owner."
        if forbidden
        else "Locate the implementation that maps host-specific repository tool names "
        "into semantic routing classes. Report the owning path."
    )
    path.write_text(
        json.dumps(
            {
                "schema": "agents-cookbook-openai-routing-dogfood-manifest.v1",
                "name": "fixture",
                "tasks": [
                    {
                        "id": "routing-owner",
                        "prompt": prompt,
                        "expected_paths": ["benchmarks/tool_routing.py"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _receipt(outcome: str, final_text: str) -> dict[str, object]:
    return {
        "catalog": {"schema": "catalog"},
        "trace": {
            "schema": "trace",
            "calls": [
                {
                    "tool": (
                        "mcp__hashmarks__task_evidence"
                        if outcome == "PASS"
                        else "grep"
                    )
                }
            ],
        },
        "score": {"outcome": outcome},
        "openai": {"usage": [{"total_tokens": 123}]},
        "final_text": final_text,
    }


class OpenAIRoutingDogfoodTests(unittest.TestCase):
    def test_easy_settings_require_only_two_nonsecret_choices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tunnel_client = root / "tunnel-client"
            tunnel_client.write_text("#!/bin/sh\n", encoding="utf-8")
            tunnel_client.chmod(0o755)
            env_file = root / ".env"
            env_file.write_text(
                "\n".join(
                    [
                        "OPENAI_ROUTING_TUNNEL_ID=tunnel_" + "a" * 32,
                        "OPENAI_ROUTING_MODEL=gpt-test",
                        f"OPENAI_ROUTING_TUNNEL_CLIENT={tunnel_client}",
                        "OPENAI_API_KEY=must-not-be-read-from-file",
                        "CONTROL_PLANE_API_KEY=must-not-be-read-from-file",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with mock.patch("pathlib.Path.cwd", return_value=root):
                settings = OpenAIRoutingSettings.load(
                    env_file,
                    host={"PATH": ""},
                )

            self.assertEqual(settings.tunnel_id, "tunnel_" + "a" * 32)
            self.assertEqual(settings.model, "gpt-test")
            self.assertEqual(settings.repeats, 1)
            self.assertEqual(settings.tunnel_client, tunnel_client.resolve())
            self.assertTrue(
                str(settings.handoff).endswith(
                    "Hashmarks/dist/chatgpt-secure-mcp-tunnel-handoff.json"
                )
            )

    def test_empty_optional_env_values_use_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tunnel_client = root / "tunnel-client"
            tunnel_client.write_text("#!/bin/sh\n", encoding="utf-8")
            tunnel_client.chmod(0o755)
            env_file = root / ".env"
            env_file.write_text(
                "\n".join(
                    [
                        "OPENAI_ROUTING_TUNNEL_ID=tunnel_" + "b" * 32,
                        "OPENAI_ROUTING_MODEL=gpt-test",
                        f"OPENAI_ROUTING_TUNNEL_CLIENT={tunnel_client}",
                        "OPENAI_ROUTING_WORKSPACE=",
                        "OPENAI_ROUTING_HANDOFF=",
                        "OPENAI_ROUTING_MANIFEST=",
                        "OPENAI_ROUTING_REPEATS=",
                        "OPENAI_ROUTING_RUN_ROOT=",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            settings = OpenAIRoutingSettings.load(env_file, host={"PATH": ""})

            self.assertEqual(settings.repeats, 1)
            self.assertTrue(
                str(settings.manifest).endswith(
                    "benchmarks/dogfood/openai-routing-v1.json"
                )
            )
            self.assertTrue(
                str(settings.run_root).endswith(
                    ".benchmark-runs/openai-routing"
                )
            )

    def test_numbered_runs_allocate_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_id, first = allocate_run_directory(root)
            second_id, second = allocate_run_directory(root)

            self.assertEqual(first_id, "000001")
            self.assertEqual(second_id, "000002")
            self.assertTrue(first.is_dir())
            self.assertTrue(second.is_dir())

    def test_run_inspection_needs_only_run_root_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "custom-runs"
            env_file = root / ".env"
            env_file.write_text(
                f"OPENAI_ROUTING_RUN_ROOT={run_root}\n",
                encoding="utf-8",
            )
            run_id, run_dir = allocate_run_directory(run_root)
            (run_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "status": "COMPLETE",
                        "aggregate": {
                            "hashmarks_first_rate": 1.0,
                            "outcomes": {"PASS": 5},
                        },
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(routing_run_root(env_file), run_root.resolve())
            rows = list_dogfood_runs(run_root)
            self.assertEqual(rows[0]["run_id"], run_id)
            self.assertEqual(rows[0]["status"], "COMPLETE")
            self.assertEqual(
                select_dogfood_run(run_root)["run_id"],
                run_id,
            )

    def test_failed_easy_start_is_visible_and_next_run_advances(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings = OpenAIRoutingSettings(
                workspace=root,
                handoff=root / "handoff.json",
                tunnel_client=root / "tunnel-client",
                tunnel_id="tunnel_" + "c" * 32,
                model="gpt-test",
                manifest=root / "manifest.json",
                repeats=1,
                run_root=root / "runs-root",
            )

            with mock.patch(
                "benchmarks.openai_routing_dogfood.run_campaign",
                side_effect=OpenAIRoutingDogfoodError("preflight rejected"),
            ):
                with self.assertRaisesRegex(
                    OpenAIRoutingDogfoodError,
                    "preflight rejected",
                ):
                    run_saved_campaign(
                        settings=settings,
                        openai_api_key="openai-secret",
                        control_plane_api_key="control-secret",
                    )

            rows = list_dogfood_runs(settings.run_root)
            self.assertEqual(rows[0]["run_id"], "000001")
            self.assertEqual(rows[0]["status"], "PRECHECK_FAILED")
            self.assertTrue(
                (
                    settings.run_root
                    / "runs"
                    / "000001"
                    / "start-error.json"
                ).is_file()
            )
            second_id, _ = allocate_run_directory(settings.run_root)
            self.assertEqual(second_id, "000002")

    def test_manifest_rejects_tool_directing_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = _workspace(root / "repo")
            manifest = _manifest(root / "manifest.json", forbidden=True)
            with self.assertRaisesRegex(
                OpenAIRoutingDogfoodError,
                "names routing/tool authority",
            ):
                load_manifest(manifest, workspace=workspace)

    def test_campaign_aggregates_routing_and_answer_sanity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = _workspace(root / "repo")
            manifest = _manifest(root / "manifest.json")
            output = root / "run"
            receipts = [
                _receipt("PASS", "Owned by benchmarks/tool_routing.py"),
                _receipt("FAIL", "Owned by benchmarks/tool_routing.py"),
            ]

            with mock.patch(
                "benchmarks.openai_routing_dogfood.preflight_probe",
                return_value={"schema": "preflight", "status": "READY"},
            ):
                summary = run_campaign(
                    manifest_path=manifest,
                    workspace=workspace,
                    handoff_path=root / "handoff.json",
                    tunnel_client=root / "tunnel-client",
                    tunnel_id="tunnel_" + "1" * 32,
                    model="gpt-test",
                    repeats=2,
                    output_dir=output,
                    openai_api_key="openai-secret",
                    control_plane_api_key="control-secret",
                    probe_runner=mock.Mock(side_effect=receipts),
                )

            self.assertEqual(summary["status"], "COMPLETE")
            self.assertEqual(
                summary["aggregate"]["outcomes"],
                {"FAIL": 1, "PASS": 1},
            )
            self.assertEqual(summary["aggregate"]["hashmarks_first_rate"], 0.5)
            self.assertEqual(summary["aggregate"]["answer_path_matches"], 2)
            self.assertEqual(summary["aggregate"]["total_tokens"], 246)
            self.assertEqual(campaign_exit_code(summary), 1)
            self.assertTrue((output / "preflight.json").is_file())
            self.assertTrue(
                (output / "trials" / "routing-owner-r01" / "receipt.json").is_file()
            )
            self.assertTrue(
                (output / "trials" / "routing-owner-r02" / "receipt.json").is_file()
            )

    def test_campaign_aborts_after_first_infrastructure_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = _workspace(root / "repo")
            manifest = _manifest(root / "manifest.json")
            output = root / "run"
            runner = mock.Mock(
                side_effect=OpenAIRoutingProbeError("tunnel unavailable")
            )

            with mock.patch(
                "benchmarks.openai_routing_dogfood.preflight_probe",
                return_value={"schema": "preflight", "status": "READY"},
            ):
                summary = run_campaign(
                    manifest_path=manifest,
                    workspace=workspace,
                    handoff_path=root / "handoff.json",
                    tunnel_client=root / "tunnel-client",
                    tunnel_id="tunnel_" + "2" * 32,
                    model="gpt-test",
                    repeats=5,
                    output_dir=output,
                    openai_api_key="openai-secret",
                    control_plane_api_key="control-secret",
                    probe_runner=runner,
                )

            self.assertEqual(runner.call_count, 1)
            self.assertEqual(summary["status"], "INCOMPLETE")
            self.assertEqual(
                summary["aggregate"]["outcomes"],
                {"INCOMPLETE": 1},
            )
            self.assertEqual(campaign_exit_code(summary), 3)
            self.assertTrue(
                (output / "trials" / "routing-owner-r01" / "error.json").is_file()
            )
            self.assertFalse(
                (output / "trials" / "routing-owner-r02").exists()
            )

    def test_campaign_refuses_existing_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = _workspace(root / "repo")
            manifest = _manifest(root / "manifest.json")
            output = root / "run"
            output.mkdir()

            with self.assertRaisesRegex(
                OpenAIRoutingDogfoodError,
                "already exists",
            ):
                run_campaign(
                    manifest_path=manifest,
                    workspace=workspace,
                    handoff_path=root / "handoff.json",
                    tunnel_client=root / "tunnel-client",
                    tunnel_id="tunnel_" + "3" * 32,
                    model="gpt-test",
                    repeats=1,
                    output_dir=output,
                    openai_api_key="openai-secret",
                    control_plane_api_key="control-secret",
                )


if __name__ == "__main__":
    unittest.main()
