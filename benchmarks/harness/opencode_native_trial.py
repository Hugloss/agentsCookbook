"""E250: opt-in, version-pinned OpenCode run through captured provider.

The launcher keeps provider credentials outside the evaluated child, pins
the native executable, scopes one frozen assignment to one local port, and
rejects incomplete request/response enforcement. Native process origin is
NOT proved merely because a bearer token and environment overlay were used.

No host receipt is synthesized from the process exit code. A real completed
ATIF trace must be separately supplied to TrustedModelRequestCapture.finalize
and verified; native benchmark certification remains unavailable by default.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import time
import stat
import subprocess
from pathlib import Path
from typing import Any, Mapping

from .opencode_native_gateway import (
    NativeOpenCodeGateway, admit_opencode_binary, gateway_config,
    sha256_file, write_gateway_config,
)
from .trusted_treatments import load_manifest, verify_manifest
from .opencode_native_export import acquire_native_export
from .opencode_native_session import finalize_native_export

SCHEMA = "agentscookbook.pinned-opencode-gateway-trial.v1"


def _make_private_dir(path: Path) -> None:
    if path.exists() or path.is_symlink():
        raise ValueError("trial-run-directory-already-exists")
    path.mkdir(mode=0o700, parents=False)
    if path.stat().st_mode & 0o077:
        raise ValueError("trial-directory-permissions-not-private")


def launch_native_trial(
    manifest: Mapping[str, Any], *, trial_id: str,
    opencode_executable: Path, expected_binary_sha256: str,
    expected_version: str, run_root: Path, workspace: Path,
    prompt: str, host_key_file: Path, host_identity: str,
    current: Mapping[str, Any], replaced: Mapping[str, Any] | None,
    upstream: str, approved_origin: str,
    upstream_api_key: str, catalog_sha256: str,
    oracle_sha256: str, workspace_sha256: str,
    timeout_seconds: int = 600,
    allow_unconfined_execution: bool = False,
) -> dict[str, Any]:
    frozen = verify_manifest(dict(manifest))
    cells = [x for x in frozen["assignments"] if x["trial_id"] == trial_id]
    if len(cells) != 1 or cells[0]["harness"] not in ("opencode", "opencode-native"):
        raise ValueError("unknown-or-non-opencode-native-trial")
    if (not isinstance(prompt, str) or not 0 < len(prompt) <= 16_384
            or type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 3600):
        raise ValueError("invalid-native-trial-input")
    if (workspace.is_symlink() or not workspace.is_dir()
            or not (workspace / ".git").exists()):
        raise ValueError("untrusted-or-unbound-native-workspace")
    # This experimental standalone launch is NOT the existing bwrap-backed
    # benchmark runner. OS confinement and exclusive egress are not proven.
    # Require deliberate opt-in rather than silently executing an agent with
    # access to the user's host filesystem/network.
    if allow_unconfined_execution is not True:
        raise ValueError("unconfined-native-launch-not-explicitly-authorized")
    workspace_root = workspace.resolve()
    if (run_root.resolve().is_relative_to(workspace_root)
            or host_key_file.resolve().is_relative_to(workspace_root)):
        raise ValueError("native-run-authority-inside-evaluated-workspace")
    if any((workspace_root / name).exists()
           or (workspace_root / name).is_symlink()
           for name in ("opencode.json", "opencode.jsonc", ".opencode")):
        raise ValueError("uncontrolled-project-opencode-config")
    # No filesystem or model work before exact executable and trial admission.
    pin = admit_opencode_binary(
        opencode_executable,
        expected_sha256=expected_binary_sha256,
        expected_version=expected_version,
    )
    gateway = NativeOpenCodeGateway(
        frozen, trial_id=trial_id, host_key_file=host_key_file,
        host_identity=host_identity, current=current, replaced=replaced,
        gateway_token=secrets.token_urlsafe(32),
        upstream=upstream, approved_origin=approved_origin,
        upstream_api_key=upstream_api_key, catalog_sha256=catalog_sha256,
        oracle_sha256=oracle_sha256, workspace_sha256=workspace_sha256,
    )
    _make_private_dir(run_root)
    for name in ("home", "config", "cache", "data", "state"):
        _make_private_dir(run_root / name)
    started = False
    try:
        port = gateway.start()
        started = True
        cfg = gateway_config(port=port, model_id=frozen["design"]["model"])
        config = run_root / "opencode.json"
        config_sha256 = write_gateway_config(config, cfg)
        model = cfg["model"]
        child_env = {
            "HOME": str(run_root / "home"),
            "XDG_CONFIG_HOME": str(run_root / "config"),
            "XDG_CACHE_HOME": str(run_root / "cache"),
            "XDG_DATA_HOME": str(run_root / "data"),
            "XDG_STATE_HOME": str(run_root / "state"),
            "OPENCODE_CONFIG": str(config),
            "OPENCODE_CONFIG_DIR": str(run_root / "config"),
            "OPENCODE_DISABLE_AUTOUPDATE": "1",
            "OPENCODE_AUTO_SHARE": "false",
            "BENCHMARK_NATIVE_GATEWAY_TOKEN": gateway.token,
            "PATH": os.defpath,
        }
        # Distinguish this new session from concurrent or earlier sessions.
        # The launcher never resolves "latest session" as evidence.
        native_title = "agentscookbook:" + trial_id + ":" + secrets.token_hex(12)
        started_at_ms = time.time_ns() // 1_000_000
        # Do not pass upstream API keys or ambient LLM credentials to the
        # agent; its only configured provider is the loopback gateway.
        try:
            result = subprocess.run(
                [str(opencode_executable), "run", "--model", model,
                 "--title", native_title, "--format", "json", prompt],
                cwd=workspace, env=child_env,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=timeout_seconds, check=False,
            )
            exit_code = result.returncode
        except (OSError, subprocess.SubprocessError):
            exit_code = None
        if sha256_file(opencode_executable) != expected_binary_sha256:
            raise ValueError("native-opencode-binary-changed-during-trial")
        observation = gateway.result()
        routed = exit_code == 0 and observation["post_evidence_submissions"] == 1
        session_result: dict[str, Any] | None = None
        session_error: str | None = None
        if routed:
            try:
                session_id, exported = acquire_native_export(
                    opencode_executable, workspace=workspace,
                    environment=child_env, exact_title=native_title,
                    started_at_ms=started_at_ms,
                )
                if sha256_file(opencode_executable) != expected_binary_sha256:
                    raise ValueError("native-opencode-executable-drift-after-export")
                # Exact observed provider/model IDs must match the local
                # configured OpenCode provider, not the upstream API model.
                session_result = finalize_native_export(
                    exported, capture=gateway.capture, session_id=session_id,
                    title=native_title, workspace=workspace, run_root=run_root,
                    expected_provider="agentscookbook-captured",
                    expected_model=frozen["design"]["model"],
                    original_packet=current["content"],
                )
            except (OSError, ValueError, TypeError, UnicodeError):
                session_error = "native-session-not-bound-to-observed-provider-submission"
        qualified = routed and session_result is not None
        return {
            "schema": SCHEMA,
            "trial_id": trial_id,
            "manifest_sha256": frozen["manifest_sha256"],
            "binary_sha256": pin["executable_sha256"],
            "opencode_version": pin["version"],
            "config_sha256": config_sha256,
            "native_exit_code": exit_code,
            "gateway": observation,
            "observed_provider_response_relays": observation["post_evidence_submissions"],
            "native_gateway_route_completed": routed,
            "native_session_binding": session_result,
            "native_session_binding_error": session_error,
            "native_trial_evidence_qualified": qualified,
            "host_receipt_finalized": qualified,
            "native_process_origin_proven": False,
            "native_model_input_delivered_proven": False,
            "causal_improvement_proven": False,
        }
    finally:
        if started:
            gateway.close()


def _json_file(path: Path, *, max_bytes: int = 262_144) -> object:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > max_bytes:
        raise ValueError("untrusted-native-trial-json-source")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--trial-id", required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--binary-sha256", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--host-key-file", type=Path, required=True)
    parser.add_argument("--host-identity", required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--replaced", type=Path)
    parser.add_argument("--upstream", required=True)
    parser.add_argument("--approved-origin", required=True)
    parser.add_argument("--catalog-sha256", required=True)
    parser.add_argument("--oracle-sha256", required=True)
    parser.add_argument("--workspace-sha256", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--allow-unconfined-native-test", action="store_true")
    args = parser.parse_args()
    try:
        api_key = os.environ.get("BENCHMARK_UPSTREAM_API_KEY")
        if not api_key:
            raise ValueError("missing-privileged-upstream-api-key")
        if args.prompt_file.is_symlink() or args.prompt_file.stat().st_size > 16_384:
            raise ValueError("untrusted-prompt-file")
        result = launch_native_trial(
            load_manifest(args.manifest), trial_id=args.trial_id,
            opencode_executable=args.binary,
            expected_binary_sha256=args.binary_sha256,
            expected_version=args.version, run_root=args.run_root,
            workspace=args.workspace,
            prompt=args.prompt_file.read_text(encoding="utf-8"),
            host_key_file=args.host_key_file, host_identity=args.host_identity,
            current=_json_file(args.current),
            replaced=_json_file(args.replaced) if args.replaced else None,
            upstream=args.upstream, approved_origin=args.approved_origin,
            upstream_api_key=api_key,
            catalog_sha256=args.catalog_sha256,
            oracle_sha256=args.oracle_sha256,
            workspace_sha256=args.workspace_sha256,
            timeout_seconds=args.timeout_seconds,
            allow_unconfined_execution=args.allow_unconfined_native_test,
        )
    except (ValueError, OSError, TypeError, UnicodeError) as exc:
        print(json.dumps({
            "schema": SCHEMA, "native_gateway_route_completed": False,
            "native_process_origin_proven": False,
            "causal_improvement_proven": False,
            "reason": str(exc),
        }, indent=2, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["native_trial_evidence_qualified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
