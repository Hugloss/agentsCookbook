"""Aggregate complete benchmark receipts without ranking products."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any

from benchmarks.adapters.oracles import (
    REPOSITORY_LOCATION_NORMALIZATION_POLICY,
    REPOSITORY_LOCATION_SCORING_POLICY,
    score_repository_location,
)
from benchmarks.harness.bundle import verify_bundle
from benchmarks.harness.campaign_authority import (
    CampaignAuthorityError,
    read_launch_claims,
    read_campaign,
)
from benchmarks.harness.suite import SuiteDefinition
from benchmarks.harness.identity import digest, execution_task_contract


class ReportError(ValueError):
    pass


_VALID_OUTCOMES = {"PASS", "FAIL", "NO_QUALIFYING_DEFECT"}
_NUMERIC_AGENT_METRICS = (
    "duration_ms",
    "command_calls",
    "tool_calls",
    "mcp_calls",
    "subject_mcp_calls",
    "mcp_result_bytes",
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
)


def _receipts(results_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not results_root.exists():
        return rows
    for directory in sorted(path for path in results_root.iterdir() if path.is_dir()):
        if directory.name.startswith("."):
            continue
        valid, reason = verify_bundle(directory)
        if not valid:
            raise ReportError(f"invalid published result bundle {directory}: {reason}")
        try:
            value = json.loads((directory / "result.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ReportError(
                f"cannot load complete receipt {directory}: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise ReportError(f"receipt is not an object: {directory}")
        rows.append(value)
    return rows


def _condition_id(receipt: dict[str, Any]) -> str:
    value = receipt.get("condition", {}).get("id")
    if not isinstance(value, str) or not value:
        raise ReportError("receipt has no condition id")
    return value


def _task_id(receipt: dict[str, Any]) -> str:
    value = receipt.get("task", {}).get("id")
    if not isinstance(value, str) or not value:
        raise ReportError("receipt has no task id")
    return value


def _agent_metric(receipt: dict[str, Any], name: str) -> int | float | None:
    value = receipt.get("measurements", {}).get("agent", {}).get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _oracle_bool(receipt: dict[str, Any], name: str) -> bool | None:
    value = receipt.get("scoring", {}).get("oracle_grade", {}).get(name)
    return value if isinstance(value, bool) else None


def _semantic_success(receipt: dict[str, Any]) -> bool | None:
    value = _oracle_bool(receipt, "semantic_success")
    if value is not None:
        return value
    if receipt.get("status") in _VALID_OUTCOMES:
        return receipt.get("status") == "PASS"
    return None


def _semantic_gradeable(receipt: dict[str, Any]) -> bool:
    value = _oracle_bool(receipt, "semantic_gradeable")
    if value is not None:
        return value
    return receipt.get("status") in _VALID_OUTCOMES


def _replicate_id(receipt: dict[str, Any]) -> int:
    """Return the frozen paired replicate identifier.

    The historical receipt field is named seed. Native agent adapters do not
    transport it as a provider/model sampling seed, so reports must not imply
    deterministic inference from this value.
    """
    execution = receipt["execution"]
    return int(execution.get("replicate_id", execution.get("seed")))


def _metric_summary(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for name in _NUMERIC_AGENT_METRICS:
        values = [
            value for row in receipts if (value := _agent_metric(row, name)) is not None
        ]
        metrics[name] = {
            "observations": len(values),
            "mean": mean(values) if values else None,
            "total": sum(values) if values else None,
        }
    return metrics


def _tool_strategy_summary(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    observability = Counter()
    tool_names = Counter()
    first_subject_ordinals: list[int | float] = []
    sequence_lengths: list[int] = []
    observed_sequences = 0

    for row in receipts:
        agent = row.get("measurements", {}).get("agent", {})
        if not isinstance(agent, dict):
            continue

        state = agent.get("tool_strategy_observability")
        if isinstance(state, str) and state:
            observability[state] += 1

        counts = agent.get("tool_name_counts")
        if isinstance(counts, dict):
            for name, value in counts.items():
                if (
                    isinstance(name, str)
                    and name
                    and isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and value >= 0
                ):
                    tool_names[name] += int(value)

        sequence = agent.get("tool_sequence")
        if isinstance(sequence, list) and all(
            isinstance(name, str) and name for name in sequence
        ):
            observed_sequences += 1
            sequence_lengths.append(len(sequence))

        ordinal = agent.get("subject_first_tool_call_ordinal")
        if (
            isinstance(ordinal, (int, float))
            and not isinstance(ordinal, bool)
            and ordinal >= 1
        ):
            first_subject_ordinals.append(ordinal)

    partial = sum(
        count
        for state, count in observability.items()
        if "partial" in state
    )
    return {
        "observability_counts": dict(sorted(observability.items())),
        "partial_observability_trials": partial,
        "tool_name_counts": dict(sorted(tool_names.items())),
        "sequence_observations": observed_sequences,
        "sequence_length": {
            "observations": len(sequence_lengths),
            "mean": mean(sequence_lengths) if sequence_lengths else None,
            "median": median(sequence_lengths) if sequence_lengths else None,
            "min": min(sequence_lengths) if sequence_lengths else None,
            "max": max(sequence_lengths) if sequence_lengths else None,
        },
        "subject_first_tool_call_ordinal": {
            "observations": len(first_subject_ordinals),
            "mean": (
                mean(first_subject_ordinals)
                if first_subject_ordinals
                else None
            ),
            "median": (
                median(first_subject_ordinals)
                if first_subject_ordinals
                else None
            ),
            "min": min(first_subject_ordinals) if first_subject_ordinals else None,
            "max": max(first_subject_ordinals) if first_subject_ordinals else None,
        },
        "full_order_retained_in_receipts": True,
        "arguments_or_source_contents_included": False,
    }


def _format_contract_summary(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    observed: list[tuple[bool, bool | None, str | None]] = []
    for row in receipts:
        grade = row.get("scoring", {}).get("oracle_grade", {})
        compliant = grade.get("format_compliant")
        if not isinstance(compliant, bool):
            continue
        gradeable = grade.get("semantic_gradeable")
        answer_shape = grade.get("answer_shape")
        observed.append(
            (
                compliant,
                gradeable if isinstance(gradeable, bool) else None,
                answer_shape if isinstance(answer_shape, str) else None,
            )
        )

    shapes = Counter(shape for _compliant, _gradeable, shape in observed if shape)
    compliant_count = sum(compliant for compliant, _gradeable, _shape in observed)
    gradeable = [
        value
        for _compliant, value, _shape in observed
        if isinstance(value, bool)
    ]
    if not observed:
        state = "not-observed"
        interpretation = "no strict format evidence is available"
    elif compliant_count == len(observed):
        state = "strict-contract-compliant"
        interpretation = "all observed answers satisfy the strict output contract"
    elif (
        compliant_count == 0
        and len(gradeable) == len(observed)
        and all(gradeable)
    ):
        state = "strict-contract-saturated-noncompliant"
        interpretation = (
            "all observed answers violate the strict output contract while remaining "
            "semantically gradeable; inspect answer_shapes instead of treating format "
            "noncompliance as semantic failure"
        )
    else:
        state = "mixed"
        interpretation = (
            "strict output compliance varies across observed answers; inspect "
            "answer_shapes and semantic gradeability separately"
        )
    return {
        "state": state,
        "observations": len(observed),
        "compliant": compliant_count,
        "noncompliant": len(observed) - compliant_count,
        "answer_shapes": dict(sorted(shapes.items())),
        "semantic_gradeable_observations": len(gradeable),
        "semantic_gradeable": sum(gradeable),
        "interpretation": interpretation,
    }


def _aggregate_condition(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = Counter(str(row.get("status")) for row in receipts)
    valid = [row for row in receipts if row.get("status") in _VALID_OUTCOMES]
    passed = [row for row in valid if row.get("status") == "PASS"]
    tool_available = [
        row
        for row in receipts
        if row.get("authority", {}).get("subject", {}).get("available") is True
        and row.get("measurements", {}).get("agent", {}).get("subject_tool_configured")
        is True
        and isinstance(
            row.get("measurements", {}).get("agent", {}).get("subject_tool_invoked"),
            bool,
        )
    ]
    invoked = [
        row
        for row in tool_available
        if row.get("measurements", {}).get("agent", {}).get("subject_tool_invoked")
        is True
    ]
    observability = sorted(
        {
            value
            for row in receipts
            if isinstance(
                (
                    value := row.get("measurements", {})
                    .get("agent", {})
                    .get("source_read_observability")
                ),
                str,
            )
        }
    )
    semantic_rows = [
        value
        for row in valid
        if (value := _oracle_bool(row, "semantic_success")) is not None
    ]
    gradeable_rows = [
        value
        for row in valid
        if (value := _oracle_bool(row, "semantic_gradeable")) is not None
    ]
    semantic_statuses = Counter(
        value
        for row in valid
        if isinstance(
            (
                value := row.get("scoring", {})
                .get("oracle_grade", {})
                .get("semantic_status")
            ),
            str,
        )
    )
    format_rows = [
        value
        for row in valid
        if (value := _oracle_bool(row, "format_compliant")) is not None
    ]
    return {
        "trials": len(receipts),
        "valid_outcomes": len(valid),
        "statuses": dict(sorted(statuses.items())),
        "task_success_rate": len(passed) / len(valid) if valid else None,
        "semantic_success_rate": (
            sum(semantic_rows) / len(semantic_rows) if semantic_rows else None
        ),
        "semantic_success_denominator": len(semantic_rows),
        "semantic_gradeable_rate": (
            sum(gradeable_rows) / len(gradeable_rows) if gradeable_rows else None
        ),
        "semantic_gradeable_denominator": len(gradeable_rows),
        "semantic_statuses": dict(sorted(semantic_statuses.items())),
        "format_compliance_rate": (
            sum(format_rows) / len(format_rows) if format_rows else None
        ),
        "format_compliance_denominator": len(format_rows),
        "format_contract": _format_contract_summary(valid),
        "subject_tool_adoption_rate": (
            len(invoked) / len(tool_available) if tool_available else None
        ),
        "subject_tool_adoption_denominator": len(tool_available),
        "source_read_observability": observability,
        "tool_strategy": _tool_strategy_summary(receipts),
        "metrics": _metric_summary(receipts),
        "valid_outcome_metrics": _metric_summary(valid),
    }


def _subject_adoption_summary(
    receipts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Describe whether configured repository-intelligence subjects were used."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for receipt in receipts:
        subject = receipt.get("condition", {}).get("subject_definition", {}).get("id")
        agent = receipt.get("condition", {}).get("agent_definition", {}).get("id")
        if not isinstance(subject, str) or subject == "none":
            continue
        if not isinstance(agent, str) or not agent:
            continue
        grouped[(agent, subject)].append(receipt)

    rows: list[dict[str, Any]] = []
    for (agent, subject), group in sorted(grouped.items()):
        available = [
            row
            for row in group
            if row.get("authority", {}).get("subject", {}).get("available") is True
        ]
        configured = [
            row
            for row in group
            if row.get("measurements", {}).get("agent", {}).get(
                "subject_tool_configured"
            )
            is True
        ]
        observed = [
            row
            for row in group
            if isinstance(
                row.get("measurements", {}).get("agent", {}).get(
                    "subject_tool_invoked"
                ),
                bool,
            )
        ]
        invoked = [
            row
            for row in observed
            if row.get("measurements", {}).get("agent", {}).get(
                "subject_tool_invoked"
            )
            is True
        ]
        not_invoked = len(observed) - len(invoked)
        calls = [
            value
            for row in group
            if (
                value := _agent_metric(row, "subject_mcp_calls")
            )
            is not None
        ]
        tools = sorted(
            {
                name
                for row in group
                for name in (
                    row.get("measurements", {})
                    .get("agent", {})
                    .get("subject_tool_names", [])
                )
                if isinstance(name, str) and name
            }
        )
        output_contract_failures = sum(
            row.get("scoring", {})
            .get("oracle_grade", {})
            .get("format_compliant")
            is False
            and row.get("scoring", {})
            .get("oracle_grade", {})
            .get("semantic_gradeable")
            is False
            for row in group
        )
        semantic_incorrect = sum(
            row.get("scoring", {})
            .get("oracle_grade", {})
            .get("semantic_status")
            == "INCORRECT"
            for row in group
        )
        if not available:
            state = "subject-unavailable"
        elif not observed:
            state = "invocation-unobserved"
        elif not invoked:
            state = "configured-never-invoked"
        elif len(invoked) == len(observed):
            state = "invoked-all-observed"
        else:
            state = "invoked-some-observed"
        rows.append(
            {
                "agent_id": agent,
                "subject_id": subject,
                "trials": len(group),
                "available_trials": len(available),
                "configured_trials": len(configured),
                "invocation_observed_trials": len(observed),
                "invoked_trials": len(invoked),
                "not_invoked_trials": not_invoked,
                "invocation_unknown_trials": len(group) - len(observed),
                "subject_mcp_calls": sum(calls),
                "subject_tool_names": tools,
                "output_contract_failures": output_contract_failures,
                "semantic_incorrect_trials": semantic_incorrect,
                "status_counts": dict(
                    sorted(Counter(str(row.get("status")) for row in group).items())
                ),
                "state": state,
            }
        )
    return rows


def _agent_id(receipt: dict[str, Any]) -> str:
    value = receipt.get("condition", {}).get("agent_definition", {}).get("id")
    if not isinstance(value, str) or not value:
        raise ReportError("receipt has no frozen agent id")
    return value


def _subject_id(receipt: dict[str, Any]) -> str:
    value = receipt.get("condition", {}).get("subject_definition", {}).get("id")
    if not isinstance(value, str) or not value:
        raise ReportError("receipt has no frozen subject id")
    return value


def _comparison_identity(receipt: dict[str, Any]) -> dict[str, Any]:
    """Runtime authority shared by conditions; trial MCP wiring is excluded."""
    agent = receipt.get("authority", {}).get("agent", {})
    observed = agent.get("observed", {})
    if not isinstance(observed, dict):
        observed = {}
    adapter = receipt["condition"]["agent_definition"]["adapter"]
    common = {
        "adapter": adapter,
        "version": observed.get("version"),
        "executable_sha256": observed.get("executable_sha256"),
        "auth_mode": observed.get("auth_mode"),
        "model": observed.get("model"),
    }
    if adapter == "opencode-native":
        common.update(
            provider=observed.get("provider"),
            native_config_sha256=observed.get("native_config_sha256"),
        )
    elif adapter == "codex":
        common["reasoning_effort"] = observed.get("reasoning_effort")
        common["native_config_sha256"] = observed.get("native_config_sha256")
    return common


def validate_comparability(receipts: list[dict[str, Any]]) -> None:
    _check_comparable_agents(receipts)
    _check_comparable_evidence(receipts)
    _check_comparable_localization_scoring(receipts)
    _check_localization_grades(receipts)


def _task_agent_authority(receipts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    identities = {
        (_task_id(receipt), _agent_id(receipt)): _comparison_identity(receipt)
        for receipt in receipts
    }
    return [
        {"task_id": task_id, "agent_id": agent_id, **identity}
        for (task_id, agent_id), identity in sorted(identities.items())
    ]


def _check_localization_grades(receipts: list[dict[str, Any]]) -> None:
    for receipt in receipts:
        if receipt.get("status") not in _VALID_OUTCOMES:
            continue
        task = receipt.get("task", {})
        if task.get("oracle", {}).get("adapter") != "repository-location-json":
            continue
        grade = receipt.get("scoring", {}).get("oracle_grade")
        declared = receipt.get("authority", {}).get("oracle", {}).get("declared", {})
        policy = declared.get("provenance", {})
        observed = receipt.get("execution", {}).get("location_observation")
        if not isinstance(grade, dict) or not all(
            isinstance(grade.get(key), bool)
            for key in ("semantic_success", "semantic_gradeable", "format_compliant")
        ):
            raise ReportError("valid localization receipt has incomplete oracle grade")
        if (
            grade.get("semantic_status") not in {"CORRECT", "INCORRECT", "UNSCORABLE"}
            or grade.get("normalization_policy") != policy.get("normalization_policy")
            or grade.get("scoring_policy") != policy.get("scoring_policy")
            or policy.get("normalization_policy")
            != REPOSITORY_LOCATION_NORMALIZATION_POLICY
            or policy.get("scoring_policy") != REPOSITORY_LOCATION_SCORING_POLICY
            or grade.get("expected") != task["oracle"]["configuration"]["expected"]
            or grade.get("semantic_success")
            != (grade.get("semantic_status") == "CORRECT")
            or grade.get("semantic_gradeable")
            != (grade.get("semantic_status") != "UNSCORABLE")
            or not isinstance(observed, dict)
            or observed.get("normalization_policy")
            != REPOSITORY_LOCATION_NORMALIZATION_POLICY
            or grade
            != score_repository_location(
                observed, expected=task["oracle"]["configuration"]["expected"]
            )
            or receipt["status"] != ("PASS" if grade.get("passed") else "FAIL")
        ):
            raise ReportError(
                "valid localization receipt has inconsistent oracle grade"
            )


def _check_comparable_localization_scoring(
    receipts: list[dict[str, Any]],
) -> None:
    policies = {
        value
        for receipt in receipts
        if isinstance(
            (
                value := receipt.get("scoring", {})
                .get("oracle_grade", {})
                .get("scoring_policy")
            ),
            str,
        )
    }
    if len(policies) > 1:
        raise ReportError(
            "mixed localization scoring policy; use separate result campaigns"
        )


def _check_comparable_agents(receipts: list[dict[str, Any]]) -> None:
    global_identities: dict[str, dict[str, Any]] = {}
    task_identities: dict[tuple[str, str], dict[str, Any]] = {}
    for receipt in receipts:
        agent = _agent_id(receipt)
        identity = _comparison_identity(receipt)
        if not any(
            identity.get(key) is not None
            for key in ("version", "executable_sha256", "model", "native_config_sha256")
        ):
            continue
        global_identity = {
            key: value
            for key, value in identity.items()
            if key != "native_config_sha256"
        }
        prior_global = global_identities.setdefault(agent, global_identity)
        if prior_global != global_identity:
            raise ReportError(
                f"mixed observed runtime authority for agent {agent}; "
                "use separate result campaigns"
            )
        task_key = (_task_id(receipt), agent)
        prior_task = task_identities.setdefault(task_key, identity)
        if prior_task != identity:
            raise ReportError(
                f"mixed native config authority for task {task_key[0]} / {agent}; "
                "paired conditions are not comparable"
            )


def _check_comparable_evidence(receipts: list[dict[str, Any]]) -> None:
    if not receipts:
        return
    for field in ("harness",):
        baseline = receipts[0].get("authority", {}).get(field)
        if any(
            receipt.get("authority", {}).get(field) != baseline
            for receipt in receipts[1:]
        ):
            raise ReportError(f"mixed {field} authority; use separate result campaigns")
    environments: dict[str, Any] = {}
    subjects: dict[tuple[str, str, str], Any] = {}
    subject_executables: dict[str, str] = {}
    for receipt in receipts:
        agent = _agent_id(receipt)
        environment = receipt.get("authority", {}).get("environment")
        if agent in environments and environments[agent] != environment:
            raise ReportError(
                f"mixed environment authority for agent {agent}; "
                "use separate result campaigns"
            )
        environments[agent] = environment
        authority = receipt.get("authority", {}).get("subject", {})
        if authority.get("available") is not True:
            continue
        subject = (_task_id(receipt), agent, _subject_id(receipt))
        observed = authority.get("observed")
        native = (
            observed.get("native_subject_identity")
            if isinstance(observed, dict)
            else None
        )
        executable_hash = (
            native.get("executable_sha256") if isinstance(native, dict) else None
        )
        if isinstance(executable_hash, str):
            subject_id = subject[2]
            if (
                subject_id in subject_executables
                and subject_executables[subject_id] != executable_hash
            ):
                raise ReportError(
                    f"mixed observed subject authority for {subject_id}; "
                    "use separate result campaigns"
                )
            subject_executables[subject_id] = executable_hash
        comparable_observed = observed
        if isinstance(observed, dict) and "native_subject_identity" in observed:
            exposure = observed.get("mcp_exposure") or {}
            comparable_observed = {
                "source": observed.get("source"),
                "subject": observed.get("subject"),
                "native_subject_identity": observed.get("native_subject_identity"),
                "native_config_sha256": observed.get("native_config_sha256"),
                "workspace_binding": observed.get("workspace_binding"),
                "mcp_semantic_identity": (
                    exposure.get("semantic_identity")
                    if isinstance(exposure, dict)
                    else None
                ),
            }
        if subject in subjects and subjects[subject] != comparable_observed:
            raise ReportError(
                f"mixed observed subject authority for {subject}; "
                "use separate result campaigns"
            )
        subjects[subject] = comparable_observed


def _pair_key(receipt: dict[str, Any]) -> tuple[str, str, int, int]:
    execution = receipt["execution"]
    agent_id = _agent_id(receipt)
    return (
        _task_id(receipt),
        agent_id,
        int(execution["trial_index"]),
        _replicate_id(receipt),
    )


def _assistance_transition(
    baseline: dict[str, Any],
    assisted: dict[str, Any],
) -> str | None:
    if not _semantic_gradeable(baseline) or not _semantic_gradeable(assisted):
        return None
    left = _semantic_success(baseline)
    right = _semantic_success(assisted)
    if left is None or right is None:
        return None
    if not left and right:
        return "gain"
    if left and right:
        return "preserved"
    if not left and not right:
        return "unresolved"
    return "regression"


def _pair_input_id(receipt: dict[str, Any]) -> str:
    authority = receipt.get("authority", {})
    return digest(
        {
            "task": execution_task_contract(receipt["task"]),
            "agent": _comparison_identity(receipt),
            "harness": authority.get("harness"),
            "environment": authority.get("environment"),
            "mutation": authority.get("mutation"),
            "admitted_state": receipt.get("execution", {}).get("admitted_state_sha256"),
            "replicate_id": _replicate_id(receipt),
        }
    )


def classify_assistance_pair(
    baseline: dict[str, Any], assisted: dict[str, Any]
) -> str | None:
    """Use the report's evidence contract for both live and final pair summaries."""
    if (
        baseline.get("status") not in _VALID_OUTCOMES
        or assisted.get("status") not in _VALID_OUTCOMES
    ):
        return None
    if _pair_input_id(baseline) != _pair_input_id(assisted):
        raise ReportError(f"paired non-subject authority differs for {_pair_key(assisted)}")
    return _assistance_transition(baseline, assisted)


def _paired_assistance(receipts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bare: dict[tuple[str, str, int, int], dict[str, Any]] = {}
    assisted: list[dict[str, Any]] = []
    for receipt in receipts:
        if receipt.get("status") not in _VALID_OUTCOMES:
            continue
        adapter = (
            receipt.get("condition", {}).get("subject_definition", {}).get("adapter")
        )
        if adapter == "none":
            key = _pair_key(receipt)
            if key in bare:
                raise ReportError(f"multiple bare executions for pair {key}")
            bare[key] = receipt
        else:
            assisted.append(receipt)

    rows: list[dict[str, Any]] = []
    for receipt in assisted:
        key = _pair_key(receipt)
        baseline = bare.get(key)
        if baseline is None:
            continue
        pair_input = _pair_input_id(baseline)
        transition = classify_assistance_pair(baseline, receipt)
        row: dict[str, Any] = {
            "task_id": key[0],
            "agent_id": key[1],
            "trial_index": key[2],
            "replicate_id": key[3],
            **({"seed": key[3]} if "seed" in receipt["execution"] else {}),
            "condition_id": _condition_id(receipt),
            "subject_id": receipt["condition"]["subject_definition"]["id"],
            "pair_input_id": pair_input,
            "bare_status": baseline["status"],
            "assisted_status": receipt["status"],
            "task_success_delta": (
                int(receipt["status"] == "PASS") - int(baseline["status"] == "PASS")
            ),
            "assistance_transition": transition,
        }
        invoked = (
            receipt.get("measurements", {})
            .get("agent", {})
            .get("subject_tool_invoked")
        )
        row["subject_tool_invoked"] = invoked if isinstance(invoked, bool) else None
        configured = (
            receipt.get("measurements", {})
            .get("agent", {})
            .get("subject_tool_configured")
        )
        row["subject_tool_configured"] = (
            configured if isinstance(configured, bool) else None
        )
        tool_names = (
            receipt.get("measurements", {})
            .get("agent", {})
            .get("subject_tool_names")
        )
        row["subject_tool_names"] = sorted(
            {
                name
                for name in tool_names
                if isinstance(name, str) and name
            }
        ) if isinstance(tool_names, list) else []
        subject_calls = _agent_metric(receipt, "subject_mcp_calls")
        row["subject_mcp_calls"] = subject_calls
        for metric in (
            "duration_ms",
            "command_calls",
            "tool_calls",
            "mcp_calls",
            "input_tokens",
            "output_tokens",
        ):
            left = _agent_metric(baseline, metric)
            right = _agent_metric(receipt, metric)
            row[f"{metric}_delta"] = (
                right - left if left is not None and right is not None else None
            )
        rows.append(row)
    return sorted(
        rows,
        key=lambda row: (
            str(row["task_id"]),
            str(row["agent_id"]),
            int(row["trial_index"]),
            str(row["condition_id"]),
        ),
    )


def _paired_assistance_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for row in rows:
        transition = row.get("assistance_transition")
        if isinstance(transition, str):
            grouped[(str(row["agent_id"]), str(row["subject_id"]))][transition] += 1
    return [
        {
            "agent_id": key[0],
            "subject_id": key[1],
            "total_pairs": sum(counts.values()),
            "transitions": {
                name: counts.get(name, 0)
                for name in ("gain", "preserved", "unresolved", "regression")
            },
        }
        for key, counts in sorted(grouped.items())
    ]


def _paired_assistance_usage_summary(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        invoked = row.get("subject_tool_invoked")
        state = (
            "invoked"
            if invoked is True
            else "not-invoked"
            if invoked is False
            else "unknown"
        )
        grouped[
            (str(row["agent_id"]), str(row["subject_id"]), state)
        ].append(row)

    summaries: list[dict[str, Any]] = []
    for (agent_id, subject_id, state), group in sorted(grouped.items()):
        transitions = Counter(
            str(row["assistance_transition"])
            for row in group
            if isinstance(row.get("assistance_transition"), str)
        )
        metric_summary: dict[str, dict[str, int | float | None]] = {}
        for metric in (
            "duration_ms",
            "command_calls",
            "tool_calls",
            "mcp_calls",
            "input_tokens",
            "output_tokens",
        ):
            values = [
                value
                for row in group
                if isinstance(
                    (value := row.get(f"{metric}_delta")),
                    (int, float),
                )
                and not isinstance(value, bool)
            ]
            metric_summary[metric] = {
                "observations": len(values),
                "mean": mean(values) if values else None,
                "median": median(values) if values else None,
            }
        summaries.append(
            {
                "agent_id": agent_id,
                "subject_id": subject_id,
                "invocation_state": state,
                "total_pairs": len(group),
                "subject_mcp_calls": sum(
                    int(value)
                    for row in group
                    if isinstance(
                        (value := row.get("subject_mcp_calls")),
                        (int, float),
                    )
                    and not isinstance(value, bool)
                ),
                "transitions": {
                    name: transitions.get(name, 0)
                    for name in ("gain", "preserved", "unresolved", "regression")
                },
                "delta_metrics": metric_summary,
            }
        )
    return summaries


def _task_assistance_evidence(
    rows: list[dict[str, Any]],
    exclusions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[
        tuple[str, str, str, str],
        dict[str, list[dict[str, Any]]],
    ] = defaultdict(lambda: {"pairs": [], "exclusions": []})
    for row in rows:
        key = (
            str(row["task_id"]),
            str(row["agent_id"]),
            str(row["condition_id"]),
            str(row["subject_id"]),
        )
        grouped[key]["pairs"].append(row)
    for row in exclusions:
        key = (
            str(row["task_id"]),
            str(row["agent_id"]),
            str(row["condition_id"]),
            str(row["subject_id"]),
        )
        grouped[key]["exclusions"].append(row)

    output: list[dict[str, Any]] = []
    for (task_id, agent_id, condition_id, subject_id), evidence in sorted(
        grouped.items()
    ):
        pairs = evidence["pairs"]
        excluded = evidence["exclusions"]
        transitions = Counter(
            str(row["assistance_transition"])
            for row in pairs
            if isinstance(row.get("assistance_transition"), str)
        )
        by_invocation: dict[str, list[dict[str, Any]]] = {
            "invoked": [],
            "not-invoked": [],
            "unknown": [],
        }
        for row in pairs:
            invoked = row.get("subject_tool_invoked")
            state = (
                "invoked"
                if invoked is True
                else "not-invoked"
                if invoked is False
                else "unknown"
            )
            by_invocation[state].append(row)

        transition_by_invocation = {}
        economics_by_invocation = {}
        for state, state_rows in by_invocation.items():
            counts = Counter(
                str(row["assistance_transition"])
                for row in state_rows
                if isinstance(row.get("assistance_transition"), str)
            )
            transition_by_invocation[state] = {
                name: counts.get(name, 0)
                for name in ("gain", "preserved", "unresolved", "regression")
            }
            metrics: dict[str, dict[str, int | float | None]] = {}
            for metric in (
                "duration_ms",
                "command_calls",
                "tool_calls",
                "mcp_calls",
                "input_tokens",
                "output_tokens",
            ):
                values = [
                    value
                    for row in state_rows
                    if isinstance(
                        (value := row.get(f"{metric}_delta")),
                        (int, float),
                    )
                    and not isinstance(value, bool)
                ]
                metrics[metric] = {
                    "observations": len(values),
                    "mean": mean(values) if values else None,
                    "median": median(values) if values else None,
                }
            economics_by_invocation[state] = metrics

        bare_semantic_failures = (
            transitions.get("gain", 0) + transitions.get("unresolved", 0)
        )
        bare_semantic_successes = (
            transitions.get("preserved", 0) + transitions.get("regression", 0)
        )
        assisted_semantic_failures = (
            transitions.get("unresolved", 0) + transitions.get("regression", 0)
        )
        assisted_semantic_successes = (
            transitions.get("gain", 0) + transitions.get("preserved", 0)
        )
        invoked_transitions = transition_by_invocation["invoked"]
        not_invoked_transitions = transition_by_invocation["not-invoked"]

        signals: list[str] = []
        if excluded:
            signals.append("runtime-or-comparability-exclusions")
        if pairs and bare_semantic_failures:
            signals.append("bare-headroom-observed")
        elif pairs and not bare_semantic_failures:
            signals.append("bare-no-headroom-observed")
        if by_invocation["invoked"]:
            signals.append("subject-invocation-observed")
            if invoked_transitions["gain"]:
                signals.append("invoked-gain-observed")
            if invoked_transitions["regression"]:
                signals.append("invoked-regression-observed")
            if not invoked_transitions["gain"]:
                signals.append("invoked-no-gain-observed")
        elif pairs and not by_invocation["unknown"]:
            signals.append("subject-not-invoked")
        if bare_semantic_failures and not by_invocation["invoked"]:
            signals.append("bare-headroom-without-subject-invocation")
        if not_invoked_transitions["regression"]:
            signals.append("regression-without-subject-invocation")

        tools = sorted(
            {
                name
                for row in pairs
                for name in row.get("subject_tool_names", [])
                if isinstance(name, str) and name
            }
        )
        output.append(
            {
                "task_id": task_id,
                "agent_id": agent_id,
                "condition_id": condition_id,
                "subject_id": subject_id,
                "expected_pairs": len(pairs) + len(excluded),
                "comparable_pairs": len(pairs),
                "excluded_pairs": len(excluded),
                "excluded_statuses": {
                    "bare": dict(
                        sorted(Counter(str(row["bare_status"]) for row in excluded).items())
                    ),
                    "assisted": dict(
                        sorted(
                            Counter(
                                str(row["assisted_status"]) for row in excluded
                            ).items()
                        )
                    ),
                },
                "bare_semantic": {
                    "successes": bare_semantic_successes,
                    "failures": bare_semantic_failures,
                },
                "assisted_semantic": {
                    "successes": assisted_semantic_successes,
                    "failures": assisted_semantic_failures,
                },
                "transitions": {
                    name: transitions.get(name, 0)
                    for name in ("gain", "preserved", "unresolved", "regression")
                },
                "subject_use": {
                    "invoked_pairs": len(by_invocation["invoked"]),
                    "not_invoked_pairs": len(by_invocation["not-invoked"]),
                    "unknown_pairs": len(by_invocation["unknown"]),
                    "subject_mcp_calls": sum(
                        int(value)
                        for row in pairs
                        if isinstance(
                            (value := row.get("subject_mcp_calls")),
                            (int, float),
                        )
                        and not isinstance(value, bool)
                    ),
                    "subject_tool_names": tools,
                },
                "transitions_by_invocation": transition_by_invocation,
                "delta_metrics_by_invocation": economics_by_invocation,
                "evidence_signals": signals,
            }
        )
    return output


def _stability(
    receipts: list[dict[str, Any]],
    *,
    expected: dict[str, dict[str, Any]],
    suite: SuiteDefinition,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    expected_ids: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    conditions = {row["id"]: row for row in suite.experiment["conditions"]}
    for row in expected.values():
        condition = conditions[row["condition_id"]]
        key = (str(row["task_id"]), str(condition["agent"]), str(condition["subject"]))
        expected_ids[key].append(int(row.get("replicate_id", row.get("seed"))))
    for receipt in receipts:
        grouped[(_task_id(receipt), _agent_id(receipt), _subject_id(receipt))].append(
            receipt
        )

    rows: list[dict[str, Any]] = []
    for key, identifiers in sorted(expected_ids.items()):
        group = grouped.get(key, [])
        valid = [row for row in group if row.get("status") in _VALID_OUTCOMES]
        gradeable = [row for row in valid if _semantic_gradeable(row)]
        correct = sum(_semantic_success(row) is True for row in gradeable)
        answer_counts = Counter(
            json.dumps(
                row.get("scoring", {}).get("oracle_grade", {}).get("normalized_actual"),
                sort_keys=True,
            )
            for row in gradeable
        )
        if len(valid) != len(identifiers):
            state = "execution-unstable"
        elif len(gradeable) != len(valid):
            state = "not-gradeable" if not gradeable else "unstable"
        elif correct == len(gradeable):
            state = "stable-correct"
        elif correct == 0 and len(answer_counts) == 1:
            state = "stable-incorrect"
        else:
            state = "unstable"
        rows.append(
            {
                "task_id": key[0],
                "agent_id": key[1],
                "subject_id": key[2],
                "replicates": len(identifiers),
                "observed_replicates": len(group),
                "replicate_ids": sorted(identifiers),
                "observed_replicate_ids": sorted(_replicate_id(row) for row in group),
                "valid_outcomes": len(valid),
                "gradeable_outcomes": len(gradeable),
                "semantic_correct": correct,
                "semantic_incorrect": len(gradeable) - correct,
                "format_compliant": sum(
                    _oracle_bool(row, "format_compliant") is True for row in valid
                ),
                "answer_distribution": dict(sorted(answer_counts.items())),
                "state": state,
            }
        )
    return rows


def _diagnostic(receipt: dict[str, Any]) -> dict[str, Any]:
    status = receipt.get("status")
    grade = receipt.get("scoring", {}).get("oracle_grade", {})
    process = receipt.get("execution", {}).get("agent_terminal") or {}
    source = receipt.get("diagnostic")
    if not isinstance(source, dict):
        source = None
    stage = source.get("stage") if source is not None else None
    reason_code = source.get("reason_code") if source is not None else None
    flags = {
        "contamination": status == "CONTAMINATED",
        "output_contract": grade.get("format_compliant") is False,
        "semantic_ungradeable": grade.get("semantic_gradeable") is False,
        "semantic_incorrect": grade.get("semantic_status") == "INCORRECT",
    }
    reason = str(receipt.get("reason") or "").lower()
    if reason_code == "interrupted-launch":
        primary = "runtime"
    elif reason_code == "agent-timeout":
        primary = "timeout"
    elif reason_code == "oracle-invalid":
        primary = "oracle-invalid-or-ambiguous"
    elif reason_code in {
        "agent-terminal-failed",
        "agent-terminal-missing",
        "agent-final-answer-missing",
    }:
        primary = "agent-terminal"
    elif isinstance(reason_code, str) and reason_code.startswith("agent-"):
        primary = "runtime"
    elif flags["contamination"]:
        primary = "contamination"
    elif status == "INVALID" and "oracle" in reason:
        primary = "oracle-invalid-or-ambiguous"
    elif status == "INCOMPLETE" and "timed out" in reason:
        primary = "timeout"
    elif status == "INCOMPLETE" and process.get("type") == "turn.failed":
        primary = "agent-terminal"
    elif status in {"INCOMPLETE", "INVALID"}:
        primary = "runtime"
    elif flags["semantic_incorrect"]:
        primary = "semantic-incorrect"
    elif flags["output_contract"] and not grade.get("semantic_gradeable"):
        primary = "output-contract"
    elif flags["semantic_ungradeable"]:
        primary = "semantic-ungradeable"
    elif status == "PASS":
        primary = "semantic-correct"
    else:
        primary = "semantic-incorrect" if status == "FAIL" else "runtime"
    return {
        "primary": primary,
        "flags": flags,
        "stage": stage,
        "reason_code": reason_code,
        "diagnostic_source": "receipt" if source is not None else "legacy-inferred",
    }


def _pair_exclusions(
    *,
    expected: dict[str, dict[str, Any]],
    by_definition: dict[str, list[dict[str, Any]]],
    suite: SuiteDefinition,
    interrupted: set[str] | None = None,
) -> list[dict[str, Any]]:
    interrupted = interrupted or set()
    conditions = {row["id"]: row for row in suite.experiment["conditions"]}
    groups: dict[tuple[str, str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for definition, row in expected.items():
        condition = conditions[row["condition_id"]]
        key = (
            str(row["task_id"]),
            str(condition["agent"]),
            int(row.get("replicate_id", row.get("seed"))),
        )
        groups[key][str(row["condition_id"])] = {
            "definition_id": definition,
            "subject_id": str(condition["subject"]),
            "receipt": by_definition.get(definition, [None])[0],
        }
    exclusions = []
    for key, arms in sorted(groups.items()):
        controls = [arm for arm in arms.values() if arm["subject_id"] == "none"]
        if len(controls) > 1:
            raise ReportError(f"multiple bare executions for pair {key}")
        bare = controls[0] if controls else None
        for condition_id, arm in sorted(arms.items()):
            if arm["subject_id"] == "none":
                continue
            left = bare["receipt"] if bare else None
            right = arm["receipt"]
            if (
                left
                and right
                and all(row.get("status") in _VALID_OUTCOMES for row in (left, right))
            ):
                continue
            exclusions.append(
                {
                    "task_id": key[0],
                    "agent_id": key[1],
                    "replicate_id": key[2],
                    "condition_id": condition_id,
                    "subject_id": arm["subject_id"],
                    "bare_definition_id": bare["definition_id"] if bare else None,
                    "assisted_definition_id": arm["definition_id"],
                    "bare_status": left.get("status")
                    if left
                    else (
                        "INTERRUPTED"
                        if bare and bare["definition_id"] in interrupted
                        else "MISSING"
                    ),
                    "assisted_status": right.get("status")
                    if right
                    else (
                        "INTERRUPTED"
                        if arm["definition_id"] in interrupted
                        else "MISSING"
                    ),
                }
            )
    return exclusions


def _cross_agent_observations(
    receipts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[
        tuple[str, str, int, int],
        dict[str, dict[str, Any]],
    ] = defaultdict(dict)
    for receipt in receipts:
        if receipt.get("status") not in _VALID_OUTCOMES:
            continue
        execution = receipt["execution"]
        key = (
            _task_id(receipt),
            _subject_id(receipt),
            int(execution["trial_index"]),
            _replicate_id(receipt),
        )
        agent = _agent_id(receipt)
        if agent in grouped[key]:
            raise ReportError(
                f"multiple executions for cross-agent observation {key} / {agent}"
            )
        grouped[key][agent] = {
            "status": receipt["status"],
            "duration_ms": _agent_metric(receipt, "duration_ms"),
            "tool_calls": _agent_metric(receipt, "tool_calls"),
            "mcp_calls": _agent_metric(receipt, "mcp_calls"),
            "subject_mcp_calls": _agent_metric(
                receipt,
                "subject_mcp_calls",
            ),
            "input_tokens": _agent_metric(receipt, "input_tokens"),
            "output_tokens": _agent_metric(receipt, "output_tokens"),
            "subject_tool_invoked": (
                receipt.get("measurements", {})
                .get("agent", {})
                .get("subject_tool_invoked")
            ),
        }

    return [
        {
            "task_id": key[0],
            "subject_id": key[1],
            "trial_index": key[2],
            "replicate_id": key[3],
            "agents": dict(sorted(agents.items())),
        }
        for key, agents in sorted(grouped.items())
        if len(agents) > 1
    ]


def build_report(
    *,
    suite: SuiteDefinition,
    results_root: Path,
    require_complete: bool = True,
    selected_definitions: set[str] | None = None,
    selection: dict[str, Any] | None = None,
    projected_receipts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    receipts = (
        _receipts(results_root) if projected_receipts is None else projected_receipts
    )
    all_expected = {str(row["definition_id"]): row for row in suite.trial_definitions()}
    expected = (
        all_expected
        if selected_definitions is None
        else {
            key: row for key, row in all_expected.items() if key in selected_definitions
        }
    )
    if selected_definitions is not None and set(expected) != selected_definitions:
        raise ReportError("report selection contains definitions outside frozen suite")
    new_contract = any("replicate_id" in row for row in expected.values())
    interrupted: set[str] = set()
    launch_claims: dict[str, str] = {}
    campaign_id = None
    by_definition: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for receipt in receipts:
        definition = receipt.get("definition_id")
        if not isinstance(definition, str):
            raise ReportError("receipt has no definition_id")
        if definition not in all_expected:
            raise ReportError(
                f"results contain execution outside frozen suite: {definition}"
            )
        if definition in expected:
            by_definition[definition].append(receipt)

    receipts = [row for rows in by_definition.values() for row in rows]

    duplicates = {
        definition: values
        for definition, values in by_definition.items()
        if len(values) > 1
    }
    if duplicates:
        raise ReportError(
            "multiple executions found for frozen definition(s): "
            + ", ".join(sorted(duplicates))
        )

    if new_contract:
        try:
            manifest = read_campaign(results_root)
            campaign_id = manifest["campaign_id"]
            if projected_receipts is None and not set(expected).issubset(
                set(manifest["selected_definitions"])
            ):
                raise CampaignAuthorityError("report selection exceeds frozen campaign")
            launch_claims = read_launch_claims(results_root, campaign_id)
            if not set(launch_claims).issubset(set(manifest["selected_definitions"])):
                raise CampaignAuthorityError(
                    "launch claim exceeds frozen campaign selection"
                )
            interrupted = set(launch_claims)
        except CampaignAuthorityError as exc:
            raise ReportError(str(exc)) from exc
        for receipt in receipts:
            if (
                receipt.get("definition_id") in expected
                and receipt.get("execution", {}).get("campaign_id") != campaign_id
            ):
                raise ReportError("receipt belongs to a different campaign authority")
            if projected_receipts is None and launch_claims.get(
                receipt["definition_id"]
            ) != receipt.get("trial_id"):
                raise ReportError("receipt has no matching launch claim")

    missing = sorted(set(expected) - set(by_definition))
    if require_complete and missing:
        raise ReportError(
            f"campaign is incomplete: {len(missing)} frozen definition(s) missing"
        )

    validate_comparability(receipts)

    by_condition: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_agent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for receipt in receipts:
        by_condition[_condition_id(receipt)].append(receipt)
        by_agent[_agent_id(receipt)].append(receipt)

    statuses = Counter(str(row.get("status")) for row in receipts)
    invalid_outcomes = sum(
        count
        for status, count in statuses.items()
        if status not in _VALID_OUTCOMES
    )
    campaign_complete = not missing
    campaign_qualified = campaign_complete and invalid_outcomes == 0
    paired_assistance = _paired_assistance(receipts)
    stability = _stability(receipts, expected=expected, suite=suite)
    pair_exclusions = _pair_exclusions(
        expected=expected,
        by_definition=by_definition,
        suite=suite,
        interrupted=interrupted,
    )
    return {
        "schema": {
            "name": "agents-cookbook-benchmark-report",
            "version": 11,
        },
        "suite": suite.experiment["suite"],
        "experiment": {
            "id": suite.experiment["id"],
            "version": suite.experiment["version"],
        },
        "selection": selection
        or {
            "tasks": [],
            "agents": [],
            "subjects": [],
            "condition": None,
            "bare_control_included": False,
        },
        "expected_trials": len(expected),
        "observed_trials": len(receipts),
        "missing_definitions": missing,
        "interrupted_definitions": sorted(interrupted & set(missing)),
        "status_counts": dict(sorted(statuses.items())),
        "conditions": {
            condition: _aggregate_condition(rows)
            for condition, rows in sorted(by_condition.items())
        },
        "paired_assistance": paired_assistance,
        "paired_assistance_summary": _paired_assistance_summary(paired_assistance),
        "paired_assistance_usage_summary": _paired_assistance_usage_summary(
            paired_assistance
        ),
        "paired_assistance_exclusions": pair_exclusions,
        "expected_assistance_pairs": len(paired_assistance) + len(pair_exclusions),
        "task_assistance_evidence": _task_assistance_evidence(
            paired_assistance,
            pair_exclusions,
        ),
        "stability": stability,
        "task_agent_authority": _task_agent_authority(receipts),
        "subject_adoption": _subject_adoption_summary(receipts),
        "diagnostics": [
            {
                "definition_id": row["definition_id"],
                "trial_id": row["trial_id"],
                "task_id": _task_id(row),
                "agent_id": _agent_id(row),
                "subject_id": _subject_id(row),
                **_diagnostic(row),
            }
            for row in sorted(receipts, key=lambda item: item["definition_id"])
        ],
        "agent_profiles": {
            agent: _aggregate_condition(rows)
            for agent, rows in sorted(by_agent.items())
        },
        "cross_agent_observations": _cross_agent_observations(receipts),
        "campaign_qualification": {
            "status": "QUALIFIED" if campaign_qualified else "NOT_QUALIFIED",
            "complete": campaign_complete,
            "invalid_outcomes": invalid_outcomes,
            "mixed_execution_authority": False,
            "mixed_localization_scoring_policy": False,
        },
        "authority": {
            "overall_winner": None,
            "ranking_performed": False,
            "mixed_execution_definitions_rejected": True,
            "invalid_outcomes_excluded_from_success_rates": True,
            "economics_include_invalid_and_incomplete_trials": True,
            "paired_assistance_scope": "valid-outcomes-only",
            "replicate_identity_field": (
                "execution.replicate_id"
                if any("replicate_id" in row["execution"] for row in receipts)
                else "execution.seed"
            ),
            "replicate_identity_is_provider_sampling_seed": False,
            "cross_agent_rows_are_descriptive": True,
        },
    }
