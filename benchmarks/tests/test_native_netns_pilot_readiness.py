"""E260: no fabricated pilot outcomes from incomplete netns execution receipts.

Only synthetic model-free fixtures. Cohort projection is mocked here because
its real native export and host HMAC checks have a separate regression ring.
"""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.harness.native_netns_pilot_readiness import evaluate_native_netns_pilot
from benchmarks.harness.opencode_native_trial import SCHEMA as TRIAL_SCHEMA
from benchmarks.tests.test_opencode_native_gateway import KEY, H, manifest


class NativeNetnsPilotAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.results = self.root / "results"
        self.results.mkdir()
        self.sources = self.root / "sources"
        self.sources.mkdir()
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.frozen = manifest()
        self._make_execution_receipts()
        self.cohort = {
            "native_session_cohort_observationally_consistent": True,
            "verified_native_trial_exports": 2,
        }

    def tearDown(self):
        self.tmp.cleanup()

    def _make_execution_receipts(self):
        for cell in self.frozen["assignments"]:
            folder = self.results / cell["trial_id"]
            folder.mkdir()
            report = {
                "schema": TRIAL_SCHEMA,
                "trial_id": cell["trial_id"],
                "manifest_sha256": self.frozen["manifest_sha256"],
                "native_exit_code": 0,
                "native_trial_evidence_qualified": True,
                "host_receipt_finalized": True,
                "native_gateway_route_completed": True,
                "linux_network_namespace_requested": True,
                "host_network_egress_intentionally_disabled": True,
                "kernel_distinct_netns_relay_observed": True,
                "native_sandbox_binary_sha256": H("approved-bwrap"),
                "frozen_hashmarks_executable_sha256": H("approved-hashmarks"),
                "observed_provider_response_relays": 1,
                "native_process_origin_proven": False,
                "causal_improvement_proven": False,
                "gateway": {
                    "kernel_netns_peer_check_required": True,
                    "distinct_netns_peer_connections": 1,
                },
                "native_session_binding": {
                    "native_session_to_gateway_packet_bound": True,
                    "signed_host_input_and_transport_verified": True,
                },
            }
            (folder / "trial-execution.json").write_text(json.dumps(report))

    def assess(self):
        with patch(
            "benchmarks.harness.native_netns_pilot_readiness.audit_native_session_cohort",
            return_value=self.cohort,
        ) as cohort:
            result = evaluate_native_netns_pilot(
                self.frozen, results_root=self.results,
                sources_root=self.sources, workspace=self.workspace,
                host_key=KEY, host_identity="privileged-host",
                approved_endpoint_sha256=H("endpoint"),
                expected_bwrap_sha256=H("approved-bwrap"),
                expected_hashmarks_sha256=H("approved-hashmarks"),
            )
        self.assertEqual(cohort.call_count, 1)
        return result

    def test_complete_observations_are_not_model_effect_or_review_proof(self):
        result = self.assess()
        self.assertTrue(result["paired_pilot_observations_ready_for_independent_grading"])
        self.assertEqual(result["verified_local_isolation_receipts"], 2)
        for flag in (
            "exclusive_network_egress_independently_audited",
            "native_executable_origin_independently_proven",
            "independent_oracle_grading_completed",
            "pre_work_timestamp_independently_proven",
            "randomized_causal_hashmarks_uplift_proven",
        ):
            self.assertFalse(result[flag])

    def test_wrong_binary_pin_or_untrusted_isolation_claim_rejects(self):
        trial = self.frozen["assignments"][0]["trial_id"]
        path = self.results / trial / "trial-execution.json"
        base = json.loads(path.read_text())
        for key, changed in (
            ("native_sandbox_binary_sha256", H("wrong")),
            ("frozen_hashmarks_executable_sha256", H("wrong")),
            ("kernel_distinct_netns_relay_observed", False),
            ("native_gateway_route_completed", False),
            ("native_process_origin_proven", True),
            ("observed_provider_response_relays", 2),
        ):
            with self.subTest(key=key):
                tampered = copy.deepcopy(base)
                tampered[key] = changed
                path.write_text(json.dumps(tampered))
                report = self.assess()
                self.assertFalse(report["paired_pilot_observations_ready_for_independent_grading"])
                self.assertIn("inconsistent-or-self-upgraded-native-isolation-receipt",
                              report["blockers"])
        path.write_text(json.dumps(base))

    def test_missing_pair_or_unverified_native_cohort_rejects(self):
        trial = self.frozen["assignments"][0]["trial_id"]
        (self.results / trial / "trial-execution.json").unlink()
        result = self.assess()
        self.assertFalse(result["paired_pilot_observations_ready_for_independent_grading"])
        self.assertEqual(result["verified_local_isolation_receipts"], 1)
        self.cohort["native_session_cohort_observationally_consistent"] = False
        self.assertIn("unqualified-native-session-cohort", self.assess()["blockers"])


if __name__ == "__main__":
    unittest.main()
