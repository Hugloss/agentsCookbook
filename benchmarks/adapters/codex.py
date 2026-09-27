"""Codex CLI benchmark agent with structured JSONL evidence."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tomllib
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
) -> str:
    lines: list[str] = []
    if model:
        lines.append(f"model = {_toml_string(model)}")
    if reasoning_effort:
        lines.append(f"model_reasoning_effort = {_toml_string(reasoning_effort)}")
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
        if event.get("type") == "item.completed" and isinstance(event.get("item"), dict)
    ]


def _metrics(
    events: list[dict[str, Any]],
    *,
    subject_server: str | None,
) -> dict[str, int | float | str | bool]:
    items = _completed_items(events)
    commands = [item for item in items if item.get("type") == "command_execution"]
    changes = [item for item in items if item.get("type") == "file_change"]
    mcp_calls = [item for item in items if item.get("type") == "mcp_tool_call"]
    subject_calls = [
        item
        for item in mcp_calls
        if subject_server and item.get("server") == subject_server
    ]
    completed = [event for event in events if event.get("type") == "turn.completed"]
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
        "cached_input_tokens": int(usage.get("cached_input_tokens", 0) or 0),
        "output_tokens": int(usage.get("output_tokens", 0) or 0),
        "source_read_observability": ("not-authoritatively-exposed-by-codex-jsonl"),
    }


_REMOTE_AUTH_VARIABLES = (
    "OPENAI_API_KEY",
    "CODEX_API_KEY",
    "CODEX_ACCESS_TOKEN",
)


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
            raise FileNotFoundError(f"Codex auth seed does not exist: {source}")
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
        if item.get("type") == "agent_message" and isinstance(item.get("text"), str)
    ]
    return messages[-1] if messages else None


def _verify_native_binding(
    server: dict[str, Any], name: str, workspace: Path, path: str | None
) -> None:
    transport = server.get("transport")
    if not isinstance(transport, dict) or transport.get("type") != "stdio":
        raise ValueError(f"native Codex MCP server {name} is not stdio")
    command = transport.get("command")
    args = transport.get("args")
    cwd = transport.get("cwd")
    if (
        not isinstance(command, str)
        or not isinstance(args, list)
        or not all(isinstance(x, str) for x in args)
    ):
        raise ValueError(f"native Codex MCP server {name} has an unverified command")
    expected = shutil.which(name, path=path)
    configured = shutil.which(command, path=path) if os.sep not in command else command
    if (
        Path(command).name != name
        or not expected
        or not configured
        or not Path(configured).is_file()
        or not Path(configured).samefile(expected)
    ):
        raise ValueError(
            f"native Codex MCP server {name} must use the selected {name} executable"
        )
    root = workspace.resolve()
    current = (root / cwd).resolve() if isinstance(cwd, str) else root
    if current != root:
        raise ValueError(f"native Codex MCP server {name} runs outside trial workspace")
    if name == "enola":
        if args:
            raise ValueError("native Enola MCP must use its workspace-default command")
        return
    if name == "hashmarks":
        values = [
            args[index + 1]
            for index, value in enumerate(args[:-1])
            if value == "--workspace"
        ]
        values += [
            value.split("=", 1)[1] for value in args if value.startswith("--workspace=")
        ]
        if (
            len(values) != 1
            or args[-1:] != ["mcp"]
            or (root / values[0]).resolve() != root
        ):
            raise ValueError(
                "native Hashmarks MCP must bind --workspace to the trial repository"
            )
        return
    raise ValueError(f"unsupported native benchmark subject: {name}")


@dataclass(frozen=True)
class CodexAgent:
    model: str | None = None
    reasoning_effort: str | None = None
    native_host: bool = False
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
                "surface": "codex-exec-json",
                "native_host": self.native_host,
            },
        )

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

    def prepare(
        self,
        context: TrialContext,
        exposed_subject: SubjectAdapter | None,
    ) -> Observation:
        exposure = self._exposure(context, exposed_subject)
        if self.native_host:
            return self._prepare_native(context, exposure)
        config = _render_config(
            self.model,
            exposure,
            reasoning_effort=self.reasoning_effort,
        )
        config_path = self._config_path(context)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(config, encoding="utf-8")

        observed = observe_executable(context, "codex")
        payload = dict(observed.payload)
        payload.update(
            {
                "config_sha256": hashlib.sha256(config.encode()).hexdigest(),
                "mcp_exposure": (exposure.semantic_identity if exposure else None),
                "auth_mode": context.environment.get(
                    "BENCHMARK_CODEX_AUTH_MODE",
                    "none",
                ),
                "model": self.model,
                "reasoning_effort": self.reasoning_effort,
            }
        )
        return Observation(
            payload,
            observed.raw,
            observed.measurements,
        )

    def _prepare_native(
        self, context: TrialContext, exposure: McpExposure | None
    ) -> Observation:
        observed = observe_executable(context, "codex")
        config_path = self._config_path(context)
        try:
            raw = config_path.read_bytes()
            config = tomllib.loads(raw.decode("utf-8"))
            model = config.get("model")
            effort = config.get("model_reasoning_effort")
            if not isinstance(model, str) or not model:
                raise ValueError(
                    "native Codex config needs an explicit model for comparison"
                )
            result = run_bounded(
                repository_root=context.workspace,
                argv=("codex", "mcp", "list", "--json"),
                environment=context.environment,
                limits=ProcessLimits(timeout_seconds=30, max_stdout_bytes=1_000_000),
            )
            if result.return_code != 0 or result.timed_out or result.stdout_truncated:
                raise ValueError("native Codex MCP list did not complete")
            servers = json.loads(result.stdout)
            if not isinstance(servers, list):
                raise ValueError("native Codex MCP list was not an array")
            if any(not isinstance(row, dict) for row in servers):
                raise ValueError("native Codex MCP list contains a malformed server")
            names = [row.get("name") for row in servers]
            if any(
                not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", name)
                for name in names
            ) or len(names) != len(set(names)):
                raise ValueError("native Codex MCP names are invalid or duplicated")
            selected = exposure.name if exposure else None
            if selected:
                server = next((row for row in servers if row["name"] == selected), None)
                if not server or server.get("enabled") is not True:
                    raise ValueError(
                        f"native Codex MCP server {selected} is not enabled"
                    )
                _verify_native_binding(
                    server, selected, context.workspace, context.environment.get("PATH")
                )
            (context.control_root / "codex-native-servers.json").write_text(
                json.dumps(
                    {"names": names, "config_sha256": hashlib.sha256(raw).hexdigest()}
                )
            )
            reason = None
            available = bool(observed.payload.get("available"))
        except (
            OSError,
            UnicodeError,
            tomllib.TOMLDecodeError,
            json.JSONDecodeError,
            ValueError,
        ) as exc:
            model = effort = None
            names = []
            reason = str(exc)
            available = False
            raw = b""
        payload = dict(observed.payload)
        payload.update(
            {
                "available": available,
                "reason": reason,
                "auth_mode": "native-host",
                "model": model,
                "reasoning_effort": effort,
                "native_config_sha256": hashlib.sha256(raw).hexdigest()
                if raw
                else None,
                "native_mcp_servers": sorted(names),
                "mcp_exposure": exposure.semantic_identity if exposure else None,
                "observed_identity": {
                    "version": observed.payload.get("version"),
                    "executable_sha256": observed.payload.get("executable_sha256"),
                    "model": model,
                    "reasoning_effort": effort,
                    "native_config_sha256": hashlib.sha256(raw).hexdigest()
                    if raw
                    else None,
                },
            }
        )
        return Observation(payload, observed.raw, observed.measurements)

    def _exec_argv(
        self, prompt: str, names: tuple[str, ...] = (), selected: str | None = None
    ) -> tuple[str, ...]:
        argv = ["codex", "exec", "--json"]
        if self.native_host:
            argv.extend(
                ("--sandbox", "workspace-write", "--approve-for-me", "--ephemeral")
            )
            for name in names:
                if name != selected:
                    argv.extend(("-c", f"mcp_servers.{name}.enabled=false"))
        else:
            argv.append("--full-auto")
        if self.model:
            argv.extend(("--model", self.model))
        argv.append(prompt)
        return tuple(argv)

    def run(
        self,
        context: TrialContext,
        prompt: str,
        exposed_subject: SubjectAdapter | None,
    ) -> Observation:
        exposure = self._exposure(context, exposed_subject)
        names: tuple[str, ...] = ()
        if self.native_host:
            prepared = json.loads(
                (context.control_root / "codex-native-servers.json").read_text()
            )
            if (
                hashlib.sha256(self._config_path(context).read_bytes()).hexdigest()
                != prepared["config_sha256"]
            ):
                return Observation(
                    {
                        "terminal_event": None,
                        "reason": "native Codex config changed during trial",
                    },
                    "",
                )
            names = tuple(prepared["names"])
        result = run_bounded(
            repository_root=context.workspace,
            argv=self._exec_argv(prompt, names, exposure.name if exposure else None),
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
                if event.get("type") in {"turn.completed", "turn.failed", "error"}
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
                terminal and terminal.get("type") in {"turn.completed", "turn.failed"}
            ),
            "final_message": _final_message(events),
            "jsonl_parse_errors": parse_errors,
            "subject_server": subject_server,
            "tool_available": exposure is not None,
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
            "budget_violation": (
                (f"tool calls {tool_calls} exceed max_tool_calls {self.max_tool_calls}")
                if self.max_tool_calls is not None and tool_calls > self.max_tool_calls
                else (
                    f"agent output exceeded max_output_bytes {self.max_output_bytes}"
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
