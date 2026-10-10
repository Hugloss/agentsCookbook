"""E237: callable provider-host boundary adapter for exact input observations.

A model-invoking host may call this library at its real outbound request
boundary. It is NOT wired into Harbor/third-party Codex, OpenCode or Claude
Code processes, and does not claim their model-request capture. We never
generate signed receipts from arbitrary ATIF data alone or provide a CLI
that turns trial artifacts into 'host observed' evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from .evidence_lifecycle import _packet, project_evidence_lifecycle
from .host_input_attestation import (
    SCHEMA, _bound_mac, canonical, load_host_key,
)
from .trusted_treatments import assigned_cell, select_treatment, verify_manifest

MAX_REQUEST_BYTES = 8_388_608
MAX_OBSERVATIONS = 10_000


def _hex64(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


class TrustedModelRequestCapture:
    """Integration point for a privileged provider host, never a model tool.

    One instance is scoped to one frozen trial and is kept outside the
    evaluated workspace. The host must call observe_outbound_request() on
    the *actual serialized request* it is sending, not on a proposed prompt.
    Finalize only after the immutable ATIF trace is available.
    """

    def __init__(self, manifest: Mapping[str, Any], *, trial_id: str,
                 harness: str, task: str, replicate: int, arm: str,
                 host_identity: str, host_key_file: Path) -> None:
        self._manifest = verify_manifest(dict(manifest))
        assigned_cell(self._manifest, trial_id=trial_id, harness=harness,
                      task=task, replicate=replicate, arm=arm)
        if not isinstance(host_identity, str) or not 0 < len(host_identity) <= 128:
            raise ValueError("invalid-observing-host-identity")
        self._trial_id = trial_id
        self._arm = arm
        self._host_identity = host_identity
        self._key = load_host_key(host_key_file)
        self._recorded: list[dict[str, Any]] = []
        self._transport_required = False
        self._transport_attempted = False

    def observe_outbound_request(
        self, *, serialized_model_request: bytes,
        tool_call_id: str, returned_packet: object,
        request_sequence: int, current: Mapping[str, Any],
        replaced: Mapping[str, Any] | None = None,
        catalog_sha256: str, prompt_sha256: str,
        oracle_sha256: str, workspace_sha256: str,
    ) -> dict[str, str]:
        """Host validates the *actual* provider request's tool-message bytes.

        Only a syntactically matched provider-style tool message is supported.
        Unsupported provider formats fail closed; adapters for other SDK
        envelopes must be explicitly implemented and adversarially tested.
        """
        if (not isinstance(serialized_model_request, bytes)
                or not 0 < len(serialized_model_request) <= MAX_REQUEST_BYTES
                or not isinstance(tool_call_id, str) or not 0 < len(tool_call_id) <= 512
                or type(request_sequence) is not int or request_sequence <= 0
                or len(self._recorded) >= MAX_OBSERVATIONS
                or not all(_hex64(x) for x in (
                    catalog_sha256, prompt_sha256, oracle_sha256, workspace_sha256,
                ))):
            raise ValueError("invalid-host-outbound-request-arguments")
        selected = select_treatment(
            self._manifest,
            trial_id=self._trial_id,
            harness=self._assigned("harness"), task=self._assigned("task"),
            replicate=self._assigned("replicate"), arm=self._arm,
            current=current, replaced=replaced,
        )
        # The selected current content must be the actual Hashmarks return,
        # not an unrelated packet used to launder a model message identity.
        if canonical(returned_packet) != canonical(current.get("content")):
            raise ValueError("selected-source-does-not-match-returned-packet")
        packet = _packet(returned_packet)
        if packet is None:
            raise ValueError("empty-returned-packet-is-not-evidence")
        try:
            request = json.loads(serialized_model_request)
        except (ValueError, UnicodeError) as exc:
            raise ValueError("non-json-host-request-not-supported") from exc
        if (not isinstance(request, dict) or not isinstance(request.get("messages"), list)
                or request.get("model") != self._manifest["design"]["model"]):
            raise ValueError("unsupported-or-cross-model-provider-request")
        expected_prompt_digest = hashlib.sha256(canonical({
            "request_settings": {key: value for key, value in request.items()
                                 if key != "messages"},
            "non_tool_messages": [
                message for message in request["messages"]
                if isinstance(message, dict) and message.get("role") != "tool"
            ],
        })).hexdigest()
        if prompt_sha256 != expected_prompt_digest:
            raise ValueError("outbound-prompt-digest-not-observed")
        # A tool packet MUST be present in exactly one specifically linked
        # model-input message. Agent prose cannot substitute for this link.
        matches = [
            message for message in request["messages"]
            if isinstance(message, dict)
            and message.get("role") == "tool"
            and message.get("tool_call_id") == tool_call_id
            and message.get("content") == selected["selected_content"]
        ]
        if len(matches) != 1:
            raise ValueError("tool-packet-not-present-exactly-once-in-model-input")
        message_digest = hashlib.sha256(canonical(matches[0])).hexdigest()
        request_digest = hashlib.sha256(canonical(request)).hexdigest()
        if any(row["call_id_sha256"] == hashlib.sha256(tool_call_id.encode()).hexdigest()
               for row in self._recorded):
            raise ValueError("duplicate-host-delivery-observation")
        intervention = {
            "study": selected["study"], "arm": selected["arm"],
            "design_sha256": selected["design_sha256"],
            "presentation": selected["presentation"],
            "generation_sha256": selected["generation_sha256"],
            "current_generation_sha256": selected["current_generation_sha256"],
            "semantic_sha256": selected["semantic_sha256"],
            "catalog_sha256": catalog_sha256,
            "prompt_sha256": prompt_sha256,
            "oracle_sha256": oracle_sha256,
            "workspace_sha256": workspace_sha256,
            "surface_sha256": selected["surface_sha256"],
        }
        self._recorded.append({
            "host_identity": self._host_identity,
            "host_build_sha256": self._manifest["host_build_sha256"],
            "model_request_sha256": request_digest,
            "model_input_sha256": hashlib.sha256(serialized_model_request).hexdigest(),
            "model_message_sha256": message_digest,
            "packet_sha256": packet[0],
            "call_id_sha256": hashlib.sha256(tool_call_id.encode()).hexdigest(),
            "model_request_sequence": request_sequence,
            "boundary": "host-model-request-input",
            "intervention": intervention,
        })
        return {
            "call_id_sha256": self._recorded[-1]["call_id_sha256"],
            "packet_sha256": packet[0],
            "model_request_sha256": request_digest,
            "host_request_observed": "true",
            "model_attention_proven": "false",
        }

    def begin_provider_transport(self) -> None:
        """One attempt only. Even failed/ambiguous dispatch cannot retry or sign."""
        if self._transport_attempted or not self._recorded:
            raise ValueError("provider-transport-retry-or-unobserved-request")
        self._transport_required = True
        self._transport_attempted = True

    def record_provider_submission(
        self, *, tool_call_id: str, serialized_model_request: bytes,
        endpoint_sha256: str, status: int,
        response_sha256: str, response_bytes: int,
    ) -> None:
        """Trusted transport calls only after a bounded 2xx response.

        Host-key authenticated submission is not provider processing proof.
        """
        if not self._transport_required or not self._transport_attempted:
            raise ValueError("provider-transport-not-started")
        if (not isinstance(tool_call_id, str) or not tool_call_id
                or not isinstance(serialized_model_request, bytes)
                or not _hex64(endpoint_sha256) or not _hex64(response_sha256)
                or type(status) is not int or not 200 <= status < 300
                or type(response_bytes) is not int or not 0 < response_bytes <= 2_097_152):
            raise ValueError("invalid-provider-submission")
        call_digest = hashlib.sha256(tool_call_id.encode("utf-8")).hexdigest()
        request_digest = hashlib.sha256(serialized_model_request).hexdigest()
        found = [
            row for row in self._recorded
            if row["call_id_sha256"] == call_digest
            and row["model_input_sha256"] == request_digest
        ]
        if len(found) != 1 or "transport" in found[0]:
            raise ValueError("provider-submission-request-mismatch-or-duplicate")
        found[0]["transport"] = {
            "boundary": "https-response",
            "endpoint_sha256": endpoint_sha256,
            "http_status": status,
            "response_sha256": response_sha256,
            "response_bytes": response_bytes,
        }

    def _assigned(self, field: str) -> Any:
        return next(x[field] for x in self._manifest["assignments"]
                    if x["trial_id"] == self._trial_id)

    def finalize(self, *, trajectory: Path, output: Path) -> dict[str, Any]:
        """Sign exact ATIF trace only when every usable packet was observed.

        Create-only output; rejects altered ATIF, missing/extra host input,
        calls with no matching returned packet and implicit second attempts.
        """
        if self._transport_required and any("transport" not in row for row in self._recorded):
            raise ValueError("provider-transport-not-proven-successful")
        lifecycle = project_evidence_lifecycle(trajectory)
        if (not lifecycle["qualified"] or lifecycle["return_state"] != "RETURNED"
                or lifecycle["unreturned_calls"] != 0 or not self._recorded):
            raise ValueError("unqualified-or-incomplete-subject-trace")
        expected = {
            (p["call_id_sha256"], p["packet_sha256"])
            for p in lifecycle["packet_refs"]
        }
        seen = {(p["call_id_sha256"], p["packet_sha256"]) for p in self._recorded}
        if expected != seen or len(expected) != len(self._recorded):
            raise ValueError("host-observations-not-bound-to-complete-atif")
        raw = trajectory.read_bytes()
        if len(raw) > 64 * 1024 * 1024:
            raise ValueError("oversized-atif-transport")
        context = {
            "schema": SCHEMA, "campaign_id": self._manifest["design"]["campaign_id"],
            "trial_id": self._trial_id,
            "trajectory_sha256": hashlib.sha256(raw).hexdigest(),
        }
        envelope = {**context, "deliveries": [
            {**observation, "mac_sha256": _bound_mac(self._key, context, observation)}
            for observation in self._recorded
        ]}
        data = canonical(envelope) + b"\n"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(output, flags, 0o600)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            output.unlink(missing_ok=True)
            raise
        return {
            "host_input_receipt_written": True,
            "trial_id": self._trial_id,
            "observed_packets": len(self._recorded),
            "model_attention_proven": False,
            "provider_consumption_proven": False,
            "provider_submission_attested": bool(
                self._transport_required
                and all("transport" in row for row in self._recorded)
            ),
        }
