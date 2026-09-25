"""Adapter registry for frozen benchmark definitions."""
from __future__ import annotations

import sys
from typing import Any

from benchmarks.adapters.codex import CodexAgent
from benchmarks.adapters.enola import EnolaSubject
from benchmarks.adapters.hashmarks import HashmarksSubject
from benchmarks.adapters.oracles import CommandOracle, ExpectedJsonOracle
from benchmarks.adapters.subjects import NoneSubject


class AdapterConfigurationError(ValueError):
    pass


def build_subject(definition: dict[str, Any]):
    adapter = definition["adapter"]
    config = definition.get("configuration", {})
    if adapter == "none":
        return NoneSubject()
    if adapter == "hashmarks":
        return HashmarksSubject(
            timeout_seconds=int(config.get("timeout_seconds", 120))
        )
    if adapter == "enola":
        return EnolaSubject(
            timeout_seconds=int(config.get("timeout_seconds", 180))
        )
    raise AdapterConfigurationError(f"unknown subject adapter: {adapter}")


def build_agent(definition: dict[str, Any], *, budgets: dict[str, Any]):
    adapter = definition["adapter"]
    config = definition.get("configuration", {})
    if adapter == "codex":
        model = config.get("model")
        if model is not None and not isinstance(model, str):
            raise AdapterConfigurationError("codex model must be a string or null")
        return CodexAgent(
            model=model,
            timeout_seconds=min(
                int(config.get("timeout_seconds", budgets["timeout_seconds"])),
                int(budgets["timeout_seconds"]),
            ),
            max_output_bytes=int(budgets.get("max_output_bytes", 50_000_000)),
            max_tool_calls=(
                int(budgets["max_tool_calls"])
                if "max_tool_calls" in budgets
                else None
            ),
        )
    raise AdapterConfigurationError(f"unknown agent adapter: {adapter}")


def build_oracle(definition: dict[str, Any], *, timeout_seconds: int):
    adapter = definition["adapter"]
    identity = definition["identity"]
    config = definition["configuration"]
    if adapter == "expected-json":
        expected = config.get("expected")
        if not isinstance(expected, dict):
            raise AdapterConfigurationError(
                "expected-json oracle requires object configuration.expected"
            )
        return ExpectedJsonOracle(
            str(identity["id"]),
            str(identity["version"]),
            expected,
        )
    if adapter == "command":
        health = config.get("health_argv")
        grade = config.get("grade_argv")
        if not (
            isinstance(health, list)
            and health
            and all(isinstance(value, str) and value for value in health)
            and isinstance(grade, list)
            and grade
            and all(isinstance(value, str) and value for value in grade)
        ):
            raise AdapterConfigurationError(
                "command oracle requires non-empty health_argv and grade_argv"
            )
        expand = lambda values: tuple(
            sys.executable if value == "{python}" else value for value in values
        )
        return CommandOracle(
            str(identity["id"]),
            str(identity["version"]),
            expand(health),
            expand(grade),
            timeout_seconds=min(
                int(config.get("timeout_seconds", timeout_seconds)),
                timeout_seconds,
            ),
        )
    raise AdapterConfigurationError(f"unknown oracle adapter: {adapter}")
