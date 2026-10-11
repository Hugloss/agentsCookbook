"""E269-E272: synthetic native paired study and tool-call ancestry attacks."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.harness.host_input_attestation import canonical
from benchmarks.harness.native_chat_pair_admission import (
    admit_native_chat_pair, verify_native_chat_pair_claim,
)
from benchmarks.harness.native_chat_request_integrity import (
    require_assistant_tool_ancestry,
)
from benchmarks.harness.opencode_native_gateway import NativeOpenCodeGateway
from benchmarks.tests.test_opencode_native_gateway import (
    H, KEY, UPSTREAM, manifest, source,
)


def exact_request(content: str):
    return {
        "model": "gpt-fixture",
        "messages": [
            {"role": "user", "content": "find source owner"},
            {"role": "assistant", "tool_calls": [{
                "id": "call-1", "type": "function",
                "function": {"name": "hashmarks_task_evidence",
                             "arguments": "{\\"scope\\":\\"repo\\"}"},
            }]},
            {"role": "tool", "tool_call_id": "call-1", "content": content},
        ],
    }


class FrozenNativePairTests(unittest.TestCase):
    def setUp(self):
        self.plan = manifest()
        self.variant = next(c for c in self.plan["assignments"] if c["arm"] == "variant")
        self.control = next(c for c in self.plan["assignments"] if c["arm"] == "control")

    def test_structured_control_prevents_paired_native_admission(self):
        with self.assertRaisesRegex(ValueError, "paired-transport-not-admitted"):
            admit_native_chat_pair(
                self.plan, trial_id=self.variant["trial_id"],
                current=source(), replaced=None,
            )
        with self.assertRaisesRegex(ValueError, "selected-native-chat-arm"):
            admit_native_chat_pair(
                self.plan, trial_id=self.control["trial_id"],
                current=source(), replaced=None,
                allow_unpaired_diagnostic=True,
            )

    def test_explicit_single_arm_diagnostic_is_never_a_paired_trial(self):
        receipt = admit_native_chat_pair(
            self.plan, trial_id=self.variant["trial_id"],
            current=source(), replaced=None,
            allow_unpaired_diagnostic=True,
        )
        self.assertTrue(receipt["diagnostic_only"])
        self.assertFalse(receipt["paired_transport_compatible"])
        self.assertTrue(verify_native_chat_pair_claim(
            receipt, trial_id=self.variant["trial_id"],
            manifest_sha256=self.plan["manifest_sha256"],
        ))
        self.assertEqual(receipt["native_model_runs_performed_by_admission"], 0)
        self.assertEqual(receipt["representations"]["control"],
                         "unsupported-nested-json-tool-content")
        for field, value in (
            ("diagnostic_only", False),
            ("paired_transport_compatible", True),
            ("model_attention_proven", True),
            ("native_model_runs_performed_by_admission", True),
            ("pair_id", ""),
            ("trial_id", self.control["trial_id"]),
        ):
            with self.subTest(field=field):
                tampered = copy.deepcopy(receipt)
                tampered[field] = value
                self.assertFalse(verify_native_chat_pair_claim(
                    tampered, trial_id=self.variant["trial_id"],
                    manifest_sha256=self.plan["manifest_sha256"],
                ))

    def test_frozen_pair_must_have_exact_identity_and_completeness(self):
        bad = copy.deepcopy(self.plan)
        bad["assignments"] = [
            a for a in bad["assignments"] if a["arm"] != "control"
        ]
        with self.assertRaises(ValueError):
            admit_native_chat_pair(
                bad, trial_id=self.variant["trial_id"],
                current=source(), replaced=None,
                allow_unpaired_diagnostic=True,
            )


class NativeAssistantLineageAttacks(unittest.TestCase):
    def test_exact_assistant_to_tool_link(self):
        self.assertEqual(require_assistant_tool_ancestry(
            exact_request("{}"), call_id="call-1",
        ), "hashmarks_task_evidence")

    def test_orphan_replay_duplicate_foreign_or_parallel_tool_call_fails(self):
        good = exact_request("{}")
        bad = []
        orphan = copy.deepcopy(good)
        orphan["messages"].pop(1)
        bad.append(orphan)
        changed = copy.deepcopy(good)
        changed["messages"][-1]["tool_call_id"] = "foreign"
        bad.append(changed)
        changed = copy.deepcopy(good)
        changed["messages"][-2]["tool_calls"][0]["id"] = "foreign"
        bad.append(changed)
        changed = copy.deepcopy(good)
        changed["messages"][-2]["tool_calls"][0]["function"]["name"] = "bash"
        bad.append(changed)
        changed = copy.deepcopy(good)
        changed["messages"][-2]["tool_calls"].append(
            copy.deepcopy(changed["messages"][-2]["tool_calls"][0])
        )
        bad.append(changed)
        changed = copy.deepcopy(good)
        changed["messages"].insert(-1, {
            "role": "tool", "tool_call_id": "foreign", "content": "{}",
        })
        bad.append(changed)
        changed = copy.deepcopy(good)
        changed["messages"][-1] = None
        bad.append(changed)
        changed = copy.deepcopy(good)
        changed["messages"][-1]["role"] = "user"
        bad.append(changed)
        for case in bad:
            with self.subTest(case=case), self.assertRaises(ValueError):
                require_assistant_tool_ancestry(case, call_id="call-1")

    def test_gateway_rejects_orphan_before_upstream_submission(self):
        with tempfile.TemporaryDirectory() as td:
            key = Path(td) / "host.key"
            key.write_bytes(KEY)
            key.chmod(0o600)
            plan = manifest()
            trial = next(c for c in plan["assignments"] if c["arm"] == "variant")
            gw = NativeOpenCodeGateway(
                plan, trial_id=trial["trial_id"], host_key_file=key,
                host_identity="host", current=source(), replaced=None,
                gateway_token="approved-local-gateway-token-value-1234",
                upstream=UPSTREAM, approved_origin="https://api.example.invalid",
                upstream_api_key="host-only-secret", catalog_sha256=H("catalog"),
                oracle_sha256=H("oracle"), workspace_sha256=H("workspace"),
                enforce_chat_tool_wire_contract=True,
            )
            chosen = gw.selected["selected_content"]
            no_assistant = exact_request(chosen)
            no_assistant["messages"].pop(1)
            accepted = exact_request(chosen)
            with patch(
                "benchmarks.harness.opencode_native_gateway.dispatch_verified_chat_response",
                return_value=b'{"choices":[{"message":{"role":"assistant","content":"owner"}}]}',
            ) as upstream:
                with self.assertRaisesRegex(ValueError, "assistant-tool-call-absent"):
                    gw._handle_request(canonical(no_assistant),
                                       authorization="Bearer " + gw.token)
                upstream.assert_not_called()
                self.assertEqual(gw.result()["post_evidence_submissions"], 0)
                self.assertTrue(gw._handle_request(canonical(accepted),
                          authorization="Bearer " + gw.token))
                self.assertEqual(upstream.call_count, 1)


if __name__ == "__main__":
    unittest.main()
