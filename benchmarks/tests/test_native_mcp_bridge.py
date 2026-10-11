"""E273–E276 native MCP bridge attack ring and executable subprocess proof.

The local stdio end-to-end ring uses an executable deterministic Hashmarks
fixture, NOT an actual Hashmarks release or a real OpenCode model/provider.
The actual bridge executable subprocess and JSON-RPC bytes are exercised.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from benchmarks.harness.host_input_attestation import canonical
from benchmarks.harness.native_mcp_bridge_contract import (
    BridgeState, freeze_bridge_contract, validate_bridge_contract,
    write_bridge_contract,
)
from benchmarks.harness.native_mcp_stdio_bridge import run_stdio, sha_file
from benchmarks.harness.native_bwrap_execution import build_isolated_argv
from benchmarks.harness.opencode_native_gateway import gateway_config
from benchmarks.harness.trusted_treatments import select_treatment
from benchmarks.tests.test_opencode_native_gateway import manifest, source


def selection():
    frozen = manifest()
    cell = next(row for row in frozen["assignments"] if row["arm"] == "variant")
    return select_treatment(
        frozen, trial_id=cell["trial_id"], harness=cell["harness"],
        task=cell["task"], replicate=cell["replicate"],
        arm=cell["arm"], current=source(),
    )


def call_frame(*, identity=3, name="task_evidence"):
    return canonical({
        "jsonrpc": "2.0", "id": identity, "method": "tools/call",
        "params": {"name": name, "arguments": {"path": "src/owner.py"}},
    })


def result_frame(identity=3, *, packet=None, alternate=None):
    packet = source()["content"] if packet is None else packet
    result = {"content": [{"type": "text", "text": json.dumps(packet)}]}
    if alternate is not None:
        result["structuredContent"] = alternate
    return canonical({"jsonrpc": "2.0", "id": identity, "result": result})


class NativeMcpBridgeContractAttacks(unittest.TestCase):
    def setUp(self):
        self.chosen = selection()
        self.digest = "a" * 64
        self.contract = freeze_bridge_contract(
            self.chosen, original_packet=source()["content"],
            hashmarks_sha256=self.digest,
        )

    def test_frozen_identity_and_semantics_roundtrip(self):
        self.assertEqual(validate_bridge_contract(
            self.contract, hashmarks_sha256=self.digest,
        ), self.contract)
        self.assertEqual(self.contract["selected_text"],
                         self.chosen["selected_content"])
        self.assertEqual(self.contract["original_packet"], source()["content"])
        for name, value in (
            ("selected_text", "{}"),
            ("original_packet", {"owner": "different.py"}),
            ("contract_sha256", "0" * 64),
            ("manifest_sha256", "changed"),
        ):
            broken = {**self.contract, name: value}
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_bridge_contract(broken, hashmarks_sha256=self.digest)
        with self.assertRaises(ValueError):
            freeze_bridge_contract(
                {**self.chosen, "selected_content": json.loads(
                    self.chosen["selected_content"],
                )}, original_packet=source()["content"],
                hashmarks_sha256=self.digest,
            )

    def test_actual_original_required_before_presenting_selected_text(self):
        state = BridgeState(self.contract)
        first = call_frame()
        self.assertEqual(state.receive_request(first), first)
        actual = result_frame()
        transformed = state.receive_response(actual)
        decoded = json.loads(transformed)
        self.assertEqual(decoded["result"], {
            "content": [{
                "type": "text", "text": self.chosen["selected_content"],
            }],
        })
        self.assertEqual(state.subject_calls, 1)
        self.assertEqual(state.subject_responses, 1)
        with self.assertRaisesRegex(ValueError, "extra-subject"):
            state.receive_request(call_frame(identity=4))

    def test_subject_response_replay_and_boolean_id_alias_are_rejected(self):
        state = BridgeState(self.contract)
        state.receive_request(call_frame(identity=1))
        with self.assertRaisesRegex(ValueError, "id-type-confusion"):
            state.receive_response(canonical({
                "jsonrpc": "2.0", "id": True,
                "result": {"content": [{
                    "type": "text", "text": json.dumps(source()["content"]),
                }]},
            }))
        self.assertEqual(state.subject_responses, 0)
        original = result_frame(identity=1)
        state.receive_response(original)
        with self.assertRaisesRegex(ValueError, "replayed-subject-response"):
            state.receive_response(original)
        self.assertEqual(state.subject_responses, 1)

    def test_native_tool_errors_wrong_packet_parallel_or_forged_sources_block(self):
        bads = [
            (result_frame(packet={"owner": "wrong"}), "packet-drift"),
            (result_frame(alternate={"owner": "wrong"}), "structured-content-drift"),
            (canonical({"jsonrpc": "2.0", "id": 3, "error": {"code": -1}}), "failed"),
            (canonical({"jsonrpc": "2.0", "id": 3,
                        "result": {"content": []}}), "ambiguous"),
            (canonical({"jsonrpc": "2.0", "id": 3,
                        "result": {"content": [
                            {"type": "text", "text": "{}"},
                            {"type": "text", "text": "{}"},
                        ]}}), "ambiguous"),
        ]
        for raw, message in bads:
            with self.subTest(message=message):
                state = BridgeState(self.contract)
                state.receive_request(call_frame())
                with self.assertRaisesRegex(ValueError, message):
                    state.receive_response(raw)
                self.assertEqual(state.subject_responses, 0)
        for malicious in (
            call_frame(name="other-tool"),
            canonical({"jsonrpc":"2.0","id":True,"method":"tools/call",
                       "params":{"name":"find","arguments":{}}}),
        ):
            with self.assertRaises(ValueError):
                BridgeState(self.contract).receive_request(malicious)

    def test_create_only_contract_and_guest_mcp_binding(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            work = root / "workspace"
            work.mkdir()
            run = root / "run"
            run.mkdir()
            hashmarks = root / "hashmarks"
            hashmarks.write_text("#!/bin/sh\nexit 0\n")
            hashmarks.chmod(0o700)
            python = Path("/usr/bin/python3")
            opencode = root / "opencode"
            opencode.write_text("#!/bin/sh\\nexit 0\\n")
            opencode.chmod(0o700)
            for name in ("home", "config", "cache", "data", "state", "gateway"):
                (run / name).mkdir()
            (run / "opencode.json").write_text("{}")
            write_bridge_contract(run / "native-mcp-contract.json", self.contract)
            with self.assertRaisesRegex(ValueError, "create-only"):
                write_bridge_contract(run / "native-mcp-contract.json", self.contract)
            config = gateway_config(
                port=42424, model_id="gpt-fixture",
                hashmarks_executable=hashmarks, workspace=work,
                bridge_python=python, bridge_hashmarks_sha256=self.digest,
            )
            self.assertEqual(config["mcp"]["hashmarks"]["command"], [
                str(python), "/run/native-mcp-bridge.py",
                "--hashmarks", str(hashmarks), "--sha256", self.digest,
                "--workspace", str(work), "--contract",
                "/run/native-mcp-contract.json",
            ])
            substrate = {"bwrap": "/usr/bin/bwrap", "python": str(python)}
            environment = {
                "HOME": str(run / "home"), "XDG_CONFIG_HOME": str(run / "config"),
                "XDG_CACHE_HOME": str(run / "cache"), "XDG_DATA_HOME": str(run / "data"),
                "XDG_STATE_HOME": str(run / "state"),
                "OPENCODE_CONFIG": str(run / "opencode.json"),
                "OPENCODE_CONFIG_DIR": str(run / "config"),
                "OPENCODE_DISABLE_AUTOUPDATE": "1", "OPENCODE_AUTO_SHARE": "false",
                "BENCHMARK_NATIVE_GATEWAY_TOKEN": "x" * 32, "PATH": os.defpath,
            }
            argv = build_isolated_argv(
                substrate, executable=opencode, workspace=work,
                run_root=run, gateway_dir=run / "gateway", environment=environment,
                command=[str(hashmarks), "test"], worker_port=42424,
                hashmarks_executable=hashmarks, use_native_mcp_bridge=True,
            )
            for guest in (
                "/run/native-mcp-bridge.py",
                "/run/native_mcp_bridge_contract.py",
                "/run/native-mcp-contract.json",
            ):
                self.assertIn(guest, argv)
            self.assertIn("--ro-bind", argv)
            self.assertNotIn("--share-net", argv)


class ExecutableHashmarksStdioFixture(unittest.TestCase):
    def _fixture(self, path: Path, *, wrong=False):
        packet = {"owner": "wrong.py"} if wrong else source()["content"]
        payload = json.dumps(packet)
        code = """#!/usr/bin/python3
import json
import sys
for line in sys.stdin.buffer:
    request = json.loads(line)
    mid = request.get('id')
    if request.get('method') == 'tools/call':
        response = {'jsonrpc':'2.0', 'id':mid, 'result':{
            'content':[{'type':'text','text':%r}]}}
    else:
        response = {'jsonrpc':'2.0','id':mid,'result':{'tools':[]}}
    sys.stdout.write(json.dumps(response, separators=(',',':'))+'\\n')
    sys.stdout.flush()
""" % payload
        path.write_text(code)
        path.chmod(0o700)

    def test_real_subprocess_native_stdio_roundtrip_and_fail_closed_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            workspace = root / "workspace"
            workspace.mkdir()
            executable = root / "hashmarks"
            contract = root / "contract.json"
            self._fixture(executable)
            chosen = selection()
            frozen = freeze_bridge_contract(
                chosen, original_packet=source()["content"],
                hashmarks_sha256=sha_file(executable),
            )
            write_bridge_contract(contract, frozen)
            input_bytes = (
                canonical({"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}})
                + b"\n" + call_frame() + b"\n"
            )
            output = io.BytesIO()
            status = run_stdio(
                hashmarks_executable=executable, hashmarks_sha256=sha_file(executable),
                workspace=workspace, contract_path=contract,
                stdin=io.BytesIO(input_bytes), stdout=output,
            )
            self.assertEqual(status, 0)
            lines = [json.loads(line) for line in output.getvalue().splitlines()]
            self.assertEqual(len(lines), 2)
            self.assertEqual(lines[0]["id"], 1)
            self.assertEqual(lines[1]["result"]["content"][0]["text"],
                             chosen["selected_content"])
            self.assertNotIn("structuredContent", lines[1]["result"])

            self._fixture(executable, wrong=True)
            wrong_digest = sha_file(executable)
            wrong_contract = freeze_bridge_contract(
                chosen, original_packet=source()["content"],
                hashmarks_sha256=wrong_digest,
            )
            other = root / "wrong-contract.json"
            write_bridge_contract(other, wrong_contract)
            drift_output = io.BytesIO()
            status = run_stdio(
                hashmarks_executable=executable, hashmarks_sha256=wrong_digest,
                workspace=workspace, contract_path=other,
                stdin=io.BytesIO(input_bytes), stdout=drift_output,
            )
            self.assertEqual(status, 2)
            self.assertNotIn(chosen["selected_content"].encode(), drift_output.getvalue())


if __name__ == "__main__":
    unittest.main()
