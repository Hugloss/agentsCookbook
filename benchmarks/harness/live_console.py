"""Human-readable live benchmark result projection.

This module renders already-observed trial statuses for the terminal. It owns no
benchmark truth: receipts, scoring, campaign authority, and qualification remain
unchanged.
"""

from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any

from benchmarks.harness.runner import TrialRunResult

from benchmarks.harness.suite import SuiteDefinition


_SEMANTIC_STATUSES = frozenset({"PASS", "FAIL"})


def _subject_label(subject: str) -> str:
    if subject == "none":
        return "Bare"
    return subject.replace("_", " ").replace("-", " ").title()


def _replicate_key(row: dict[str, Any]) -> object:
    if "replicate_id" in row:
        return ("replicate", row["replicate_id"])
    if "seed" in row:
        return ("seed", row["seed"])
    return ("trial", row["trial"])


def _transition(control: str | None, assisted: str | None) -> str:
    if control not in _SEMANTIC_STATUSES or assisted not in _SEMANTIC_STATUSES:
        return "excluded"
    if control == "FAIL" and assisted == "PASS":
        return "gain"
    if control == "PASS" and assisted == "PASS":
        return "preserved"
    if control == "FAIL" and assisted == "FAIL":
        return "unresolved"
    return "regression"


def _render_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]

    def render(row: list[str]) -> str:
        return " | ".join(
            value.ljust(widths[index]) for index, value in enumerate(row)
        )

    return [
        render(headers),
        "-+-".join("-" * width for width in widths),
        *(render(row) for row in rows),
    ]


class LiveTaskMatrix:
    """Project completed task/agent groups into compact terminal matrices."""

    def __init__(
        self,
        suite: SuiteDefinition,
        selected_rows: list[dict[str, Any]],
    ) -> None:
        self._conditions = {
            str(condition["id"]): condition
            for condition in suite.experiment["conditions"]
        }
        self._expected: Counter[tuple[str, str]] = Counter()
        self._subject_order: dict[tuple[str, str], list[str]] = {}
        self._outcomes: dict[
            tuple[str, str],
            list[tuple[dict[str, Any], str, str]],
        ] = {}
        self._emitted: set[tuple[str, str]] = set()

        for row in selected_rows:
            condition = self._conditions[str(row["condition_id"])]
            group = (str(row["task_id"]), str(condition["agent"]))
            subject = str(condition["subject"])
            self._expected[group] += 1
            order = self._subject_order.setdefault(group, [])
            if subject not in order:
                order.append(subject)

    def record(self, row: dict[str, Any], status: str) -> str | None:
        condition = self._conditions[str(row["condition_id"])]
        group = (str(row["task_id"]), str(condition["agent"]))
        subject = str(condition["subject"])
        self._outcomes.setdefault(group, []).append((row, subject, status))

        if group in self._emitted:
            return None
        if len(self._outcomes[group]) != self._expected[group]:
            return None

        self._emitted.add(group)
        return self._render(group)

    def _render(self, group: tuple[str, str]) -> str:
        task_id, agent = group
        outcomes = self._outcomes[group]
        subjects = self._subject_order[group]

        trial_indexes = sorted({int(row["trial"]) for row, _, _ in outcomes})
        by_trial_subject = {
            (int(row["trial"]), subject): status
            for row, subject, status in outcomes
        }

        headers = ["Replicate", *(_subject_label(subject) for subject in subjects)]
        table_rows = [
            [
                str(trial),
                *(
                    by_trial_subject.get((trial, subject), "-")
                    for subject in subjects
                ),
            ]
            for trial in trial_indexes
        ]

        lines = [
            "",
            f"RESULT {task_id} [{agent}]",
            "",
            *_render_table(headers, table_rows),
        ]

        if "none" in subjects:
            control = {
                _replicate_key(row): status
                for row, subject, status in outcomes
                if subject == "none"
            }
            assisted_subjects = [subject for subject in subjects if subject != "none"]
            if assisted_subjects:
                lines.extend(["", "Paired vs Bare"])
                transition_rows: list[list[str]] = []
                for subject in assisted_subjects:
                    assisted = {
                        _replicate_key(row): status
                        for row, observed_subject, status in outcomes
                        if observed_subject == subject
                    }
                    counts: Counter[str] = Counter(
                        _transition(control.get(key), assisted.get(key))
                        for key in sorted(set(control) | set(assisted), key=repr)
                    )
                    transition_rows.append(
                        [
                            _subject_label(subject),
                            str(counts["gain"]),
                            str(counts["preserved"]),
                            str(counts["unresolved"]),
                            str(counts["regression"]),
                            str(counts["excluded"]),
                        ]
                    )
                lines.extend(
                    _render_table(
                        [
                            "Subject",
                            "Gain",
                            "Preserved",
                            "Unresolved",
                            "Regression",
                            "Excluded",
                        ],
                        transition_rows,
                    )
                )

        return "\n".join(lines)


def _duration(value: float | None) -> str:
    if value is None:
        return "estimating..."
    seconds = max(0, int(round(value)))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h{minutes:02d}m"
    if minutes:
        return f"{minutes}m{seconds:02d}s"
    return f"{seconds}s"


class LiveCampaignProgress:
    """Render bounded human/agent-readable campaign progress and ETA."""

    def __init__(
        self,
        suite: SuiteDefinition,
        selected_rows: list[dict[str, Any]],
    ) -> None:
        self._conditions = {
            str(condition["id"]): condition
            for condition in suite.experiment["conditions"]
        }
        self._total = len(selected_rows)
        self._completed = 0
        self._durations: list[float] = []
        self._task_order: list[str] = []
        for row in selected_rows:
            task_id = str(row["task_id"])
            if task_id not in self._task_order:
                self._task_order.append(task_id)

    def start_line(self, row: dict[str, Any], *, elapsed: float) -> str:
        condition = self._conditions[str(row["condition_id"])]
        task_id = str(row["task_id"])
        task_index = self._task_order.index(task_id) + 1
        trial = int(row["trial"])
        trials = int(condition["trials"])
        remaining = self._total - self._completed
        eta = self._eta(remaining=remaining)
        return (
            f"[{self._completed + 1}/{self._total}] "
            f"task {task_index}/{len(self._task_order)} {task_id} | "
            f"{row['condition_id']} | replicate {trial + 1}/{trials} | "
            f"elapsed {_duration(elapsed)} | remaining {remaining} | "
            f"ETA {_duration(eta)}"
        )

    def finish_line(
        self,
        result: TrialRunResult,
        *,
        elapsed: float,
        trial_seconds: float,
    ) -> str:
        self._completed += 1
        if not result.reused and not result.recovered and trial_seconds > 0:
            self._durations.append(trial_seconds)
        remaining = self._total - self._completed
        eta = self._eta(remaining=remaining)
        mode = (
            "reused"
            if result.reused
            else "recovered"
            if result.recovered
            else "executed"
        )
        average = mean(self._durations) if self._durations else None
        return (
            f"PROGRESS {self._completed}/{self._total} "
            f"({(100 * self._completed / self._total):.1f}%) | "
            f"{mode} | elapsed {_duration(elapsed)} | remaining {remaining} | "
            f"avg {_duration(average)}/trial | ETA {_duration(eta)}"
        )

    def _eta(self, *, remaining: int) -> float | None:
        if not self._durations or remaining <= 0:
            return 0.0 if remaining <= 0 else None
        return mean(self._durations) * remaining


def render_trial_failure(
    *,
    row: dict[str, Any],
    subject: str,
    result: TrialRunResult,
) -> str | None:
    """Render stable failure fields before bounded raw diagnostic evidence."""
    if result.status == "PASS":
        return None
    lines = [
        "",
        f"FAILURE {row['task_id']}",
        f"Replicate: {row['trial']}",
        f"Condition: {row['condition_id']}",
        f"Subject: {_subject_label(subject)}",
        f"Status: {result.status}",
        f"Stage: {result.stage or 'unknown'}",
        f"Reason code: {result.reason_code or 'unknown'}",
        f"Reason: {result.reason or 'none'}",
        f"Evidence: {result.result_dir}",
    ]
    if result.recovered:
        lines.append("Recovery: prior interrupted launch sealed; model was not retried")
    if result.diagnostic:
        lines.extend(["", "--- diagnostic ---", result.diagnostic])
    return "\n".join(lines)
