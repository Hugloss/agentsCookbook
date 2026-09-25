"""Codex CLI benchmark agent with structured JSONL evidence."""
from __future__ import annotations

import hashlib
import json
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


def _render_config(model: str | None, exposure: McpExposure | None) -> str:
    lines: list[str] = []
    if model:
        lines.append(f"model = {_toml_string(model)}")
    if exposure is not None:
        lines.extend(
            [
                "",
                f"[mcp_servers.{exposure.name}]",
                f"command = {_toml_string(exposure.command)}",
                "args = [" + ", ".join(_toml_string(value) for value in exposure.args) + "]",
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
    commands = [item for item in items if item.get("type") == "command_execution"]
    changes = [item for item in items if item.get("type") == "file_change"]
    mcp_calls = [item for item in items if item.get("type") == "mcp_tool_call"]
    subject_calls = [
        item for item in mcp_calls if subject_server and item.get("server") == subject_server
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
                json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
            )
    return {
        "event_count": len(events),
        "command_calls": len(commands),
        "file_change_events": len(changes),
        "mcp_calls": len(mcp_calls),
        "subject_mcp_calls": len(subject_calls),
        "subject_tool_invoked": bool(subject_calls),
        "mcp_result_bytes": result_bytes,
        "input_tokens": int(usage.get("input_tokens", 0) or 0),
        "cached_input_tokens": int(usage.get("cached_input_tokens", 0) or 0),
        "output_tokens": int(usage.get("output_tokens", 0) or 0),
        "source_read_observability": "not-authoritatively-exposed-by-codex-jsonl",
    }


def _final_message(events: list[dict[str, Any]]) -> str | None:
    messages = [
        item.get("text")
        for item in _completed_items(events)
        if item.get("type") == "agent_message" and isinstance(item.get("text"), str)
    ]
    return messages[-1] if messages else None


@dataclass(frozen=True)
class CodexAgent:
    model: str | None = None
    timeout_seconds: int = 600

    def identity(self) -> ParticipantIdentity:
        return ParticipantIdentity(
            "codex",
            "coding_agent",
            "runtime-observed",
            {"model": self.model or "host-default", "surface": "codex-exec-json"},
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
        config = _render_config(self.model, exposure)
        config_path = self._config_path(context)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(config, encoding="utf-8")
        observed = observe_executable(context, "codex")
        payload = dict(observed.payload)
        payload.update(
            {
                "config_sha256": hashlib.sha256(config.encode()).hexdigest(),
                "mcp_exposure": exposure.semantic_identity if exposure else None,
            }
        )
        return Observation(payload, observed.raw, observed.measurements)

    def run(
        self,
        context: TrialContext,
        prompt: str,
        exposed_subject: SubjectAdapter | None,
    ) -> Observation:
        exposure = self._exposure(context, exposed_subject)
        result = run_bounded(
            repository_root=context.workspace,
            argv=("codex", "exec", "--json", "--full-auto", prompt),
            environment=context.environment,
            limits=ProcessLimits(
                timeout_seconds=self.timeout_seconds,
                max_stdout_bytes=50_000_000,
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
            "process": result.metrics(),
            "stderr": result.stderr.decode("utf-8", errors="replace"),
        }
        return Observation(
            payload,
            result.stdout.decode("utf-8", errors="replace"),
            metrics,
        )
