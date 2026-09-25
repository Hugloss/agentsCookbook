"""Native OpenCode benchmark adapter.

OpenCode owns model/provider/auth configuration. The benchmark never writes those
settings. It only applies an in-memory tool-visibility overlay so bare/Hashmarks/Enola
conditions remain comparable.
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
    McpExposure,
    Observation,
    ParticipantIdentity,
    SubjectAdapter,
    TrialContext,
)
from scripts.agent_economics.bounded_process import ProcessLimits, run_bounded


_SECRET_FRAGMENTS = (
    "apikey",
    "api_key",
    "authorization",
    "credential",
    "password",
    "secret",
    "token",
)


def _parse_json_object(raw: bytes, label: str) -> dict[str, Any]:
    text = raw.decode("utf-8", errors="replace")
    start = text.find("{")
    if start < 0:
        raise ValueError(f"{label}: missing JSON object")
    value = json.loads(text[start:])
    if not isinstance(value, dict):
        raise ValueError(f"{label}: expected JSON object")
    return value


def _sanitize(value: Any, *, key: str = "") -> Any:
    normalized = key.lower().replace("-", "_")
    if any(fragment in normalized for fragment in _SECRET_FRAGMENTS):
        return "<redacted>"
    if isinstance(value, dict):
        return {
            str(child_key): _sanitize(child, key=str(child_key))
            for child_key, child in sorted(
                value.items(),
                key=lambda item: str(item[0]),
            )
        }
    if isinstance(value, list):
        return [_sanitize(child) for child in value]
    return value


def _config_identity(config: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(_sanitize(config))).hexdigest()


def _mcp_servers(config: dict[str, Any]) -> dict[str, Any]:
    mcp = config.get("mcp")
    if not isinstance(mcp, dict):
        return {}
    nested = mcp.get("servers")
    if isinstance(nested, dict):
        return nested
    return mcp


def _configured_model(config: dict[str, Any]) -> str | None:
    agent = config.get("agent")
    if isinstance(agent, dict):
        build = agent.get("build")
        if isinstance(build, dict):
            model = build.get("model")
            if isinstance(model, str) and model:
                return model
    model = config.get("model")
    return model if isinstance(model, str) and model else None


def _provider_from_model(model: str | None) -> str | None:
    if not model or "/" not in model:
        return None
    return model.split("/", 1)[0]


def _native_environment(
    context: TrialContext,
    *,
    overlay: dict[str, Any] | None = None,
) -> dict[str, str]:
    environment = {
        "OPENCODE_DISABLE_AUTOUPDATE": "1",
        "OPENCODE_DISABLE_PRUNE": "1",
        "OPENCODE_AUTO_SHARE": "false",
        "TMPDIR": context.environment["TMPDIR"],
        "TMP": context.environment["TMP"],
        "TEMP": context.environment["TEMP"],
    }
    if overlay is not None:
        environment["OPENCODE_CONFIG_CONTENT"] = json.dumps(
            overlay,
            sort_keys=True,
            separators=(",", ":"),
        )
    return environment


def _tool_overlay(
    *,
    server_names: tuple[str, ...],
    selected_server: str | None,
) -> dict[str, Any]:
    tools = {
        f"{name}_*": name == selected_server
        for name in sorted(server_names)
    }
    return {
        "tools": tools,
        "agent": {
            "build": {
                "tools": tools,
            }
        },
    }


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


def _final_message(exported: dict[str, Any]) -> str | None:
    messages = _assistant_messages(exported)
    if not messages:
        return None
    parts = messages[-1].get("parts")
    if not isinstance(parts, list):
        return None
    text = [
        part.get("text")
        for part in parts
        if isinstance(part, dict)
        and part.get("type") == "text"
        and isinstance(part.get("text"), str)
    ]
    value = "\n".join(text).strip()
    return value or None


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
            return model, _provider_from_model(model)
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
    mcp_calls = [
        name
        for name in names
        if any(name.startswith(f"{server}_") for server in mcp_servers)
    ]
    subject_calls = [
        name
        for name in mcp_calls
        if selected_server and name.startswith(f"{selected_server}_")
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
        if name not in mcp_calls:
            continue
        state = part.get("state")
        if state is not None:
            result_bytes += len(
                json.dumps(
                    state,
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str,
                ).encode()
            )
    input_tokens, output_tokens, cached_tokens = _token_metrics(exported)
    return {
        "event_count": len(parts),
        "command_calls": len(command_calls),
        "file_change_events": len(file_changes),
        "tool_calls": len(tool_parts),
        "mcp_calls": len(mcp_calls),
        "subject_mcp_calls": len(subject_calls),
        "subject_tool_configured": selected_server is not None,
        "subject_tool_invoked": bool(subject_calls),
        "mcp_result_bytes": result_bytes,
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_tokens,
        "output_tokens": output_tokens,
        "source_read_observability": (
            "not-authoritatively-exposed-by-opencode-export"
        ),
    }


@dataclass(frozen=True)
class OpenCodeNativeAgent:
    timeout_seconds: int = 600
    max_output_bytes: int = 50_000_000
    max_tool_calls: int | None = None

    def identity(self) -> ParticipantIdentity:
        return ParticipantIdentity(
            "opencode-native",
            "coding_agent",
            "runtime-observed",
            {
                "configuration": "native-opencode",
                "model_provider": "native-opencode",
                "runtime_overlay": "mcp-tool-gating-only",
                "surface": "opencode-run-export",
            },
        )

    def _resolve_native(
        self,
        context: TrialContext,
    ) -> tuple[dict[str, Any], Observation]:
        environment = _native_environment(context)
        executable = observe_executable(
            context,
            "opencode",
            environment=environment,
        )
        result = run_bounded(
            repository_root=context.workspace,
            argv=("opencode", "--pure", "debug", "config"),
            environment=environment,
            limits=ProcessLimits(
                timeout_seconds=30,
                max_stdout_bytes=5_000_000,
                max_stderr_bytes=1_000_000,
            ),
        )
        if (
            result.executable_missing
            or result.timed_out
            or result.return_code != 0
            or result.stdout_truncated
            or result.stderr_truncated
        ):
            return {}, Observation(
                {
                    **executable.payload,
                    "available": False,
                    "reason": "opencode native config could not be resolved",
                    "config_process": result.metrics(),
                    "stderr": result.stderr.decode(
                        "utf-8",
                        errors="replace",
                    ),
                },
                result.stdout.decode("utf-8", errors="replace"),
            )
        try:
            config = _parse_json_object(result.stdout, "opencode debug config")
        except (ValueError, json.JSONDecodeError) as exc:
            return {}, Observation(
                {
                    **executable.payload,
                    "available": False,
                    "reason": str(exc),
                    "config_process": result.metrics(),
                },
                result.stdout.decode("utf-8", errors="replace"),
            )
        return config, executable

    def _selected_server(
        self,
        context: TrialContext,
        subject: SubjectAdapter | None,
    ) -> str | None:
        if subject is None:
            return None
        exposure = subject.mcp_exposure(context)
        return exposure.name if exposure is not None else None

    def prepare(
        self,
        context: TrialContext,
        exposed_subject: SubjectAdapter | None,
    ) -> Observation:
        config, executable = self._resolve_native(context)
        if not config:
            return executable

        model = _configured_model(config)
        servers = _mcp_servers(config)
        selected = self._selected_server(context, exposed_subject)
        selected_config = servers.get(selected) if selected else None
        selected_ready = selected is None or (
            isinstance(selected_config, dict)
            and selected_config.get("enabled", True) is not False
            and selected_config.get("disabled", False) is not True
        )
        overlay = _tool_overlay(
            server_names=tuple(sorted(servers)),
            selected_server=selected,
        )
        evidence = {
            "native_config_sha256": _config_identity(config),
            "model": model,
            "provider": _provider_from_model(model),
            "native_mcp_servers": sorted(servers),
            "selected_server": selected,
            "overlay_sha256": hashlib.sha256(
                canonical_json(overlay)
            ).hexdigest(),
        }
        evidence_path = context.control_root / "opencode-native-evidence.json"
        evidence_path.write_bytes(canonical_json(evidence))
        overlay_path = context.control_root / "opencode-native-overlay.json"
        overlay_path.write_bytes(canonical_json(overlay))

        available = (
            bool(executable.payload.get("available"))
            and model is not None
            and selected_ready
        )
        reason = None
        if model is None:
            reason = (
                "native OpenCode config does not resolve an explicit build model"
            )
        elif not selected_ready:
            reason = (
                f"native OpenCode config does not expose enabled MCP server "
                f"{selected}"
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
                "provider": _provider_from_model(model),
                "native_config_sha256": evidence["native_config_sha256"],
                "native_mcp_servers": evidence["native_mcp_servers"],
                "mcp_exposure": (
                    {"name": selected, "source": "native-opencode-config"}
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
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        evidence = json.loads(
            (
                context.control_root / "opencode-native-evidence.json"
            ).read_text(encoding="utf-8")
        )
        overlay = json.loads(
            (
                context.control_root / "opencode-native-overlay.json"
            ).read_text(encoding="utf-8")
        )
        return evidence, overlay

    def _find_session(
        self,
        context: TrialContext,
        *,
        environment: dict[str, str],
        title: str,
    ) -> str | None:
        result = run_bounded(
            repository_root=context.workspace,
            argv=(
                "opencode",
                "--pure",
                "session",
                "list",
                "--format",
                "json",
                "--max-count",
                "20",
            ),
            environment=environment,
            limits=ProcessLimits(
                timeout_seconds=30,
                max_stdout_bytes=2_000_000,
                max_stderr_bytes=500_000,
            ),
        )
        if result.return_code != 0 or result.timed_out:
            return None
        try:
            sessions = json.loads(
                result.stdout.decode("utf-8", errors="replace")
            )
        except json.JSONDecodeError:
            return None
        if not isinstance(sessions, list):
            return None
        workspace = str(context.workspace.resolve())
        for session in sessions:
            if (
                isinstance(session, dict)
                and session.get("title") == title
                and session.get("directory") == workspace
                and isinstance(session.get("id"), str)
            ):
                return session["id"]
        return None

    def run(
        self,
        context: TrialContext,
        prompt: str,
        exposed_subject: SubjectAdapter | None,
    ) -> Observation:
        evidence, overlay = self._load_prepared(context)
        config, _ = self._resolve_native(context)
        if (
            not config
            or _config_identity(config)
            != evidence["native_config_sha256"]
            or _configured_model(config) != evidence["model"]
        ):
            return Observation(
                {
                    "available": True,
                    "terminal_event": {
                        "type": "turn.failed",
                        "reason": "native OpenCode config changed after admission",
                    },
                    "terminal_complete": False,
                    "final_message": None,
                    "jsonl_parse_errors": [],
                    "process": {},
                },
                "",
            )

        environment = _native_environment(context, overlay=overlay)
        title = (
            "agents-cookbook-benchmark:"
            + context.control_root.parent.name
        )
        result = run_bounded(
            repository_root=context.workspace,
            argv=(
                "opencode",
                "--pure",
                "run",
                "--dir",
                str(context.workspace),
                "--agent",
                "build",
                "--title",
                title,
                "--format",
                "json",
                prompt,
            ),
            environment=environment,
            limits=ProcessLimits(
                timeout_seconds=self.timeout_seconds,
                max_stdout_bytes=self.max_output_bytes,
                max_stderr_bytes=5_000_000,
            ),
        )
        session_id = self._find_session(
            context,
            environment=environment,
            title=title,
        )
        exported: dict[str, Any] = {}
        export_raw = b""
        export_error: str | None = None
        if session_id:
            export = run_bounded(
                repository_root=context.workspace,
                argv=("opencode", "--pure", "export", session_id),
                environment=environment,
                limits=ProcessLimits(
                    timeout_seconds=60,
                    max_stdout_bytes=self.max_output_bytes,
                    max_stderr_bytes=2_000_000,
                ),
            )
            export_raw = export.stdout
            if (
                export.return_code == 0
                and not export.timed_out
                and not export.stdout_truncated
            ):
                try:
                    exported = _parse_json_object(
                        export.stdout,
                        "opencode export",
                    )
                except (ValueError, json.JSONDecodeError) as exc:
                    export_error = str(exc)
            else:
                export_error = "opencode export failed or exceeded bounds"

            run_bounded(
                repository_root=context.workspace,
                argv=(
                    "opencode",
                    "--pure",
                    "session",
                    "delete",
                    session_id,
                ),
                environment=environment,
                limits=ProcessLimits(
                    timeout_seconds=30,
                    max_stdout_bytes=200_000,
                    max_stderr_bytes=200_000,
                ),
            )
        else:
            export_error = "unable to locate OpenCode session"

        selected = evidence.get("selected_server")
        server_names = tuple(evidence.get("native_mcp_servers", []))
        metrics = (
            _metrics(
                exported,
                mcp_servers=server_names,
                selected_server=selected,
            )
            if exported
            else {
                "event_count": 0,
                "command_calls": 0,
                "file_change_events": 0,
                "tool_calls": 0,
                "mcp_calls": 0,
                "subject_mcp_calls": 0,
                "subject_tool_configured": selected is not None,
                "subject_tool_invoked": False,
                "mcp_result_bytes": 0,
                "input_tokens": 0,
                "cached_input_tokens": 0,
                "output_tokens": 0,
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
        final = _final_message(exported) if exported else None
        tool_calls = int(metrics["tool_calls"])
        complete = (
            result.return_code == 0
            and not result.timed_out
            and not result.stdout_truncated
            and export_error is None
            and final is not None
        )
        terminal = (
            {"type": "turn.completed"}
            if complete
            else {
                "type": "turn.failed",
                "reason": export_error or "opencode run failed",
            }
        )
        return Observation(
            {
                "available": not result.executable_missing,
                "terminal_event": terminal,
                "terminal_complete": complete,
                "final_message": final,
                "jsonl_parse_errors": [],
                "subject_server": selected,
                "tool_available": selected is not None,
                "model": observed_model or evidence.get("model"),
                "provider": (
                    observed_provider or evidence.get("provider")
                ),
                "native_config_sha256": evidence.get(
                    "native_config_sha256"
                ),
                "native_mcp_servers": list(server_names),
                "session_id": session_id,
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
                "stderr": result.stderr.decode(
                    "utf-8",
                    errors="replace",
                ),
            },
            export_raw.decode("utf-8", errors="replace"),
            metrics,
        )
