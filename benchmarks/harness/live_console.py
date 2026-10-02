"""Human-readable live benchmark result projection.

This module renders already-observed trial statuses for the terminal. It owns no
benchmark truth: receipts, scoring, campaign authority, and qualification remain
unchanged.
"""

from __future__ import annotations

from collections import Counter
from statistics import mean
from threading import Event, Lock, Thread
from time import monotonic
from typing import Any, Callable

from benchmarks.harness.report import ReportError, classify_assistance_pair
from benchmarks.harness.runner import TrialRunResult

from benchmarks.harness.suite import SuiteDefinition


def _subject_label(subject: str) -> str:
    if subject == "none":
        return "Bare"
    return subject.replace("_", " ").replace("-", " ").title()


def _replicate_key(row: dict[str, Any]) -> object:
    if "replicate_id" in row:
        return (row["trial"], "replicate", row["replicate_id"])
    if "seed" in row:
        return (row["trial"], "seed", row["seed"])
    return (row["trial"],)


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


def _display_outcome(receipt: dict[str, Any]) -> str:
    status = str(receipt.get("status") or "UNKNOWN")
    grade = receipt.get("scoring", {}).get("oracle_grade", {})
    if not isinstance(grade, dict):
        return status
    if grade.get("semantic_gradeable") is False:
        return "UNGRADABLE"
    semantic_status = grade.get("semantic_status")
    if semantic_status == "CORRECT":
        return "PASS"
    if semantic_status == "INCORRECT":
        return "FAIL"
    return status


def _subject_tool_use(receipt: dict[str, Any]) -> tuple[bool | None, int | None]:
    agent = receipt.get("measurements", {}).get("agent", {})
    if not isinstance(agent, dict):
        return None, None
    invoked = agent.get("subject_tool_invoked")
    if not isinstance(invoked, bool):
        invoked = None
    calls = agent.get("subject_mcp_calls")
    if isinstance(calls, bool) or not isinstance(calls, int):
        calls = None
    return invoked, calls


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
        self._condition_order: dict[tuple[str, str], list[str]] = {}
        self._outcomes: dict[
            tuple[str, str],
            list[tuple[dict[str, Any], str, dict[str, Any]]],
        ] = {}
        self._emitted: set[tuple[str, str]] = set()

        for row in selected_rows:
            condition = self._conditions[str(row["condition_id"])]
            group = (str(row["task_id"]), str(condition["agent"]))
            self._expected[group] += 1
            order = self._condition_order.setdefault(group, [])
            condition_id = str(row["condition_id"])
            if condition_id not in order:
                order.append(condition_id)

    def record(self, row: dict[str, Any], receipt: dict[str, Any]) -> str | None:
        if receipt.get("definition_id") != row["definition_id"]:
            raise ValueError("live matrix receipt does not match selected definition")
        condition = self._conditions[str(row["condition_id"])]
        group = (str(row["task_id"]), str(condition["agent"]))
        condition_id = str(row["condition_id"])
        self._outcomes.setdefault(group, []).append((row, condition_id, receipt))

        if group in self._emitted:
            return None
        if len(self._outcomes[group]) != self._expected[group]:
            return None

        self._emitted.add(group)
        return self._render(group)

    def _render(self, group: tuple[str, str]) -> str:
        task_id, agent = group
        outcomes = self._outcomes[group]
        conditions = self._condition_order[group]
        subjects = [str(self._conditions[item]["subject"]) for item in conditions]
        repeated = {subject for subject, count in Counter(subjects).items() if count > 1}

        def label(condition_id: str) -> str:
            subject = str(self._conditions[condition_id]["subject"])
            name = _subject_label(subject)
            return f"{name} ({condition_id})" if subject in repeated else name

        trial_indexes = sorted({int(row["trial"]) for row, _, _ in outcomes})
        replicate_ids: dict[int, set[object]] = {}
        for row, _, _ in outcomes:
            replicate_ids.setdefault(int(row["trial"]), set()).add(
                row.get("replicate_id", row.get("seed", row["trial"]))
            )
        by_trial_condition = {
            (int(row["trial"]), condition_id): _display_outcome(receipt)
            for row, condition_id, receipt in outcomes
        }

        headers = ["Replicate ID", *(label(condition_id) for condition_id in conditions)]
        table_rows = [
            [
                (
                    str(next(iter(replicate_ids[trial])))
                    if len(replicate_ids[trial]) == 1
                    else f"trial {trial} (mixed IDs)"
                ),
                *(
                    by_trial_condition.get((trial, condition_id), "-")
                    for condition_id in conditions
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
            controls: dict[object, dict[str, Any]] = {}
            for row, condition_id, receipt in outcomes:
                if self._conditions[condition_id]["subject"] != "none":
                    continue
                key = _replicate_key(row)
                if key in controls:
                    raise ReportError(
                        f"multiple bare executions for pair {task_id} / {agent} / {key}"
                    )
                controls[key] = receipt
            assisted_conditions = [
                item for item in conditions if self._conditions[item]["subject"] != "none"
            ]
            if assisted_conditions:
                lines.extend(["", "Paired vs Bare"])
                transition_rows: list[list[str]] = []
                for condition_id in assisted_conditions:
                    assisted = {
                        _replicate_key(row): receipt
                        for row, observed_condition, receipt in outcomes
                        if observed_condition == condition_id
                    }
                    counts: Counter[str] = Counter()
                    for key in sorted(assisted, key=repr):
                        baseline = controls.get(key)
                        candidate = assisted.get(key)
                        transition = (
                            classify_assistance_pair(baseline, candidate)
                            if baseline is not None and candidate is not None
                            else None
                        )
                        counts[transition or "excluded"] += 1
                    transition_rows.append(
                        [
                            label(condition_id),
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

                lines.extend(["", "Subject tool use"])
                usage_rows: list[list[str]] = []
                for condition_id in assisted_conditions:
                    usage = [
                        _subject_tool_use(receipt)
                        for _row, observed_condition, receipt in outcomes
                        if observed_condition == condition_id
                    ]
                    invoked = sum(value is True for value, _calls in usage)
                    not_invoked = sum(value is False for value, _calls in usage)
                    unknown = sum(value is None for value, _calls in usage)
                    total_calls = sum(
                        calls for _value, calls in usage if calls is not None
                    )
                    usage_rows.append(
                        [
                            label(condition_id),
                            str(invoked),
                            str(not_invoked),
                            str(unknown),
                            str(total_calls),
                        ]
                    )
                lines.extend(
                    _render_table(
                        [
                            "Subject",
                            "Invoked",
                            "Not invoked",
                            "Unknown",
                            "MCP calls",
                        ],
                        usage_rows,
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
        initial_status: dict[str, Any],
    ) -> None:
        self._conditions = {
            str(condition["id"]): condition
            for condition in suite.experiment["conditions"]
        }
        self._total = len(selected_rows)
        self._processed = 0
        self._durations: list[float] = []
        self._durations_by_condition: dict[str, list[float]] = {}
        self._definition_condition = {
            str(row["definition_id"]): str(row["condition_id"])
            for row in selected_rows
        }
        self._states = {
            str(row["definition_id"]): str(row["state"])
            for row in initial_status["rows"]
        }
        self._verified = int(initial_status["complete_trials"])
        self._pending = int(initial_status["pending_trials"])
        self._interrupted = int(initial_status["interrupted_trials"])
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
        eta = self._eta()
        return (
            f"[{self._processed + 1}/{self._total} this run] "
            f"task {task_index}/{len(self._task_order)} {task_id} | "
            f"{row['condition_id']} | replicate {trial + 1}/{trials} | "
            f"run elapsed {_duration(elapsed)} | verified {self._verified}/{self._total} | "
            f"pending {self._pending} | interrupted {self._interrupted} | "
            f"execution ETA {_duration(eta)}"
        )

    def finish_line(
        self,
        result: TrialRunResult,
        *,
        elapsed: float,
        trial_seconds: float,
    ) -> str:
        self._processed += 1
        previous = self._states.get(result.definition_id)
        if previous != "COMPLETE":
            self._verified += 1
            if previous == "PENDING":
                self._pending -= 1
            elif previous == "INTERRUPTED":
                self._interrupted -= 1
            self._states[result.definition_id] = "COMPLETE"
        if not result.reused and not result.recovered and trial_seconds > 0:
            self._durations.append(trial_seconds)
            condition_id = self._definition_condition[result.definition_id]
            self._durations_by_condition.setdefault(condition_id, []).append(
                trial_seconds
            )
        eta = self._eta()
        mode = (
            "reused"
            if result.reused
            else "recovered"
            if result.recovered
            else "executed"
        )
        average = mean(self._durations) if self._durations else None
        return (
            f"PROGRESS processed {self._processed}/{self._total} "
            f"({(100 * self._processed / self._total):.1f}%) | "
            f"verified {self._verified}/{self._total} | {mode} | "
            f"run elapsed {_duration(elapsed)} | pending {self._pending} | "
            f"interrupted {self._interrupted} | avg {_duration(average)}/execution | "
            f"execution ETA {_duration(eta)}"
        )

    def heartbeat_line(
        self,
        row: dict[str, Any],
        *,
        stage: str,
        elapsed: float,
        trial_seconds: float,
    ) -> str:
        return (
            f"ACTIVE {row['task_id']} / {row['condition_id']} replicate {int(row['trial']) + 1} | "
            f"stage {stage} | trial elapsed {_duration(trial_seconds)} | "
            f"run elapsed {_duration(elapsed)} | verified {self._verified}/{self._total}"
        )

    def abort_line(
        self,
        row: dict[str, Any],
        *,
        stage: str,
        elapsed: float,
        error: Exception,
    ) -> str:
        return (
            f"ABORT {row['task_id']} / {row['condition_id']} replicate {int(row['trial']) + 1} | "
            f"stage {stage} | processed {self._processed}/{self._total} | "
            f"verified {self._verified}/{self._total} | run elapsed {_duration(elapsed)} | {error}"
        )

    def _eta(self) -> float | None:
        if self._pending <= 0:
            return 0.0
        if not self._durations:
            return None
        fallback = mean(self._durations)
        remaining = [
            definition_id
            for definition_id, state in self._states.items()
            if state == "PENDING"
        ]
        estimate = 0.0
        for definition_id in remaining:
            condition_id = self._definition_condition.get(definition_id)
            samples = self._durations_by_condition.get(str(condition_id), [])
            estimate += mean(samples) if samples else fallback
        return estimate


class TrialHeartbeat:
    """Emit bounded activity lines without mutating trial evidence."""

    def __init__(
        self,
        *,
        progress: LiveCampaignProgress,
        row: dict[str, Any],
        run_started: float,
        emit: Callable[[str], None],
        interval: float = 30.0,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._progress = progress
        self._row = row
        self._run_started = run_started
        self._emit = emit
        self._interval = interval
        self._clock = clock
        self._trial_started = clock()
        self._last_emitted = self._trial_started
        self._stage = "admission"
        self._lock = Lock()
        self._stop = Event()
        self._thread: Thread | None = None

    @property
    def stage(self) -> str:
        with self._lock:
            return self._stage

    def update_stage(self, stage: str) -> None:
        with self._lock:
            self._stage = stage

    def tick(self, now: float | None = None) -> str | None:
        now = self._clock() if now is None else now
        with self._lock:
            if self._stop.is_set() or now - self._last_emitted < self._interval:
                return None
            self._last_emitted = now
            stage = self._stage
        return self._progress.heartbeat_line(
            self._row,
            stage=stage,
            elapsed=now - self._run_started,
            trial_seconds=now - self._trial_started,
        )

    def _loop(self) -> None:
        while not self._stop.wait(self._interval):
            line = self.tick()
            if line is not None:
                self._emit(line)

    def __enter__(self) -> TrialHeartbeat:
        self._thread = Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join()


def render_trial_failure(
    *,
    row: dict[str, Any],
    subject: str,
    result: TrialRunResult,
) -> str | None:
    """Render stable failure fields before bounded raw diagnostic evidence."""
    if result.status == "PASS":
        return None
    replicate_id = row.get("replicate_id", row.get("seed"))
    lines = [
        "",
        f"FAILURE {row['task_id']}",
        f"Replicate ordinal: {int(row['trial']) + 1}",
        f"Replicate ID: {replicate_id if replicate_id is not None else 'unknown'}",
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
