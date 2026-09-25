"""Codex CLI benchmark agent with structured JSONL evidence."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benchmarks.adapters.runtime import observe_executable
from benchmarks.harness.model import (
    McpExposure,
    Observation,
    ParticipantIdentity,
    SubjectAdapter,
    TrialContext,
)
from scripts.agent_economics.bounded_process import ProcessLimits, run_bounded


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _render_config(
    model: str | None,
    exposure: McpExposure | None,
    *,
    reasoning_effort: str | None = None,
    local_provider: str | None = None,
) -> str:
    lines: list[str] = []
    if model:
        lines.append(f"model = {_toml_string(model)}")
    if reasoning_effort:
        lines.append(
            f"model_reasoning_effort = {_toml_string(reasoning_effort)}"
        )
    if local_provider:
        lines.append(f"oss_provider = {_toml_string(local_provider)}")
    if exposure is not None:
        lines.extend(
            [
                "",
                f"[mcp_servers.{exposure.name}]",
                f"command = {_toml_string(exposure.command)}",
                "args = ["
                + ", ".join(_toml_string(value) for value in exposure.args)
                + "]",
                f"cwd = {_toml_string(str(exposure.cwd))}",
                "enabled = true",
            ]
        )
        if exposure.environment:
            lines.append(f"[mcp_servers.{exposure.name}.env]")
            for key, value in sorted(exposure.environment.items()):
                lines.append(f"{key} = {_toml_string(value)}")
    return "\n".join(lines).strip() + "\n"


def parse_codex_jsonl(raw: bytes) -> tuple[list[dict[str, Any]], list[str]]:
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    for line_no, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_no}: {exc.msg}")
            continue
        if not isinstance(value, dict):
            errors.append(f"line {line_no}: event is not an object")
            continue
        events.append(value)
    return events, errors


def _completed_items(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        event.get("item", {})
        for event in events
        if event.get("type") == "item.completed"
        and isinstance(event.get("item"), dict)
    ]


def _metrics(
    events: list[dict[str, Any]],
    *,
    subject_server: str | None,
) -> dict[str, int | float | str | bool]:
    items = _completed_items(events)
    commands = [
        item for item in items if item.get("type") == "command_execution"
    ]
    changes = [item for item in items if item.get("type") == "file_change"]
    mcp_calls = [item for item in items if item.get("type") == "mcp_tool_call"]
    subject_calls = [
        item
        for item in mcp_calls
        if subject_server and item.get("server") == subject_server
    ]
    completed = [
        event for event in events if event.get("type") == "turn.completed"
    ]
    usage = completed[-1].get("usage", {}) if completed else {}
    if not isinstance(usage, dict):
        usage = {}
    result_bytes = 0
    for item in mcp_calls:
        result = item.get("result")
        if result is not None:
            result_bytes += len(
                json.dumps(
                    result,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            )
    return {
        "event_count": len(events),
        "command_calls": len(commands),
        "file_change_events": len(changes),
        "tool_calls": len(commands) + len(changes) + len(mcp_calls),
        "mcp_calls": len(mcp_calls),
        "subject_mcp_calls": len(subject_calls),
        "subject_tool_configured": subject_server is not None,
        "subject_tool_invoked": bool(subject_calls),
        "mcp_result_bytes": result_bytes,
        "input_tokens": int(usage.get("input_tokens", 0) or 0),
        "cached_input_tokens": int(
            usage.get("cached_input_tokens", 0) or 0
        ),
        "output_tokens": int(usage.get("output_tokens", 0) or 0),
        "source_read_observability": (
            "not-authoritatively-exposed-by-codex-jsonl"
        ),
    }


_REMOTE_AUTH_VARIABLES = (
    "OPENAI_API_KEY",
    "CODEX_API_KEY",
    "CODEX_ACCESS_TOKEN",
)


def disable_codex_remote_auth(context: TrialContext) -> str:
    for name in _REMOTE_AUTH_VARIABLES:
        context.environment[name] = ""
    context.environment["BENCHMARK_CODEX_AUTH_MODE"] = (
        "disabled-local-provider"
    )
    return "disabled-local-provider"


def seed_codex_auth(
    context: TrialContext,
    source: Path | None,
) -> str:
    codex_home = Path(context.environment["CODEX_HOME"])
    codex_home.mkdir(parents=True, exist_ok=True)
    target = codex_home / "auth.json"
    if source is not None:
        source = source.expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(
                f"Codex auth seed does not exist: {source}"
            )
        shutil.copyfile(source, target)
        try:
            target.chmod(0o600)
        except OSError:
            pass
        for name in _REMOTE_AUTH_VARIABLES:
            context.environment[name] = ""
        mode = "seeded-auth-file"
    elif any(os.environ.get(name) for name in _REMOTE_AUTH_VARIABLES):
        mode = "inherited-auth-environment"
    else:
        mode = "none"
    context.environment["BENCHMARK_CODEX_AUTH_MODE"] = mode
    return mode


def _final_message(events: list[dict[str, Any]]) -> str | None:
    messages = [
        item.get("text")
        for item in _completed_items(events)
        if item.get("type") == "agent_message"
        and isinstance(item.get("text"), str)
    ]
    return messages[-1] if messages else None


@dataclass(frozen=True)
class CodexAgent:
    model: str | None = None
    reasoning_effort: str | None = None
    local_provider: str | None = None
    timeout_seconds: int = 600
    max_output_bytes: int = 50_000_000
    max_tool_calls: int | None = None

    def identity(self) -> ParticipantIdentity:
        return ParticipantIdentity(
            "codex",
            "coding_agent",
            "runtime-observed",
            {
                "model": self.model or "host-default",
                "reasoning_effort": self.reasoning_effort,
                "local_provider": self.local_provider,
                "surface": "codex-exec-json",
            },
        )

    def requires_remote_auth(self) -> bool:
        return self.local_provider is None

    def _exposure(
        self,
        context: TrialContext,
        subject: SubjectAdapter | None,
    ) -> McpExposure | None:
        if subject is None:
            return None
        return subject.mcp_exposure(context)

    def _config_path(self, context: TrialContext) -> Path:
        return Path(context.environment["CODEX_HOME"]) / "config.toml"

    def _probe_ollama(self, context: TrialContext) -> dict[str, Any]:
        if not self.model:
            return {
                "available": False,
                "reason": "local Ollama condition requires an explicit model",
            }

        executable = observe_executable(context, "ollama")
        show = run_bounded(
            repository_root=context.workspace,
            argv=("ollama", "show", self.model),
            environment=context.environment,
            limits=ProcessLimits(
                timeout_seconds=30,
                max_stdout_bytes=2_000_000,
                max_stderr_bytes=500_000,
            ),
        )
        available = (
            bool(executable.payload.get("available"))
            and not show.executable_missing
            and not show.timed_out
            and show.return_code == 0
            and not show.stdout_truncated
            and not show.stderr_truncated
        )
        descriptor_sha256 = (
            hashlib.sha256(show.stdout).hexdigest()
            if available
            else None
        )
        return {
            "available": available,
            "provider": "ollama",
            "provider_version": executable.payload.get("version"),
            "provider_executable_sha256": executable.payload.get(
                "executable_sha256"
            ),
            "model": self.model,
            "model_descriptor_sha256": descriptor_sha256,
            "show_process": show.metrics(),
            "stderr": show.stderr.decode("utf-8", errors="replace"),
        }

    def _local_provider_observation(
        self,
        context: TrialContext,
    ) -> dict[str, Any] | None:
        if self.local_provider is None:
            return None
        if self.local_provider == "ollama":
            return self._probe_ollama(context)
        return {
            "available": False,
            "provider": self.local_provider,
            "reason": "benchmark adapter does not implement provider admission",
        }

    def prepare(
        self,
        context: TrialContext,
        exposed_subject: SubjectAdapter | None,
    ) -> Observation:
        exposure = self._exposure(context, exposed_subject)
        config = _render_config(
            self.model,
            exposure,
            reasoning_effort=self.reasoning_effort,
            local_provider=self.local_provider,
        )
        config_path = self._config_path(context)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(config, encoding="utf-8")

        observed = observe_executable(context, "codex")
        local = self._local_provider_observation(context)
        available = bool(observed.payload.get("available"))
        if local is not None:
            available = available and bool(local.get("available"))

        payload = dict(observed.payload)
        payload.update(
            {
                "available": available,
                "config_sha256": hashlib.sha256(
                    config.encode()
                ).hexdigest(),
                "mcp_exposure": (
                    exposure.semantic_identity if exposure else None
                ),
                "auth_mode": context.environment.get(
                    "BENCHMARK_CODEX_AUTH_MODE",
                    "none",
                ),
                "model": self.model,
                "reasoning_effort": self.reasoning_effort,
                "local_provider": self.local_provider,
                "local_provider_observation": local,
            }
        )
        return Observation(
            payload,
            observed.raw,
            observed.measurements,
        )

    def _exec_argv(self, prompt: str) -> tuple[str, ...]:
        argv = ["codex", "exec", "--json", "--full-auto"]
        if self.model:
            argv.extend(("--model", self.model))
        if self.local_provider:
            argv.extend(
                (
                    "--oss",
                    "--local-provider",
                    self.local_provider,
                )
            )
        argv.append(prompt)
        return tuple(argv)

    def run(
        self,
        context: TrialContext,
        prompt: str,
        exposed_subject: SubjectAdapter | None,
    ) -> Observation:
        exposure = self._exposure(context, exposed_subject)
        result = run_bounded(
            repository_root=context.workspace,
            argv=self._exec_argv(prompt),
            environment=context.environment,
            limits=ProcessLimits(
                timeout_seconds=self.timeout_seconds,
                max_stdout_bytes=self.max_output_bytes,
                max_stderr_bytes=5_000_000,
            ),
        )
        events, parse_errors = parse_codex_jsonl(result.stdout)
        terminal = next(
            (
                event
                for event in reversed(events)
                if event.get("type")
                in {"turn.completed", "turn.failed", "error"}
            ),
            None,
        )
        subject_server = exposure.name if exposure else None
        metrics = _metrics(events, subject_server=subject_server)
        metrics["duration_ms"] = result.elapsed_ms
        metrics["stdout_bytes"] = len(result.stdout)
        metrics["stderr_bytes"] = len(result.stderr)
        tool_calls = int(metrics["tool_calls"])
        payload = {
            "available": not result.executable_missing,
            "terminal_event": terminal,
            "terminal_complete": bool(
                terminal
                and terminal.get("type")
                in {"turn.completed", "turn.failed"}
            ),
            "final_message": _final_message(events),
            "jsonl_parse_errors": parse_errors,
            "subject_server": subject_server,
            "tool_available": exposure is not None,
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
            "local_provider": self.local_provider,
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
        }
        return Observation(
            payload,
            result.stdout.decode("utf-8", errors="replace"),
            metrics,
        )
