from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from benchmarks.openai_responses_routing_probe import OpenAIRoutingProbeError
from benchmarks.openai_routing_dogfood import (
    OpenAIRoutingDogfoodError,
    campaign_exit_code,
    load_manifest,
    run_campaign,
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
