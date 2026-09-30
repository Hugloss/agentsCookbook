"""Explicit local runtime authority for benchmark participants."""
from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

from benchmarks.harness.suite import SuiteDefinition


RUNTIME_AUTHORITY_ENV_KEYS = (
    "HASHMARKS_BENCH_SOURCE",
    "ENOLA_BENCH_EXECUTABLE",
    "BENCHMARK_CODEX_EXECUTABLE",
    "BENCHMARK_CODEX_HOME",
    "BENCHMARK_OPENCODE_EXECUTABLE",
    "BENCHMARK_OPENCODE_HOME",
    "BENCHMARK_OPENCODE_CONFIG_HOME",
    "BENCHMARK_OPENCODE_AGENT",
)


def required_runtime_authority(
    suite: SuiteDefinition,
    rows: list[dict[str, Any]],
) -> tuple[str, ...]:
    selected_condition_ids = {
        str(row["condition_id"])
        for row in rows
        if isinstance(row, dict) and "condition_id" in row
    }
    conditions = [
        condition
        for condition in suite.experiment["conditions"]
        if condition.get("id") in selected_condition_ids
    ]
    subjects = {str(condition.get("subject")) for condition in conditions}
    agents = {str(condition.get("agent")) for condition in conditions}

    required: set[str] = set()
    if "hashmarks" in subjects:
        required.add("HASHMARKS_BENCH_SOURCE")
    if "enola" in subjects:
        required.add("ENOLA_BENCH_EXECUTABLE")
    if any(
        suite.agents[agent]["adapter"] == "codex"
        for agent in agents
        if agent in suite.agents
    ):
        required.update(
            {
                "BENCHMARK_CODEX_EXECUTABLE",
                "BENCHMARK_CODEX_HOME",
            }
        )
    if any(
        suite.agents[agent]["adapter"] == "opencode-native"
        for agent in agents
        if agent in suite.agents
    ):
        required.update(
            {
                "BENCHMARK_OPENCODE_EXECUTABLE",
                "BENCHMARK_OPENCODE_HOME",
                "BENCHMARK_OPENCODE_CONFIG_HOME",
                "BENCHMARK_OPENCODE_AGENT",
            }
        )
    return tuple(sorted(required))


def transport_runtime_authority(
    source: Mapping[str, str],
    destination: MutableMapping[str, str],
) -> None:
    for name in RUNTIME_AUTHORITY_ENV_KEYS:
        value = source.get(name)
        if value:
            destination[name] = value
