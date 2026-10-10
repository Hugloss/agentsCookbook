"""E241/E242: single-attempt OpenAI-compatible HTTPS request boundary.

This provides a runnable, deliberately narrow provider transport owned by a
trusted external host. It does not intercept native Codex/OpenCode/Claude Code.
No retry, redirect, alternate URL, proxy fallback, or unsigned observation
can satisfy provider-submission verification. The host owns real credential
custody; this module never writes request/response contents to disk.
"""

from __future__ import annotations

import hashlib
import json
import ssl
from typing import Any, Mapping
from urllib.parse import urlsplit
from urllib.request import (
    HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener,
)

from .host_input_attestation import canonical
from .trusted_host_capture import TrustedModelRequestCapture

MAX_BODY_BYTES = 8_388_608
MAX_RESPONSE_BYTES = 2_097_152


class _RejectRedirect(HTTPRedirectHandler):
    def redirect_request(self, req: object, fp: object, code: object,
                         msg: object, headers: object, newurl: object) -> None:
        raise ValueError("provider-redirect-forbidden")


def _endpoint(endpoint: str, *, approved_origin: str) -> str:
    """Origin pinned by the privileged host, never returned by the agent."""
    if not isinstance(endpoint, str) or not isinstance(approved_origin, str):
        raise ValueError("invalid-provider-endpoint")
    url = urlsplit(endpoint)
    trusted = urlsplit(approved_origin)
    if (url.scheme != "https" or trusted.scheme != "https"
            or not url.hostname or not trusted.hostname
            or url.username is not None or url.password is not None
            or trusted.username is not None or trusted.password is not None
            or url.query or url.fragment or trusted.query or trusted.fragment
            or trusted.path not in ("", "/")
            or (url.hostname, url.port or 443) !=
               (trusted.hostname, trusted.port or 443)
            or url.path != "/v1/chat/completions"):
        raise ValueError("untrusted-provider-endpoint-or-path")
    return endpoint


def dispatch_verified_chat_request(
    capture: TrustedModelRequestCapture,
    *,
    serialized_model_request: bytes,
    endpoint: str, approved_origin: str, api_key: str,
    tool_call_id: str, returned_packet: object, request_sequence: int,
    current: Mapping[str, Any], replaced: Mapping[str, Any] | None = None,
    catalog_sha256: str, prompt_sha256: str,
    oracle_sha256: str, workspace_sha256: str,
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    """Execute exactly one validated request through an HTTPS transport.

    Validate before work; only a bounded successful response is marked
    submitted. Failures never permit retry or a finalized transport receipt
    on this capture instance. Model attention and provider consumption
    are unproven even when a 2xx JSON response is observed.
    """
    if not isinstance(capture, TrustedModelRequestCapture):
        raise ValueError("trusted-host-capture-required")
    url = _endpoint(endpoint, approved_origin=approved_origin)
    if (not isinstance(api_key, str) or not 1 <= len(api_key) <= 4096
            or any(ch in api_key for ch in ("\r", "\n"))
            or type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 300
            or not isinstance(serialized_model_request, bytes)
            or not 0 < len(serialized_model_request) <= MAX_BODY_BYTES):
        raise ValueError("invalid-host-provider-transport-parameters")
    # The capture validates declared assignment, model, tool response, exact
    # model-input message and non-tool prompt identity before network work.
    observed = capture.observe_outbound_request(
        serialized_model_request=serialized_model_request,
        tool_call_id=tool_call_id, returned_packet=returned_packet,
        request_sequence=request_sequence, current=current, replaced=replaced,
        catalog_sha256=catalog_sha256, prompt_sha256=prompt_sha256,
        oracle_sha256=oracle_sha256, workspace_sha256=workspace_sha256,
    )
    capture.begin_provider_transport()
    # Explicitly suppress proxy environment influence and redirect following.
    opener = build_opener(
        ProxyHandler({}), _RejectRedirect(),
        HTTPSHandler(context=ssl.create_default_context()),
    )
    req = Request(
        url, data=serialized_model_request, method="POST",
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with opener.open(req, timeout=timeout_seconds) as response:
            status = response.status
            body = response.read(MAX_RESPONSE_BYTES + 1)
        if (type(status) is not int or not 200 <= status < 300
                or not isinstance(body, bytes)
                or not 0 < len(body) <= MAX_RESPONSE_BYTES):
            raise ValueError("provider-response-incomplete")
        parsed = json.loads(body)
        if (not isinstance(parsed, dict)
                or not isinstance(parsed.get("choices"), list)
                or not parsed["choices"]):
            raise ValueError("invalid-openai-compatible-provider-response")
    except Exception:
        # Do not leak provider URL, request/response content, credentials, or
        # exception descriptions (network errors can embed secrets).
        raise ValueError("provider-submission-unverified") from None
    capture.record_provider_submission(
        tool_call_id=tool_call_id,
        serialized_model_request=serialized_model_request,
        endpoint_sha256=hashlib.sha256(url.encode("utf-8")).hexdigest(),
        status=status,
        response_sha256=hashlib.sha256(body).hexdigest(),
        response_bytes=len(body),
    )
    return {
        "schema": "agentscookbook.provider-transport-submission.v1",
        "provider_submission_state": "SUBMITTED",
        "request_sha256": observed["model_request_sha256"],
        "response_sha256": hashlib.sha256(body).hexdigest(),
        "response_bytes": len(body),
        "http_status": status,
        "provider_consumption_proven": False,
        "model_attention_proven": False,
        "causal_influence_proven": False,
    }
