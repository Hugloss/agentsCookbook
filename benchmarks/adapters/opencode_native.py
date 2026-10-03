"""Native OpenCode benchmark adapter.

OpenCode owns model/provider/auth configuration. The benchmark never writes those
settings. The selected subject adapter owns the exact MCP executable and invocation.
A shared JS runtime overlays only that benchmark subject plus MCP tool gating, then
owns OpenCode run/session/export lifecycle and observation projection.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from benchmarks.adapters.runtime import observe_executable, resolve_native_executable
from benchmarks.harness.identity import canonical_json
from benchmarks.harness.runtime_authority import PROCESS_SUBSTRATE_ENV_KEYS
from benchmarks.harness.model import (
    Observation,
    ParticipantIdentity,
    SubjectAdapter,
    SubjectLifecycleMode,
    TrialContext,
)
from scripts.agent_economics.bounded_process import ProcessLimits, run_bounded


_RUNTIME_SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts" / "opencode-runtime.js"
)

_EXECUTABLE_OBSERVATION_CACHE: dict[tuple[str, str], Observation] = {}
_EXECUTABLE_OBSERVATION_CACHE_LOCK = Lock()
_BASE_CONFIG_CACHE: dict[tuple[str, str, str, str, str, str], dict[str, Any]] = {}
_BASE_CONFIG_CACHE_LOCK = Lock()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _observe_opencode_executable(
    context: TrialContext,
    environment: dict[str, str],
) -> Observation:
    """Reuse version evidence only for byte-identical OpenCode executables.

    Config, MCP, workspace-binding, and model authority remain freshly observed.
    """
    command = environment["OPENCODE_BIN"]
    resolved = resolve_native_executable(
        context,
        command,
        environment=environment,
    )
    if resolved is None:
        return observe_executable(
            context,
            command,
            environment=environment,
        )

    try:
        executable_sha256 = _sha256_file(Path(resolved))
    except OSError:
        return observe_executable(
            context,
            command,
            environment=environment,
        )

    key = (resolved, executable_sha256)
    with _EXECUTABLE_OBSERVATION_CACHE_LOCK:
        cached = _EXECUTABLE_OBSERVATION_CACHE.get(key)
    if cached is not None:
        return Observation(
            {**cached.payload, "cache_hit": True},
            cached.raw,
            {**cached.measurements, "cache_hit": True},
        )

    observed = observe_executable(
        context,
        command,
        environment=environment,
    )
    if (
        observed.payload.get("available") is True
        and observed.payload.get("executable_sha256") == executable_sha256
    ):
        with _EXECUTABLE_OBSERVATION_CACHE_LOCK:
            _EXECUTABLE_OBSERVATION_CACHE[key] = observed
    return observed


def _base_config_cache_key(
    context: TrialContext,
    environment: dict[str, str],
    executable: Observation,
) -> tuple[str, str, str, str, str, str] | None:
    """Scope reusable base config to one exact admitted task/native authority."""
    scope = context.admission_scope
    executable_sha256 = executable.payload.get("executable_sha256")
    if not isinstance(scope, str) or not scope:
        return None
    if not isinstance(executable_sha256, str) or not executable_sha256:
        return None
    return (
        scope,
        environment["OPENCODE_BIN"],
        executable_sha256,
        context.environment["BENCHMARK_OPENCODE_AGENT"],
        environment["HOME"],
        environment["XDG_CONFIG_HOME"],
    )


def _cached_base_config(
    key: tuple[str, str, str, str, str, str] | None,
) -> dict[str, Any] | None:
    if key is None:
        return None
    with _BASE_CONFIG_CACHE_LOCK:
        cached = _BASE_CONFIG_CACHE.get(key)
    return dict(cached) if cached is not None else None


def _store_base_config(
    key: tuple[str, str, str, str, str, str] | None,
    value: Any,
) -> None:
    if key is None or not isinstance(value, dict):
        return
    with _BASE_CONFIG_CACHE_LOCK:
        _BASE_CONFIG_CACHE[key] = dict(value)


def _parse_json_object(raw: str, label: str) -> dict[str, Any]:
    value = json.loads(raw.strip())
    if not isinstance(value, dict):
        raise ValueError(f"{label}: expected JSON object")
    return value


def _bounded_diagnostic(value: Any, *, limit: int = 2_000) -> str | None:
    if not isinstance(value, str):
        return None
    rendered = value.strip()
    if not rendered:
        return None
    if len(rendered) <= limit:
        return rendered
    return rendered[:limit] + "…"


def _bounded_tail_diagnostic(value: Any, *, limit: int = 2_000) -> str | None:
    if not isinstance(value, str):
        return None
    rendered = value.strip()
    if not rendered:
        return None
    if len(rendered) <= limit:
        return rendered
    return "…" + rendered[-limit:]


def _run_failure_reason(
    run_evidence: dict[str, Any] | None,
    *,
    export_error: str | None,
    final_text: str | None,
) -> str | None:
    if run_evidence is None:
        return export_error or "OpenCode runtime emitted no run result"

    run_status = run_evidence.get("status")
    if run_status != 0:
        if run_status is None:
            reason = "OpenCode runtime emitted no run status"
        else:
            reason = f"OpenCode run exited with status {run_status}"
        details: list[str] = []
        stderr = _bounded_diagnostic(run_evidence.get("stderr"))
        if stderr:
            details.append(f"stderr={stderr!r}")
        error = _bounded_diagnostic(run_evidence.get("error"))
        if error:
            details.append(f"error={error!r}")
        if not details:
            stdout_tail = _bounded_tail_diagnostic(run_evidence.get("stdout"))
            if stdout_tail:
                details.append(f"stdout_tail={stdout_tail!r}")
        signal = run_evidence.get("signal")
        if isinstance(signal, str) and signal:
            details.append(f"signal={signal}")
        return "; ".join((reason, *details))

    if export_error is not None:
        return export_error
    if final_text is None:
        return "OpenCode completed without a final assistant message"
    return None


def _native_environment(context: TrialContext) -> dict[str, str]:
    required = (
        "BENCHMARK_NATIVE_HOME",
        "BENCHMARK_NATIVE_XDG_CONFIG_HOME",
        "BENCHMARK_OPENCODE_AGENT",
    )
    missing = [name for name in required if not context.environment.get(name)]
    if missing:
        raise ValueError(
            "native OpenCode environment could not be established: "
            + ", ".join(missing)
        )
    resolved = resolve_native_executable(context, "opencode")
    if resolved is None:
        raise ValueError("opencode is not available on the native PATH")
    environment = {
        "OPENCODE_BIN": resolved,
        "HOME": context.environment["BENCHMARK_NATIVE_HOME"],
        "XDG_CONFIG_HOME": context.environment["BENCHMARK_NATIVE_XDG_CONFIG_HOME"],
        "OPENCODE_DISABLE_AUTOUPDATE": "1",
        "OPENCODE_DISABLE_PRUNE": "1",
        "OPENCODE_AUTO_SHARE": "false",
        "TMPDIR": context.environment["TMPDIR"],
        "TMP": context.environment["TMP"],
        "TEMP": context.environment["TEMP"],
        "XDG_CACHE_HOME": context.environment["XDG_CACHE_HOME"],
        "XDG_STATE_HOME": context.environment["XDG_STATE_HOME"],
    }
    for name in PROCESS_SUBSTRATE_ENV_KEYS:
        value = context.environment.get(name)
        if value:
            environment[name] = value
    for name in (
        key.strip()
        for key in context.environment.get(
            "BENCHMARK_PASSTHROUGH_ENV_KEYS",
            "",
        ).split(",")
        if key.strip()
    ):
        value = context.environment.get(name)
        if value:
            environment[name] = value
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


def _subject_tool_name(name: str, selected_server: str | None) -> str:
    if selected_server is None:
        return name
    for prefix in (
        f"tools.{selected_server}.",
        f"{selected_server}.",
        f"{selected_server}_",
    ):
        if name.startswith(prefix):
            return name[len(prefix) :]
    return name


def _metrics(
    exported: dict[str, Any],
    *,
    mcp_servers: tuple[str, ...],
    selected_server: str | None,
) -> dict[str, Any]:
    parts = _parts(_assistant_messages(exported))
    tool_parts = [part for part in parts if part.get("type") == "tool"]
    names = [name for part in tool_parts if (name := _tool_name(part))]
    direct_mcp_calls = [
        name
        for name in names
        if any(name.startswith(f"{server}_") for server in mcp_servers)
    ]
    nested_tool_calls: list[str] = []
    nested_mcp_calls: list[str] = []
    observed_tool_sequence: list[str] = []
    nested_observable = True
    for part in tool_parts:
        direct_name = _tool_name(part)
        if direct_name:
            observed_tool_sequence.append(direct_name)
        if direct_name != "execute":
            continue
        state = part.get("state")
        metadata = state.get("metadata") if isinstance(state, dict) else None
        calls = metadata.get("toolCalls") if isinstance(metadata, dict) else None
        if not isinstance(calls, list) or any(
            not isinstance(call, dict) or not isinstance(call.get("tool"), str)
            for call in calls
        ):
            nested_observable = False
            continue
        nested_names = [call["tool"] for call in calls]
        nested_tool_calls.extend(nested_names)
        observed_tool_sequence.extend(f"nested:{name}" for name in nested_names)
    nested_mcp_calls = [
        name
        for name in nested_tool_calls
        if any(
            name.startswith(f"{server}.") or name.startswith(f"tools.{server}.")
            for server in mcp_servers
        )
    ]
    mcp_calls = direct_mcp_calls + nested_mcp_calls
    def is_subject_call(name: str) -> bool:
        return bool(
            selected_server
            and (
                name.startswith(f"{selected_server}_")
                or name.startswith(f"{selected_server}.")
                or name.startswith(f"tools.{selected_server}.")
            )
        )

    direct_subject_calls = [name for name in direct_mcp_calls if is_subject_call(name)]
    subject_calls = [name for name in mcp_calls if is_subject_call(name)]
    command_calls = [
        name for name in names if name in {"bash", "shell", "terminal", "run"}
    ]
    file_changes = [
        name for name in names if name in {"edit", "write", "patch", "apply_patch"}
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
                output
                if isinstance(output, str)
                else json.dumps(
                    output,
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str,
                )
            )
            result_bytes += len(rendered.encode("utf-8"))
    input_tokens, output_tokens, cached_tokens = _token_metrics(exported)
    subject_ordinals = [
        index
        for index, name in enumerate(observed_tool_sequence, 1)
        if is_subject_call(name.removeprefix("nested:"))
    ]
    metrics: dict[str, Any] = {
        "event_count": len(parts),
        "command_calls": len(command_calls),
        "file_change_events": len(file_changes),
        "tool_calls": len(tool_parts),
        "subject_tool_configured": selected_server is not None,
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_tokens,
        "output_tokens": output_tokens,
        "source_read_observability": ("not-authoritatively-exposed-by-opencode-export"),
        "tool_strategy_observability": (
            "opencode-export-direct+execute-metadata"
            if nested_observable
            else "opencode-export-direct-only-partial"
        ),
        "tool_name_counts": dict(
            sorted(Counter(observed_tool_sequence).items())
        ),
        "tool_sequence": observed_tool_sequence,
        "subject_tool_call_ordinals": subject_ordinals,
        "subject_first_tool_call_ordinal": (
            subject_ordinals[0] if subject_ordinals else None
        ),
    }
    if selected_server is not None:
        observed_subject_calls = (
            subject_calls if nested_observable else direct_subject_calls
        )
        metrics.update(
            subject_mcp_calls_observed=len(observed_subject_calls),
            subject_tool_names=sorted(
                {
                    _subject_tool_name(name, selected_server)
                    for name in observed_subject_calls
                }
            ),
            subject_tool_observability=(
                "complete" if nested_observable else "partial"
            ),
        )
    if nested_observable:
        metrics.update(
            mcp_calls=len(mcp_calls),
            subject_mcp_calls=len(subject_calls),
            subject_tool_invoked=bool(subject_calls),
        )
        if not nested_mcp_calls:
            metrics["mcp_result_bytes"] = result_bytes
    elif direct_subject_calls:
        # Direct exported MCP calls are authoritative positive evidence even
        # when nested execute() metadata is incomplete. Absence remains unknown.
        metrics["subject_tool_invoked"] = True
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
        inherit_environment=False,
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
                "runtime_overlay": "benchmark-subject-exposure+tool-gating-only",
                "surface": "shared-opencode-runtime-v2",
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

    def _subject_exposure(
        self,
        context: TrialContext,
        exposed_subject: SubjectAdapter | None,
        selected_subject: str | None,
    ) -> tuple[Path | None, dict[str, Any] | None]:
        if selected_subject is None:
            return None, None
        if exposed_subject is None:
            raise ValueError(f"benchmark subject {selected_subject} is unavailable")
        exposure = exposed_subject.mcp_exposure(context)
        if exposure is None or exposure.name != selected_subject:
            raise ValueError(
                f"benchmark subject {selected_subject} has no matching MCP exposure"
            )
        payload = {
            "name": exposure.name,
            "command": [exposure.command, *exposure.args],
            "cwd": str(exposure.cwd),
            "environment": dict(exposure.environment),
            "semantic_identity": dict(exposure.semantic_identity),
        }
        path = context.control_root / "opencode-benchmark-exposure.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_json(payload))
        return path, payload

    def _resolve_native(
        self,
        context: TrialContext,
        selected_subject: str | None,
        exposure_path: Path | None,
    ) -> tuple[dict[str, Any], Observation]:
        try:
            environment = _native_environment(context)
        except ValueError as exc:
            return {}, Observation(
                {"available": False, "reason": str(exc)},
                "",
            )
        executable = _observe_opencode_executable(
            context,
            environment,
        )
        base_cache_key = _base_config_cache_key(context, environment, executable)
        cached_base = _cached_base_config(base_cache_key)
        args = (
            "inspect-config",
            "--repo",
            str(context.workspace),
            "--agent",
            context.environment["BENCHMARK_OPENCODE_AGENT"],
            "--benchmark-subject",
            selected_subject or "none",
        )
        if exposure_path is not None:
            args += ("--benchmark-exposure-file", str(exposure_path))
        if cached_base is not None:
            base_path = context.control_root / "opencode-base-config.json"
            base_path.parent.mkdir(parents=True, exist_ok=True)
            base_path.write_bytes(canonical_json(cached_base))
            args += ("--base-config-file", str(base_path))
        elif base_cache_key is not None:
            args += ("--emit-base-config", "true")
        envelope, result = _runtime_call(
            context,
            args=args,
            environment=environment,
            timeout_seconds=min(30.0, float(self.timeout_seconds)),
            max_stdout_bytes=2_000_000,
        )
        base_snapshot = (
            envelope.pop("base_config_snapshot", None)
            if isinstance(envelope, dict)
            else None
        )
        if (
            cached_base is None
            and isinstance(envelope, dict)
            and envelope.get("status") == "completed"
        ):
            _store_base_config(base_cache_key, base_snapshot)
        if (
            envelope is None
            or envelope.get("status") != "completed"
            or not isinstance(envelope.get("inspection"), dict)
            or not isinstance(envelope.get("effective_inspection"), dict)
        ):
            reason = "shared OpenCode runtime could not resolve benchmark config"
            if envelope and (envelope.get("reason") or envelope.get("parse_error")):
                reason = str(envelope.get("reason") or envelope["parse_error"])
            return {}, Observation(
                {
                    **executable.payload,
                    "available": False,
                    "reason": reason,
                    "failure_stage": envelope.get("failure_stage")
                    if envelope
                    else None,
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
        try:
            exposure_path, subject_exposure = self._subject_exposure(
                context,
                exposed_subject,
                selected_subject,
            )
        except ValueError as exc:
            return Observation(
                {
                    "available": False,
                    "reason": str(exc),
                },
                "",
            )
        resolved, executable = self._resolve_native(
            context,
            selected_subject,
            exposure_path,
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
        binding_verified = selected is None or workspace_binding.get("verified") is True
        executable_verified = True
        if selected:
            expected = (
                subject_exposure["command"][0]
                if isinstance(subject_exposure, dict)
                and isinstance(subject_exposure.get("command"), list)
                and subject_exposure["command"]
                else None
            )
            native_identity = resolved.get("native_subject_identity")
            observed_path = (
                native_identity.get("executable_path")
                if isinstance(native_identity, dict)
                else None
            )
            executable_verified = bool(
                isinstance(expected, str)
                and isinstance(observed_path, str)
                and Path(expected).resolve() == Path(observed_path).resolve()
            )
        overlay_identity = dict(resolved.get("overlay_identity", {}))
        native_subject_identity = resolved.get("native_subject_identity")
        if not isinstance(native_subject_identity, dict):
            native_subject_identity = None
        native_identity_verified = selected is None or (
            isinstance(native_subject_identity, dict)
            and native_subject_identity.get("verified") is True
            and isinstance(
                native_subject_identity.get("executable_sha256"),
                str,
            )
        )
        workspace_binding_identity = {
            "verified": workspace_binding.get("verified") is True,
            "subject": workspace_binding.get("subject"),
            "method": workspace_binding.get("method"),
            "reason_code": workspace_binding.get("reason_code"),
        }
        evidence = {
            "runtime_contract": "agents-cookbook-opencode-runtime/v2",
            "native_config_sha256": inspection.get("config_sha256"),
            "model": model,
            "provider": provider,
            "agent": context.environment["BENCHMARK_OPENCODE_AGENT"],
            "native_mcp_servers": sorted(
                row["name"] for row in inspection.get("mcp_servers", [])
            ),
            "mcp_shape": inspection.get("mcp_shape"),
            "selected_server": selected,
            "workspace_binding": workspace_binding_identity,
            "native_subject_identity": native_subject_identity,
            "subject_exposure_sha256": overlay_identity.get("subject_exposure_sha256"),
            "native_server_shadowed": overlay_identity.get("native_server_shadowed"),
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
            and native_identity_verified
            and executable_verified
        )
        reason = None
        if not isinstance(model, str) or not model:
            reason = "native OpenCode config does not resolve an explicit build model"
        elif not selected_ready:
            reason = f"benchmark MCP server {selected} is not enabled"
        elif not binding_verified:
            reason = str(
                workspace_binding.get("reason")
                or "benchmark MCP workspace binding is unverified"
            )
        elif not executable_verified:
            reason = (
                f"benchmark MCP {selected} does not use the selected subject executable"
            )
        elif not native_identity_verified:
            reason = "benchmark MCP executable identity is unverified"
        return Observation(
            {
                **executable.payload,
                "available": available,
                "reason": reason,
                "observed_identity": {
                    "version": executable.payload.get("version"),
                    "executable_sha256": executable.payload.get("executable_sha256"),
                    **evidence,
                },
                "model": model,
                "provider": provider,
                "native_config_sha256": evidence["native_config_sha256"],
                "native_mcp_servers": evidence["native_mcp_servers"],
                "base_config_source": resolved.get("base_config_source", "fresh"),
                "workspace_binding": workspace_binding,
                "native_subject_identity": native_subject_identity,
                "mcp_exposure": (
                    {
                        "name": selected,
                        "source": "benchmark-subject-exposure",
                        **overlay_identity,
                    }
                    if selected
                    else None
                ),
                "auth_mode": "native-opencode",
            },
            executable.raw,
            {
                **executable.measurements,
                "base_config_reused": (
                    resolved.get("base_config_source") == "task-cache"
                ),
            },
        )

    def _load_prepared(
        self,
        context: TrialContext,
    ) -> dict[str, Any]:
        evidence = json.loads(
            (context.control_root / "opencode-native-evidence.json").read_text(
                encoding="utf-8"
            )
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
        title = "agents-cookbook-benchmark:" + context.control_root.parent.name
        prompt_path = context.control_root / "opencode-prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        run_args = (
            "run-export",
            "--repo",
            str(context.workspace),
            "--agent",
            context.environment["BENCHMARK_OPENCODE_AGENT"],
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
        )
        if evidence.get("selected_server"):
            run_args += (
                "--benchmark-exposure-file",
                str(context.control_root / "opencode-benchmark-exposure.json"),
                "--subject-exposure-sha256",
                str(evidence["subject_exposure_sha256"]),
            )
        run_args += (
            "--native-config-sha256",
            evidence["native_config_sha256"],
        )
        envelope, result = _runtime_call(
            context,
            args=run_args,
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
            run_evidence = run_value if isinstance(run_value, dict) else None
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
                selected_server=(selected if isinstance(selected, str) else None),
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
            _observed_model(exported) if exported else (None, None)
        )
        final_text = envelope.get("final_text") if isinstance(envelope, dict) else None
        if not isinstance(final_text, str) or not final_text:
            final_text = None

        model_mismatch = observed_model is not None and observed_model != evidence.get(
            "model"
        )
        if observed_model is None and export_error is None:
            export_error = "OpenCode export did not identify the executed model"
        elif model_mismatch:
            export_error = (
                "OpenCode executed model differs from admitted native config: "
                f"{observed_model} != {evidence.get('model')}"
            )

        failure_reason = _run_failure_reason(
            run_evidence,
            export_error=export_error,
            final_text=final_text,
        )
        complete = envelope is not None and failure_reason is None
        terminal = (
            {"type": "turn.completed"}
            if complete
            else {
                "type": "turn.failed",
                "reason": failure_reason or "OpenCode run failed",
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
                "native_config_sha256": evidence.get("native_config_sha256"),
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
