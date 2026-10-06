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


def _assistance_funnel(
    subject_adoption: list[dict[str, Any]],
    usage_summary: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    usage = {
        (
            str(row.get("agent_id")),
            str(row.get("subject_id")),
            str(row.get("invocation_state")),
        ): row
        for row in usage_summary
        if isinstance(row, dict)
    }

    def conditional(
        agent_id: str,
        subject_id: str,
        state: str,
    ) -> dict[str, Any]:
        row = usage.get((agent_id, subject_id, state), {})
        transitions = row.get("transitions")
        if not isinstance(transitions, dict):
            transitions = {}
        return {
            "pairs": int(row.get("total_pairs", 0) or 0),
            "subject_mcp_calls": int(row.get("subject_mcp_calls", 0) or 0),
            "transitions": {
                name: int(transitions.get(name, 0) or 0)
                for name in ("gain", "preserved", "unresolved", "regression")
            },
        }

    output: list[dict[str, Any]] = []
    for row in subject_adoption:
        agent_id = str(row.get("agent_id"))
        subject_id = str(row.get("subject_id"))
        trials = int(row.get("trials", 0) or 0)
        available = int(row.get("available_trials", 0) or 0)
        configured = int(row.get("configured_trials", 0) or 0)
        observed = int(row.get("invocation_observed_trials", 0) or 0)
        invoked = int(row.get("invoked_trials", 0) or 0)
        not_invoked = int(row.get("not_invoked_trials", 0) or 0)
        unknown = int(row.get("invocation_unknown_trials", 0) or 0)
        output.append(
            {
                "agent_id": agent_id,
                "subject_id": subject_id,
                "availability": {
                    "trials": trials,
                    "available_trials": available,
                    "rate": available / trials if trials else None,
                },
                "configuration": {
                    "configured_trials": configured,
                    "rate": configured / trials if trials else None,
                },
                "adoption": {
                    "observed_trials": observed,
                    "invoked_trials": invoked,
                    "not_invoked_trials": not_invoked,
                    "unknown_trials": unknown,
                    "rate": invoked / observed if observed else None,
                },
                "routing_timing": {
                    "first_choice_trials": int(
                        row.get("first_choice_trials", 0) or 0
                    ),
                    "late_rescue_trials": int(
                        row.get("late_rescue_trials", 0) or 0
                    ),
                    "never_invoked_trials": int(
                        row.get("never_invoked_timing_trials", 0) or 0
                    ),
                    "unknown_trials": int(
                        row.get("routing_timing_unknown_trials", 0) or 0
                    ),
                    "first_choice_rate": row.get("first_choice_rate"),
                },
                "usefulness_when_invoked": conditional(
                    agent_id, subject_id, "invoked"
                ),
                "condition_outcomes_when_not_invoked": conditional(
                    agent_id, subject_id, "not-invoked"
                ),
                "condition_outcomes_when_invocation_unknown": conditional(
                    agent_id, subject_id, "unknown"
                ),
                "interpretation": {
                    "overall_paired_summary": (
                        "condition effect; combines invoked and non-invoked assisted pairs"
                    ),
                    "usefulness_when_invoked": (
                        "descriptive outcome transitions only where subject use was observed"
                    ),
                    "not_invoked": (
                        "cannot be attributed to the subject tool because it was not invoked"
                    ),
                },
            }
        )
    return output


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
    usage_summary = [
        row
        for row in report.get("paired_assistance_usage_summary", [])
        if isinstance(row, dict)
    ]
    adoption_states = [
        str(row["state"])
        for row in subject_adoption
        if isinstance(row.get("state"), str)
    ]
    campaign_qualification = report.get("campaign_qualification", {})
    subject_exposure = (
        campaign_qualification.get("subject_exposure", {})
        if isinstance(campaign_qualification, dict)
        else {}
    )

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
        int(row.get("late_rescue_trials", 0) or 0) > 0
        for row in subject_adoption
    ):
        evidence_signals.append("late-rescue-observed")
    if any(
        row.get("state") == "strict-contract-saturated-noncompliant"
        for row in agent_formats
    ):
        evidence_signals.append("strict-format-saturation-observed")
    if "configured-never-invoked" in adoption_states:
        evidence_signals.append("configured-subject-never-invoked")
    if isinstance(subject_exposure, dict) and subject_exposure.get("status") == "FAIL":
        evidence_signals.append("mandatory-subject-exposure-failed")
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
        "schema": "agents-cookbook-benchmark-decision-evidence.v3",
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
        "decision_summary": report.get("decision_summary", {}),
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
                "subject_exposure_qualification": subject_exposure,
                "subject_adoption": subject_adoption,
                "paired_summary": report.get("paired_assistance_summary", []),
                "usage_summary": usage_summary,
                "funnel": _assistance_funnel(subject_adoption, usage_summary),
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
