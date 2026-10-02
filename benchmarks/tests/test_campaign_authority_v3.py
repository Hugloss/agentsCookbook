from __future__ import annotations

import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from benchmarks.harness.campaign_authority import (
    CampaignAuthorityError,
    admit_campaign,
    audit_campaign,
    claim_launch,
    launch_state,
    read_campaign,
)
from benchmarks.harness.identity import definition_id, execution_evidence_id
from benchmarks.harness.suite import SuiteDefinition


def _suite() -> SuiteDefinition:
    experiment = {
        "id": "campaign-test",
        "version": 1,
        "suite": "test",
        "tasks": ["task-a", "task-b"],
        "conditions": [
            {
                "id": "bare",
                "agent": "agent",
                "subject": "none",
                "trials": 1,
                "replicate_ids": [9],
            },
            {
                "id": "assisted",
                "agent": "agent",
                "subject": "tool",
                "trials": 1,
                "replicate_ids": [9],
            },
        ],
        "scoring": {"id": "score", "version": 1, "metrics": ["task_success"]},
    }
    tasks = {
        name: {"id": name, "prompt": name, "budgets": {"timeout_seconds": 1}}
        for name in experiment["tasks"]
    }
    subjects = {name: {"id": name} for name in ("none", "tool")}
    agents = {"agent": {"id": "agent"}}
    return SuiteDefinition(Path("."), experiment, tasks, subjects, agents)


def _fake_condition_authority(admission):
    return {
        "agent": {
            "declared": {"id": admission.condition["agent"]},
            "model": "same-model",
            "native_config_sha256": admission.task["id"],
        },
        "subject": {
            "declared": {"id": admission.condition["subject"]},
            "observed": None,
            "source_identity": None,
        },
    }


class CampaignAuthorityTests(unittest.TestCase):
    def test_campaign_checks_every_task_and_subject_before_freezing(self) -> None:
        suite = _suite()
        rows = suite.trial_definitions()
        seen = []

        @contextmanager
        def fake_admission(**kwargs):
            task_id = kwargs["task_id"]
            condition_id = kwargs["condition_id"]
            seen.append((task_id, condition_id))
            condition = next(
                value
                for value in suite.experiment["conditions"]
                if value["id"] == condition_id
            )
            yield SimpleNamespace(
                task=suite.tasks[task_id],
                condition=condition,
                admitted_state={"source": "same"},
                mutation_authority=None,
                initial_outcome=lambda: (None, None),
                cleanup_subject=lambda: None,
                definition_id=next(
                    row["definition_id"]
                    for row in rows
                    if row["task_id"] == task_id and row["condition_id"] == condition_id
                ),
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            options = dict(
                suite=suite,
                rows=rows,
                results_root=root / "results",
                harness_root=root,
                cache_root=root / "cache",
                work_root=root / "work",
            )
            with (
                mock.patch(
                    "benchmarks.harness.campaign_authority.admit_trial", fake_admission
                ),
                mock.patch(
                    "benchmarks.harness.campaign_authority.condition_authority",
                    side_effect=_fake_condition_authority,
                ),
            ):
                progress = []
                audited = audit_campaign(
                    **{k: v for k, v in options.items() if k != "results_root"},
                    on_progress=progress.append,
                )
                self.assertEqual(len(seen), 4)
                condition_progress = [
                    row for row in progress if row["stage"] == "condition-authority"
                ]
                self.assertEqual(len(condition_progress), 4)
                self.assertEqual(
                    [row["index"] for row in condition_progress],
                    [1, 2, 3, 4],
                )
                self.assertTrue(
                    all(row["total"] == 4 for row in condition_progress)
                )
                self.assertEqual(
                    progress[-1],
                    {
                        "stage": "campaign-authority",
                        "status": "verified",
                        "total": 4,
                    },
                )
                self.assertFalse((root / "results/.campaign").exists())
                campaign = admit_campaign(**options)
                self.assertEqual(len(seen), 8)
                self.assertEqual(audited, campaign)
                self.assertEqual(
                    campaign["contract"], "benchmark-campaign-authority.v2"
                )
                self.assertNotEqual(
                    campaign["task_conditions"]["task-a"]["bare"]["agent"][
                        "native_config_sha256"
                    ],
                    campaign["task_conditions"]["task-b"]["bare"]["agent"][
                        "native_config_sha256"
                    ],
                )
                self.assertEqual(read_campaign(root / "results"), campaign)
                self.assertEqual(admit_campaign(**options), campaign)
                with self.assertRaisesRegex(CampaignAuthorityError, "selection"):
                    admit_campaign(**{**options, "rows": rows[:1]})
                claim_launch(
                    results_root=root / "results",
                    campaign=campaign,
                    definition_id=rows[0]["definition_id"],
                    trial_id="a" * 64,
                )
                self.assertEqual(
                    launch_state(
                        results_root=root / "results",
                        campaign=campaign,
                        definition_id=rows[0]["definition_id"],
                        trial_id="a" * 64,
                    ),
                    "INTERRUPTED",
                )
                with self.assertRaisesRegex(CampaignAuthorityError, "already claimed"):
                    claim_launch(
                        results_root=root / "results",
                        campaign=campaign,
                        definition_id=rows[0]["definition_id"],
                        trial_id="a" * 64,
                    )

            def drifted(admission):
                value = _fake_condition_authority(admission)
                if admission.task["id"] == "task-b":
                    value["agent"]["model"] = "different-model"
                return value

            with (
                mock.patch(
                    "benchmarks.harness.campaign_authority.admit_trial", fake_admission
                ),
                mock.patch(
                    "benchmarks.harness.campaign_authority.condition_authority",
                    side_effect=drifted,
                ),
            ):
                with self.assertRaisesRegex(CampaignAuthorityError, "runtime or model"):
                    admit_campaign(**options)

    def test_replicate_definition_identity_does_not_reinterpret_legacy_seed(
        self,
    ) -> None:
        suite = _suite()
        condition = suite.expanded_condition(suite.experiment["conditions"][0])
        common = dict(
            experiment=suite.experiment,
            task=suite.tasks["task-a"],
            condition=condition,
            trial=0,
        )
        self.assertNotEqual(
            definition_id(**common, seed=9), definition_id(**common, replicate_id=9)
        )

    def test_admitted_workspace_is_bound_into_v3_evidence(self) -> None:
        arguments = dict(
            task={"id": "task-a", "prompt": "find it"},
            condition={"id": "bare"},
            trial=0,
            replicate_id=9,
            campaign_id="c" * 64,
            subject_identity={},
            agent_identity={},
            harness_identity={},
            environment_identity={},
            mutation_identity=None,
            agent_answer="answer",
            workspace_root="/tmp/work",
            location_observation=None,
            agent_trace_sha256="d" * 64,
        )
        self.assertNotEqual(
            execution_evidence_id(**arguments, admitted_state_sha256="a" * 64),
            execution_evidence_id(**arguments, admitted_state_sha256="b" * 64),
        )
        with self.assertRaisesRegex(ValueError, "admitted_state"):
            execution_evidence_id(**arguments)

    def test_late_preflight_failure_publishes_no_campaign_or_launch(self) -> None:
        suite = _suite()
        rows = suite.trial_definitions()

        @contextmanager
        def fake_admission(**kwargs):
            failed = (
                kwargs["task_id"] == "task-b" and kwargs["condition_id"] == "assisted"
            )
            condition = next(
                value
                for value in suite.experiment["conditions"]
                if value["id"] == kwargs["condition_id"]
            )
            yield SimpleNamespace(
                task=suite.tasks[kwargs["task_id"]],
                condition=condition,
                admitted_state={"source": "same"},
                mutation_authority=None,
                initial_outcome=lambda: (
                    ("INCOMPLETE", "unavailable") if failed else (None, None)
                ),
                cleanup_subject=lambda: None,
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                mock.patch(
                    "benchmarks.harness.campaign_authority.admit_trial", fake_admission
                ),
                mock.patch(
                    "benchmarks.harness.campaign_authority.condition_authority",
                    side_effect=_fake_condition_authority,
                ),
            ):
                with self.assertRaisesRegex(
                    CampaignAuthorityError, "cannot enter campaign"
                ):
                    admit_campaign(
                        suite=suite,
                        rows=rows,
                        results_root=root / "results",
                        harness_root=root,
                        cache_root=root / "cache",
                        work_root=root / "work",
                    )
            self.assertFalse((root / "results/.campaign/authority.json").exists())
            self.assertFalse((root / "results/.campaign/claims").exists())

    def test_model_free_audit_rejects_stale_results_before_admission(self) -> None:
        suite = _suite()
        rows = suite.trial_definitions()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "results" / "old-receipt").mkdir(parents=True)
            with mock.patch(
                "benchmarks.harness.campaign_authority.admit_trial",
                side_effect=AssertionError("stale results must fail first"),
            ):
                with self.assertRaisesRegex(
                    CampaignAuthorityError, "no campaign authority"
                ):
                    audit_campaign(
                        suite=suite,
                        rows=rows,
                        results_root=root / "results",
                        harness_root=root,
                        cache_root=root / "cache",
                        work_root=root / "work",
                    )


if __name__ == "__main__":
    unittest.main()
