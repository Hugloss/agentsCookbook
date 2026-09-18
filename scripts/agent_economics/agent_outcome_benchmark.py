from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass, asdict
from pathlib import Path


class BenchmarkError(ValueError):
    pass


@dataclass(frozen=True)
class Outcome:
    task_id: str
    mode: str
    correct: bool
    ci_activations: int = 0
    files_opened: int = 0
    evidence_bytes: int = 0
    context_tokens_estimate: int = 0
    tool_calls: int = 0
    local_commands: int = 0
    repair_iterations: int = 0
    seconds_to_first_correct_edit: float | None = None
    focused_verifications: int = 0
    broad_verifications: int = 0
    failed_edits: int = 0
    no_progress_stops: int = 0
    bridge_elapsed_ms: float = 0.0
    local_ci_agree: bool | None = None

    def __post_init__(self) -> None:
        if self.mode not in {"baseline", "bridge"}:
            raise BenchmarkError("mode must be baseline or bridge")
        numeric = (
            self.ci_activations, self.files_opened, self.evidence_bytes,
            self.context_tokens_estimate, self.tool_calls, self.local_commands,
            self.repair_iterations, self.focused_verifications,
            self.broad_verifications, self.failed_edits, self.no_progress_stops,
        )
        if any(value < 0 for value in numeric) or self.bridge_elapsed_ms < 0:
            raise BenchmarkError("benchmark counters must be non-negative")
        if self.seconds_to_first_correct_edit is not None and self.seconds_to_first_correct_edit < 0:
            raise BenchmarkError("time-to-edit must be non-negative")


def load_outcomes(path: Path, *, max_bytes: int = 5_000_000, max_records: int = 10_000) -> list[Outcome]:
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        raise BenchmarkError("benchmark input exceeds byte bound")
    records: list[Outcome] = []
    for line_no, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
            records.append(Outcome(**value))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise BenchmarkError(f"invalid benchmark record at line {line_no}") from exc
        if len(records) > max_records:
            raise BenchmarkError("benchmark record count exceeds bound")
    return records


def compare(outcomes: list[Outcome]) -> dict[str, object]:
    grouped: dict[str, dict[str, Outcome]] = {}
    for outcome in outcomes:
        modes = grouped.setdefault(outcome.task_id, {})
        if outcome.mode in modes:
            raise BenchmarkError(f"duplicate {outcome.mode} record for task {outcome.task_id}")
        modes[outcome.mode] = outcome
    pairs = [(task, modes["baseline"], modes["bridge"]) for task, modes in sorted(grouped.items()) if {"baseline", "bridge"} <= modes.keys()]
    if not pairs:
        raise BenchmarkError("at least one paired baseline/bridge task is required")
    metrics = [
        "ci_activations", "files_opened", "evidence_bytes", "context_tokens_estimate",
        "tool_calls", "local_commands", "repair_iterations", "focused_verifications",
        "broad_verifications", "failed_edits", "no_progress_stops",
    ]
    deltas: dict[str, dict[str, float]] = {}
    for metric in metrics:
        baseline = sum(float(getattr(b, metric)) for _, b, _ in pairs)
        bridge = sum(float(getattr(g, metric)) for _, _, g in pairs)
        deltas[metric] = {
            "baseline_total": baseline,
            "bridge_total": bridge,
            "delta": bridge - baseline,
            "reduction_fraction": (baseline - bridge) / baseline if baseline else 0.0,
        }
    correctness = {
        "baseline_correct": sum(1 for _, b, _ in pairs if b.correct),
        "bridge_correct": sum(1 for _, _, g in pairs if g.correct),
        "paired_tasks": len(pairs),
        "local_ci_disagreements": sum(1 for _, _, g in pairs if g.local_ci_agree is False),
    }
    promotion = {
        "correctness_not_reduced": correctness["bridge_correct"] >= correctness["baseline_correct"],
        "ci_activations_not_increased": deltas["ci_activations"]["delta"] <= 0,
        "context_not_increased": deltas["context_tokens_estimate"]["delta"] <= 0,
        "local_ci_disagreement_zero": correctness["local_ci_disagreements"] == 0,
    }
    payload = {
        "schema": {"name": "agent-outcome-benchmark", "version": 1},
        "correctness": correctness,
        "metrics": deltas,
        "promotion_evidence": promotion,
        "authority": {
            "benchmark_is_measurement_not_release_authority": True,
            "automatic_promotion": False,
        },
    }
    payload["identity"] = "sha256:" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return payload


def main(argv: list[str] | None = None) -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Compare paired baseline and capability-bridge agent outcomes.")
    parser.add_argument("--input", type=Path, required=True, help="JSONL Outcome records")
    parser.add_argument("--artifact", type=Path)
    args = parser.parse_args(argv)
    payload = compare(load_outcomes(args.input))
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.artifact:
        args.artifact.parent.mkdir(parents=True, exist_ok=True)
        args.artifact.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
