"""Human-readable live benchmark result projection.

This module renders already-observed trial statuses for the terminal. It owns no
benchmark truth: receipts, scoring, campaign authority, and qualification remain
unchanged.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

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
