"""Compact derived decision evidence for completed benchmark reports."""

from __future__ import annotations

from collections import Counter
from typing import Any


_RUNTIME_PRIMARIES = {
    "runtime",
    "timeout",
    "agent-terminal",
    "contamination",
    "oracle-invalid-or-ambiguous",
}


def _counter(values: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def build_decision_evidence(report: dict[str, Any]) -> dict[str, Any]:
    """Summarize decision-relevant evidence without adding a scoring authority."""

    diagnostics = [
        row
        for row in report.get("diagnostics", [])
        if isinstance(row, dict)
    ]
    runtime_rows = [
        row
        for row in diagnostics
        if row.get("primary") in _RUNTIME_PRIMARIES
    ]
    semantic_rows = [
        row
        for row in report.get("stability", [])
        if isinstance(row, dict)
        and int(row.get("semantic_incorrect", 0) or 0) > 0
    ]

    condition_formats = []
    for condition_id, summary in sorted(
        (report.get("conditions") or {}).items()
    ):
        if not isinstance(summary, dict):
            continue
        contract = summary.get("format_contract")
        if isinstance(contract, dict):
            condition_formats.append(
                {
                    "condition_id": str(condition_id),
                    **contract,
                }
            )

    agent_formats = []
    for agent_id, summary in sorted(
        (report.get("agent_profiles") or {}).items()
    ):
        if not isinstance(summary, dict):
            continue
        contract = summary.get("format_contract")
        if isinstance(contract, dict):
            agent_formats.append(
                {
                    "agent_id": str(agent_id),
                    **contract,
                }
            )

    task_assistance = [
        row
        for row in report.get("task_assistance_evidence", [])
        if isinstance(row, dict)
    ]
    task_signals = [
        str(signal)
        for row in task_assistance
        for signal in row.get("evidence_signals", [])
        if isinstance(signal, str)
    ]

    subject_adoption = [
        row
        for row in report.get("subject_adoption", [])
        if isinstance(row, dict)
    ]
    adoption_states = [
        str(row["state"])
        for row in subject_adoption
        if isinstance(row.get("state"), str)
    ]

    source_read_observability = sorted(
        {
            str(value)
            for summary in (report.get("agent_profiles") or {}).values()
            if isinstance(summary, dict)
            for value in summary.get("source_read_observability", [])
            if isinstance(value, str)
        }
    )
    invocation_unknown = sum(
        int(row.get("invocation_unknown_trials", 0) or 0)
        for row in subject_adoption
    )
    agent_tool_strategy = []
    for agent_id, summary in sorted(
        (report.get("agent_profiles") or {}).items()
    ):
        if not isinstance(summary, dict):
            continue
        strategy = summary.get("tool_strategy")
        if isinstance(strategy, dict):
            agent_tool_strategy.append(
                {
                    "agent_id": str(agent_id),
                    **strategy,
                }
            )

    condition_tool_strategy = []
    for condition_id, summary in sorted(
        (report.get("conditions") or {}).items()
    ):
        if not isinstance(summary, dict):
            continue
        strategy = summary.get("tool_strategy")
        if isinstance(strategy, dict):
            condition_tool_strategy.append(
                {
                    "condition_id": str(condition_id),
                    **strategy,
                }
            )
    partial_tool_strategy_trials = sum(
        int(row.get("partial_observability_trials", 0) or 0)
        for row in agent_tool_strategy
    )

    evidence_signals: list[str] = []
    if runtime_rows:
        evidence_signals.append("runtime-or-host-instability-observed")
    if semantic_rows:
        evidence_signals.append("semantic-misses-observed")
    if any(
        row.get("state") == "strict-contract-saturated-noncompliant"
        for row in agent_formats
    ):
        evidence_signals.append("strict-format-saturation-observed")
    if "configured-never-invoked" in adoption_states:
        evidence_signals.append("configured-subject-never-invoked")
    if task_signals:
        evidence_signals.extend(sorted(set(task_signals)))
    if any(
        value.startswith("not-authoritatively-exposed")
        for value in source_read_observability
    ):
        evidence_signals.append("source-read-archaeology-unavailable")
    if invocation_unknown:
        evidence_signals.append("subject-invocation-partially-unobserved")
    if partial_tool_strategy_trials:
        evidence_signals.append("native-tool-strategy-partially-observed")

    return {
        "schema": "agents-cookbook-benchmark-decision-evidence.v1",
        "authority": {
            "derived_only": True,
            "ranking_performed": False,
            "recommendation_performed": False,
            "source": "report.json",
        },
        "campaign": {
            "expected_trials": report.get("expected_trials"),
            "observed_trials": report.get("observed_trials"),
            "status_counts": report.get("status_counts", {}),
            "qualification": report.get("campaign_qualification", {}),
        },
        "surfaces": {
            "runtime": {
                "trials": len(runtime_rows),
                "tasks": sorted(
                    {
                        str(row["task_id"])
                        for row in runtime_rows
                        if isinstance(row.get("task_id"), str)
                    }
                ),
                "primary_counts": _counter(
                    [
                        str(row["primary"])
                        for row in runtime_rows
                        if isinstance(row.get("primary"), str)
                    ]
                ),
                "reason_codes": _counter(
                    [
                        str(row["reason_code"])
                        for row in runtime_rows
                        if isinstance(row.get("reason_code"), str)
                    ]
                ),
                "stages": _counter(
                    [
                        str(row["stage"])
                        for row in runtime_rows
                        if isinstance(row.get("stage"), str)
                    ]
                ),
            },
            "semantic": {
                "rows": [
                    {
                        key: row.get(key)
                        for key in (
                            "task_id",
                            "agent_id",
                            "subject_id",
                            "state",
                            "valid_outcomes",
                            "gradeable_outcomes",
                            "semantic_correct",
                            "semantic_incorrect",
                        )
                    }
                    for row in semantic_rows
                ],
            },
            "strict_format": {
                "agent_profiles": agent_formats,
                "conditions": condition_formats,
            },
            "assistance": {
                "subject_adoption": subject_adoption,
                "paired_summary": report.get("paired_assistance_summary", []),
                "usage_summary": report.get(
                    "paired_assistance_usage_summary",
                    [],
                ),
                "task_signal_counts": _counter(task_signals),
                "task_evidence": task_assistance,
            },
            "tool_strategy": {
                "agent_profiles": agent_tool_strategy,
                "conditions": condition_tool_strategy,
            },
        },
        "evidence_gaps": {
            "source_read_observability": source_read_observability,
            "subject_invocation_unknown_trials": invocation_unknown,
            "tool_strategy_partial_trials": partial_tool_strategy_trials,
        },
        "evidence_signals": sorted(set(evidence_signals)),
    }
