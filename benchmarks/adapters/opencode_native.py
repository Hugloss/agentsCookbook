"""Native OpenCode benchmark adapter.

OpenCode owns model/provider/auth configuration. The benchmark never writes those
settings. A shared JS runtime owns OpenCode run/session/export lifecycle. This adapter
only owns benchmark-specific MCP gating and observation projection.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benchmarks.adapters.runtime import observe_executable
from benchmarks.harness.identity import canonical_json
from benchmarks.harness.model import (
    Observation,
    ParticipantIdentity,
    SubjectAdapter,
    SubjectLifecycleMode,
    TrialContext,
)
from scripts.agent_economics.bounded_process import ProcessLimits, run_bounded


_RUNTIME_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "opencode-runtime.js"


def _parse_json_object(raw: str, label: str) -> dict[str, Any]:
    start = raw.find("{")
    if start < 0:
        raise ValueError(f"{label}: missing JSON object")
    value = json.loads(raw[start:])
    if not isinstance(value, dict):
        raise ValueError(f"{label}: expected JSON object")
    return value


def _native_environment(context: TrialContext) -> dict[str, str]:
    environment = {
        "OPENCODE_DISABLE_AUTOUPDATE": "1",
        "OPENCODE_DISABLE_PRUNE": "1",
        "OPENCODE_AUTO_SHARE": "false",
        "TMPDIR": context.environment["TMPDIR"],
        "TMP": context.environment["TMP"],
        "TEMP": context.environment["TEMP"],
    }
    return environment


def _assistant_messages(exported: dict[str, Any]) -> list[dict[str, Any]]:
    messages = exported.get("messages")
    if not isinstance(messages, list):
        return []
    return [
        message
        for message in messages
        if isinstance(message, dict)
        and isinstance(message.get("info"), dict)
        and message["info"].get("role") == "assistant"
    ]


def _parts(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for message in messages:
        parts = message.get("parts")
        if not isinstance(parts, list):
            continue
        result.extend(part for part in parts if isinstance(part, dict))
    return result


def _tool_name(part: dict[str, Any]) -> str | None:
    for key in ("tool", "toolName", "name"):
        value = part.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _observed_model(exported: dict[str, Any]) -> tuple[str | None, str | None]:
    for message in reversed(_assistant_messages(exported)):
        info = message["info"]
        model = info.get("modelID")
        provider = info.get("providerID")
        if isinstance(model, str) and model:
            return (
                f"{provider}/{model}"
                if isinstance(provider, str) and provider
                else model,
                provider if isinstance(provider, str) else None,
            )
        model = info.get("model")
        if isinstance(model, str) and model:
            provider = model.split("/", 1)[0] if "/" in model else None
            return model, provider
    return None, None


def _token_metrics(exported: dict[str, Any]) -> tuple[int, int, int]:
    input_tokens = output_tokens = cached_tokens = 0
    for message in _assistant_messages(exported):
        tokens = message["info"].get("tokens")
        if not isinstance(tokens, dict):
            continue
        input_tokens += int(tokens.get("input", 0) or 0)
        output_tokens += int(tokens.get("output", 0) or 0)
        cache = tokens.get("cache")
        if isinstance(cache, dict):
            cached_tokens += int(cache.get("read", 0) or 0)
        else:
            cached_tokens += int(tokens.get("cached", 0) or 0)
    return input_tokens, output_tokens, cached_tokens


def _metrics(
    exported: dict[str, Any],
    *,
    mcp_servers: tuple[str, ...],
    selected_server: str | None,
) -> dict[str, int | float | str | bool]:
    parts = _parts(_assistant_messages(exported))
    tool_parts = [part for part in parts if part.get("type") == "tool"]
    names = [name for part in tool_parts if (name := _tool_name(part))]
    direct_mcp_calls = [
        name
        for name in names
        if any(name.startswith(f"{server}_") for server in mcp_servers)
    ]
    nested_mcp_calls: list[str] = []
    nested_observable = True
    for part in tool_parts:
        if _tool_name(part) != "execute":
            continue
        state = part.get("state")
        metadata = state.get("metadata") if isinstance(state, dict) else None
        calls = metadata.get("toolCalls") if isinstance(metadata, dict) else None
        if not isinstance(calls, list) or any(
            not isinstance(call, dict)
            or not isinstance(call.get("tool"), str)
            for call in calls
        ):
            nested_observable = False
            continue
        nested_mcp_calls.extend(call["tool"] for call in calls)
    nested_mcp_calls = [
        name for name in nested_mcp_calls
        if any(
            name.startswith(f"{server}.")
            or name.startswith(f"tools.{server}.")
            for server in mcp_servers
        )
    ]
    mcp_calls = direct_mcp_calls + nested_mcp_calls
    subject_calls = [
        name
        for name in mcp_calls
        if selected_server and (
            name.startswith(f"{selected_server}_")
            or name.startswith(f"{selected_server}.")
            or name.startswith(f"tools.{selected_server}.")
        )
    ]
    command_calls = [
        name
        for name in names
        if name in {"bash", "shell", "terminal", "run"}
    ]
    file_changes = [
        name
        for name in names
        if name in {"edit", "write", "patch", "apply_patch"}
    ]
    result_bytes = 0
    for part in tool_parts:
        name = _tool_name(part)
        if name not in direct_mcp_calls:
            continue
        state = part.get("state")
        output = state.get("output") if isinstance(state, dict) else None
        if output is not None:
            rendered = (
                output if isinstance(output, str) else json.dumps(
                    output, sort_keys=True, separators=(",", ":"), default=str,
                )
            )
            result_bytes += len(rendered.encode("utf-8"))
    input_tokens, output_tokens, cached_tokens = _token_metrics(exported)
    metrics: dict[str, int | float | str | bool] = {
        "event_count": len(parts),
        "command_calls": len(command_calls),
        "file_change_events": len(file_changes),
        "tool_calls": len(tool_parts),
        "subject_tool_configured": selected_server is not None,
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_tokens,
        "output_tokens": output_tokens,
        "source_read_observability": (
            "not-authoritatively-exposed-by-opencode-export"
        ),
    }
    if nested_observable:
        metrics.update(
            mcp_calls=len(mcp_calls),
            subject_mcp_calls=len(subject_calls),
            subject_tool_invoked=bool(subject_calls),
        )
        if not nested_mcp_calls:
            metrics["mcp_result_bytes"] = result_bytes
    return metrics


def _runtime_call(
    context: TrialContext,
    *,
    args: tuple[str, ...],
    environment: dict[str, str],
    timeout_seconds: float,
    max_stdout_bytes: int,
) -> tuple[dict[str, Any] | None, Any]:
    result = run_bounded(
        repository_root=context.workspace,
        argv=("node", str(_RUNTIME_SCRIPT), *args),
        environment=environment,
        limits=ProcessLimits(
            timeout_seconds=timeout_seconds,
            max_stdout_bytes=max_stdout_bytes,
            max_stderr_bytes=2_000_000,
        ),
    )
    if (
        result.executable_missing
        or result.timed_out
        or result.return_code != 0
        or result.stdout_truncated
        or result.stderr_truncated
    ):
        return None, result
    try:
        envelope = json.loads(result.stdout.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, result
    if not isinstance(envelope, dict):
        return None, result
    return envelope, result


@dataclass(frozen=True)
class OpenCodeNativeAgent:
    timeout_seconds: int = 600
    max_output_bytes: int = 50_000_000
    max_tool_calls: int | None = None

    def subject_lifecycle_mode(self) -> SubjectLifecycleMode:
        return SubjectLifecycleMode.AGENT_NATIVE

    def identity(self) -> ParticipantIdentity:
        return ParticipantIdentity(
            "opencode-native",
            "coding_agent",
            "runtime-observed",
            {
                "configuration": "native-opencode",
                "model_provider": "native-opencode",
                "runtime_overlay": "mcp-tool-gating-only",
                "surface": "shared-opencode-runtime-v1",
            },
        )

    def _selected_subject(
        self,
        exposed_subject: SubjectAdapter | None,
    ) -> str | None:
        if exposed_subject is None:
            return None
        identity = exposed_subject.identity()
        if identity.kind == "control" or identity.participant_id == "none":
            return None
        return identity.participant_id

    def _resolve_native(
        self,
        context: TrialContext,
        selected_subject: str | None,
    ) -> tuple[dict[str, Any], Observation]:
        environment = _native_environment(context)
        executable = observe_executable(
            context,
            "opencode",
            environment=environment,
        )
        envelope, result = _runtime_call(
            context,
            args=(
                "inspect-config",
                "--repo",
                str(context.workspace),
                "--benchmark-subject",
                selected_subject or "none",
            ),
            environment=environment,
            timeout_seconds=30,
            max_stdout_bytes=1_000_000,
        )
        if (
            envelope is None
            or envelope.get("status") != "completed"
            or not isinstance(envelope.get("inspection"), dict)
            or not isinstance(envelope.get("effective_inspection"), dict)
        ):
            reason = "shared OpenCode runtime could not resolve native config"
            if envelope and (envelope.get("reason") or envelope.get("parse_error")):
                reason = str(envelope.get("reason") or envelope["parse_error"])
            return {}, Observation(
                {
                    **executable.payload,
                    "available": False,
                    "reason": reason,
                    "runtime_process": result.metrics(),
                    "stderr": result.stderr.decode(
                        "utf-8",
                        errors="replace",
                    ),
                },
                result.stdout.decode("utf-8", errors="replace"),
            )
        return dict(envelope), executable

    def prepare(
        self,
        context: TrialContext,
        exposed_subject: SubjectAdapter | None,
    ) -> Observation:
        selected_subject = self._selected_subject(exposed_subject)
        resolved, executable = self._resolve_native(
            context,
            selected_subject,
        )
        if not resolved:
            return executable
        inspection = resolved["inspection"]
        effective = resolved["effective_inspection"]
        model = inspection.get("model")
        provider = inspection.get("provider")
        server_rows = effective.get("mcp_servers")
        if not isinstance(server_rows, list):
            server_rows = []
        servers = {
            str(row.get("name")): bool(row.get("enabled"))
            for row in server_rows
            if isinstance(row, dict) and row.get("name")
        }
        selected = resolved.get("selected_server")
        selected_ready = selected is None or servers.get(selected) is True
        workspace_binding = resolved.get("workspace_binding")
        if not isinstance(workspace_binding, dict):
            workspace_binding = {
                "verified": selected is None,
                "reason": "shared runtime emitted no workspace-binding evidence",
            }
        binding_verified = (
            selected is None or workspace_binding.get("verified") is True
        )
        overlay_identity = dict(resolved.get("overlay_identity", {}))
        native_subject_identity = resolved.get("native_subject_identity")
        if not isinstance(native_subject_identity, dict):
            native_subject_identity = None
        workspace_binding_identity = {
            "verified": workspace_binding.get("verified") is True,
            "subject": workspace_binding.get("subject"),
            "method": workspace_binding.get("method"),
            "reason_code": workspace_binding.get("reason_code"),
        }
        evidence = {
            "runtime_contract": "agents-cookbook-opencode-runtime/v1",
            "native_config_sha256": inspection.get("config_sha256"),
            "model": model,
            "provider": provider,
            "native_mcp_servers": sorted(
                row["name"] for row in inspection.get("mcp_servers", [])
            ),
            "mcp_shape": inspection.get("mcp_shape"),
            "selected_server": selected,
            "workspace_binding": workspace_binding_identity,
            "native_subject_identity": native_subject_identity,
            "overlay_sha256": hashlib.sha256(
                canonical_json(overlay_identity)
            ).hexdigest(),
        }
        (context.control_root / "opencode-native-evidence.json").write_bytes(
            canonical_json(evidence)
        )
        available = (
            bool(executable.payload.get("available"))
            and isinstance(model, str)
            and bool(model)
            and selected_ready
            and binding_verified
        )
        reason = None
        if not isinstance(model, str) or not model:
            reason = (
                "native OpenCode config does not resolve an explicit build model"
            )
        elif not selected_ready:
            reason = (
                f"native OpenCode config does not expose enabled MCP server "
                f"{selected}"
            )
        elif not binding_verified:
            reason = str(
                workspace_binding.get("reason")
                or "native OpenCode MCP workspace binding is unverified"
            )
        return Observation(
            {
                **executable.payload,
                "available": available,
                "reason": reason,
                "observed_identity": {
                    "version": executable.payload.get("version"),
                    "executable_sha256": executable.payload.get(
                        "executable_sha256"
                    ),
                    **evidence,
                },
                "model": model,
                "provider": provider,
                "native_config_sha256": evidence["native_config_sha256"],
                "native_mcp_servers": evidence["native_mcp_servers"],
                "workspace_binding": workspace_binding,
                "native_subject_identity": native_subject_identity,
                "mcp_exposure": (
                    {
                        "name": selected,
                        "source": "native-opencode-config",
                        **overlay_identity,
                    }
                    if selected
                    else None
                ),
                "auth_mode": "native-opencode",
            },
            executable.raw,
            executable.measurements,
        )

    def _load_prepared(
        self,
        context: TrialContext,
    ) -> dict[str, Any]:
        evidence = json.loads(
            (
                context.control_root / "opencode-native-evidence.json"
            ).read_text(encoding="utf-8")
        )
        return evidence

    def run(
        self,
        context: TrialContext,
        prompt: str,
        exposed_subject: SubjectAdapter | None,
    ) -> Observation:
        evidence = self._load_prepared(context)
        environment = _native_environment(context)
        title = (
            "agents-cookbook-benchmark:"
            + context.control_root.parent.name
        )
        prompt_path = context.control_root / "opencode-prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        envelope, result = _runtime_call(
            context,
            args=(
                "run-export",
                "--repo",
                str(context.workspace),
                "--agent",
                "build",
                "--title",
                title,
                "--prompt-file",
                str(prompt_path),
                "--benchmark-subject",
                (
                    str(evidence["selected_server"])
                    if evidence.get("selected_server")
                    else "none"
                ),
                "--native-config-sha256",
                evidence["native_config_sha256"],
            ),
            environment=environment,
            timeout_seconds=self.timeout_seconds + 120,
            max_stdout_bytes=self.max_output_bytes,
        )

        exported: dict[str, Any] = {}
        export_raw = ""
        export_error: str | None = None
        session_id: str | None = None
        run_evidence: dict[str, Any] | None = None
        if envelope is None:
            export_error = "shared OpenCode runtime failed"
        else:
            session = envelope.get("session_id")
            session_id = session if isinstance(session, str) else None
            run_value = envelope.get("run")
            run_evidence = (
                run_value if isinstance(run_value, dict) else None
            )
            runtime_error = envelope.get("error")
            if isinstance(runtime_error, str) and runtime_error:
                export_error = runtime_error
            export_value = envelope.get("export")
            if isinstance(export_value, dict):
                raw = export_value.get("stdout")
                if isinstance(raw, str):
                    export_raw = raw
                if export_value.get("status") == 0:
                    try:
                        exported = _parse_json_object(
                            export_raw,
                            "opencode export",
                        )
                    except (ValueError, json.JSONDecodeError) as exc:
                        export_error = str(exc)
                else:
                    export_error = "opencode export failed"
            elif export_error is None:
                export_error = "unable to locate OpenCode session"
            parse_error = envelope.get("export_parse_error")
            if isinstance(parse_error, str) and parse_error:
                export_error = parse_error

        selected = evidence.get("selected_server")
        server_names = tuple(evidence.get("native_mcp_servers", []))
        metric_server_names = server_names + (
            (selected,) if isinstance(selected, str) else ()
        )
        metrics = (
            _metrics(
                exported,
                mcp_servers=metric_server_names,
                selected_server=(
                    selected if isinstance(selected, str) else None
                ),
            )
            if exported
            else {
                "subject_tool_configured": isinstance(selected, str),
                "source_read_observability": (
                    "not-authoritatively-exposed-by-opencode-export"
                ),
            }
        )
        metrics["duration_ms"] = result.elapsed_ms
        metrics["stdout_bytes"] = len(result.stdout)
        metrics["stderr_bytes"] = len(result.stderr)

        observed_model, observed_provider = (
            _observed_model(exported)
            if exported
            else (None, None)
        )
        final_text = (
            envelope.get("final_text")
            if isinstance(envelope, dict)
            else None
        )
        if not isinstance(final_text, str) or not final_text:
            final_text = None

        model_mismatch = (
            observed_model is not None
            and observed_model != evidence.get("model")
        )
        if observed_model is None and export_error is None:
            export_error = "OpenCode export did not identify the executed model"
        elif model_mismatch:
            export_error = (
                "OpenCode executed model differs from admitted native config: "
                f"{observed_model} != {evidence.get('model')}"
            )

        run_status = (
            run_evidence.get("status")
            if isinstance(run_evidence, dict)
            else None
        )
        complete = (
            envelope is not None
            and run_status == 0
            and export_error is None
            and final_text is not None
        )
        terminal = (
            {"type": "turn.completed"}
            if complete
            else {
                "type": "turn.failed",
                "reason": export_error or "opencode run failed",
            }
        )
        tool_calls = int(metrics.get("tool_calls", 0))
        return Observation(
            {
                "available": not result.executable_missing,
                "terminal_event": terminal,
                "terminal_complete": complete,
                "final_message": final_text,
                "jsonl_parse_errors": [],
                "subject_server": selected,
                "tool_available": isinstance(selected, str),
                "model": observed_model or evidence.get("model"),
                "provider": observed_provider or evidence.get("provider"),
                "native_config_sha256": evidence.get(
                    "native_config_sha256"
                ),
                "native_mcp_servers": list(server_names),
                "session_id": session_id,
                "runtime_contract": evidence.get("runtime_contract"),
                "budget_violation": (
                    (
                        f"tool calls {tool_calls} exceed max_tool_calls "
                        f"{self.max_tool_calls}"
                    )
                    if self.max_tool_calls is not None
                    and tool_calls > self.max_tool_calls
                    else (
                        "agent output exceeded max_output_bytes "
                        f"{self.max_output_bytes}"
                        if result.stdout_truncated
                        else None
                    )
                ),
                "process": result.metrics(),
                "runtime_run": run_evidence,
                "stderr": result.stderr.decode(
                    "utf-8",
                    errors="replace",
                ),
            },
            export_raw,
            metrics,
        )
