"""E260: independently re-read native netns trial receipts before a paired pilot.

This is an *observation and grading readiness* gate. It does NOT run a
provider, prove an independent timestamp/reviewer, or produce causal uplift.
A real host may supply artifacts; model-free tests only prove rejection
of unsupported or incomplete evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from .host_input_attestation import load_host_key
from .native_session_cohort_audit import audit_native_session_cohort
from .opencode_native_trial import SCHEMA as TRIAL_SCHEMA
from .native_netns_host_attestation import verify_isolation_attestation
from .trusted_treatments import load_manifest, verify_manifest

SCHEMA = "agentscookbook.netns-paired-pilot-readiness.v1"
HEX = set("0123456789abcdef")


def _hex64(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX


def evaluate_native_netns_pilot(
    manifest: Mapping[str, Any], *, results_root: Path,
    sources_root: Path, workspace: Path, host_key: bytes,
    host_identity: str, approved_endpoint_sha256: str,
    expected_bwrap_sha256: str, expected_hashmarks_sha256: str,
) -> dict[str, Any]:
    frozen = verify_manifest(dict(manifest))
    if not (_hex64(expected_bwrap_sha256) and _hex64(expected_hashmarks_sha256)):
        raise ValueError("missing-independent-binary-pins")
    cohort = audit_native_session_cohort(
        frozen, results_root=results_root, sources_root=sources_root,
        key=host_key, expected_workspace=workspace,
        host_identity=host_identity,
        approved_endpoint_sha256=approved_endpoint_sha256,
    )
    issues: Counter[str] = Counter()
    if not cohort["native_session_cohort_observationally_consistent"]:
        issues["unqualified-native-session-cohort"] += 1
    checked = 0
    for cell in frozen["assignments"]:
        receipt = results_root / cell["trial_id"] / "trial-execution.json"
        if (receipt.is_symlink() or not receipt.is_file()
                or receipt.stat().st_size > 65_536):
            issues["missing-or-unsafe-isolation-execution-receipt"] += 1
            continue
        try:
            evidence = json.loads(receipt.read_bytes())
        except (OSError, ValueError, UnicodeError):
            issues["malformed-isolation-execution-receipt"] += 1
            continue
        if not isinstance(evidence, dict) or not isinstance(evidence.get("gateway"), dict):
            issues["unrecognized-isolation-execution-receipt"] += 1
            continue
        if any((
            evidence.get("schema") != TRIAL_SCHEMA,
            evidence.get("trial_id") != cell["trial_id"],
            evidence.get("manifest_sha256") != frozen["manifest_sha256"],
            evidence.get("native_exit_code") != 0,
            evidence.get("native_trial_evidence_qualified") is not True,
            evidence.get("host_receipt_finalized") is not True,
            evidence.get("native_gateway_route_completed") is not True,
            evidence.get("linux_network_namespace_requested") is not True,
            evidence.get("host_network_egress_intentionally_disabled") is not True,
            evidence.get("kernel_distinct_netns_relay_observed") is not True,
            evidence.get("native_sandbox_binary_sha256") != expected_bwrap_sha256,
            evidence.get("frozen_hashmarks_executable_sha256") != expected_hashmarks_sha256,
            evidence.get("observed_provider_response_relays") != 1,
            evidence["gateway"].get("kernel_netns_peer_check_required") is not True,
            evidence["gateway"].get("distinct_netns_peer_connections", 0) < 1,
            evidence.get("native_process_origin_proven") is not False,
            evidence.get("causal_improvement_proven") is not False,
        )):
            issues["inconsistent-or-self-upgraded-native-isolation-receipt"] += 1
            continue
        binding = evidence.get("native_session_binding")
        if (not isinstance(binding, dict)
                or binding.get("native_session_to_gateway_packet_bound") is not True
                or binding.get("signed_host_input_and_transport_verified") is not True):
            issues["incomplete-native-session-transport-binding"] += 1
            continue
        # Execution JSON is agent-adjacent local data, not independent
        # kernel authority. Require a separate host-key signature bound
        # to its exact bytes and the original provider input attestation.
        try:
            raw_execution = receipt.read_bytes()
            original_provider = (
                results_root / cell["trial_id"] / "host-attestation.json"
            ).read_bytes()
            signed = results_root / cell["trial_id"] / "trial-execution.attestation.json"
            if not verify_isolation_attestation(
                signed, report=evidence, execution_bytes=raw_execution,
                provider_attestation_bytes=original_provider,
                host_identity=host_identity, host_key=host_key,
            ):
                raise ValueError("host-isolation-mac-or-source-mismatch")
        except (OSError, ValueError, TypeError):
            issues["host-isolation-attestation-unverified"] += 1
            continue
        checked += 1
    if checked != len(frozen["assignments"]):
        issues["incomplete-planned-native-isolation-population"] += 1
    return {
        "schema": SCHEMA,
        "campaign_id": frozen["design"]["campaign_id"],
        "manifest_sha256": frozen["manifest_sha256"],
        "planned_trials": len(frozen["assignments"]),
        "verified_local_isolation_receipts": checked,
        "native_session_cohort": cohort,
        "paired_pilot_observations_ready_for_independent_grading": not issues,
        "blockers": dict(sorted(issues.items())),
        "network_namespace_peer_observations_host_mac_verified": (
            checked == len(frozen["assignments"])
        ),
        "exclusive_network_egress_independently_audited": False,
        "native_executable_origin_independently_proven": False,
        "independent_oracle_grading_completed": False,
        "pre_work_timestamp_independently_proven": False,
        "randomized_causal_hashmarks_uplift_proven": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--sources-root", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--host-key-file", type=Path, required=True)
    parser.add_argument("--host-identity", required=True)
    parser.add_argument("--approved-endpoint-sha256", required=True)
    parser.add_argument("--bwrap-sha256", required=True)
    parser.add_argument("--hashmarks-sha256", required=True)
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()
    try:
        report = evaluate_native_netns_pilot(
            load_manifest(args.manifest), results_root=args.results_root,
            sources_root=args.sources_root, workspace=args.workspace,
            host_key=load_host_key(args.host_key_file),
            host_identity=args.host_identity,
            approved_endpoint_sha256=args.approved_endpoint_sha256,
            expected_bwrap_sha256=args.bwrap_sha256,
            expected_hashmarks_sha256=args.hashmarks_sha256,
        )
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({
            "schema": SCHEMA, "paired_pilot_observations_ready_for_independent_grading": False,
            "reason": str(exc), "randomized_causal_hashmarks_uplift_proven": False,
        }, sort_keys=True, indent=2))
        return 2
    print(json.dumps(report, sort_keys=True, indent=2))
    return 2 if (args.require_ready and
                 not report["paired_pilot_observations_ready_for_independent_grading"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
