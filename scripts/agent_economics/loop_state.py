from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path


class LoopStateError(ValueError):
    pass


@dataclass(frozen=True)
class LoopBudget:
    max_iterations: int = 8
    max_commands: int = 24
    max_wall_seconds: float = 1800.0
    max_stdout_bytes: int = 8_000_000
    max_stderr_bytes: int = 8_000_000

    def __post_init__(self) -> None:
        if min(self.max_iterations, self.max_commands, self.max_stdout_bytes, self.max_stderr_bytes) < 1:
            raise LoopStateError("loop budgets must be positive")
        if self.max_wall_seconds <= 0:
            raise LoopStateError("max_wall_seconds must be positive")


def semantic_identity(value: object) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


class LoopSession:
    def __init__(self, path: Path, *, budget: LoopBudget = LoopBudget()) -> None:
        self.path = path
        self.lock_path = path.with_suffix(path.suffix + ".lock")
        self.budget = budget
        self._lock_fd: int | None = None

    def __enter__(self) -> "LoopSession":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._lock_fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise LoopStateError("loop state is already owned by another writer") from exc
        os.write(self._lock_fd, str(os.getpid()).encode())
        return self

    def __exit__(self, *_args: object) -> None:
        if self._lock_fd is not None:
            os.close(self._lock_fd)
        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            pass

    def load(self) -> dict[str, object]:
        if not self.path.exists():
            return {
                "version": 1,
                "started_monotonic": time.monotonic(),
                "iterations": [],
                "cumulative_commands": 0,
                "cumulative_stdout_bytes": 0,
                "cumulative_stderr_bytes": 0,
            }
        raw = self.path.read_bytes()
        if len(raw) > 2_000_000:
            raise LoopStateError("loop state exceeds 2,000,000 byte bound")
        data = json.loads(raw)
        if not isinstance(data, dict) or data.get("version") != 1:
            raise LoopStateError("invalid loop state")
        return data

    def record(
        self,
        *,
        source_identity: str,
        command_identity: str,
        failure_identity: str,
        evidence_identity: str,
        stdout_bytes: int,
        stderr_bytes: int,
    ) -> dict[str, object]:
        state = self.load()
        iterations = state.setdefault("iterations", [])
        assert isinstance(iterations, list)
        signature = semantic_identity({
            "source_identity": source_identity,
            "failure_identity": failure_identity,
            "evidence_identity": evidence_identity,
        })
        prior = [item.get("signature") for item in iterations if isinstance(item, dict)]
        stop_reason: str | None = None
        if prior and prior[-1] == signature:
            stop_reason = "NO_PROGRESS"
        elif len(prior) >= 2 and prior[-2] == signature:
            stop_reason = "OSCILLATION"
        iterations.append({
            "iteration": len(iterations) + 1,
            "source_identity": source_identity,
            "command_identity": command_identity,
            "failure_identity": failure_identity,
            "evidence_identity": evidence_identity,
            "signature": signature,
        })
        state["cumulative_commands"] = int(state.get("cumulative_commands", 0)) + 1
        state["cumulative_stdout_bytes"] = int(state.get("cumulative_stdout_bytes", 0)) + stdout_bytes
        state["cumulative_stderr_bytes"] = int(state.get("cumulative_stderr_bytes", 0)) + stderr_bytes
        elapsed = time.monotonic() - float(state.get("started_monotonic", time.monotonic()))
        if len(iterations) >= self.budget.max_iterations and stop_reason is None:
            stop_reason = "ITERATION_BUDGET_EXHAUSTED"
        if int(state["cumulative_commands"]) >= self.budget.max_commands and stop_reason is None:
            stop_reason = "COMMAND_BUDGET_EXHAUSTED"
        if int(state["cumulative_stdout_bytes"]) >= self.budget.max_stdout_bytes and stop_reason is None:
            stop_reason = "STDOUT_BUDGET_EXHAUSTED"
        if int(state["cumulative_stderr_bytes"]) >= self.budget.max_stderr_bytes and stop_reason is None:
            stop_reason = "STDERR_BUDGET_EXHAUSTED"
        if elapsed >= self.budget.max_wall_seconds and stop_reason is None:
            stop_reason = "WALL_TIME_BUDGET_EXHAUSTED"
        state["stop_reason"] = stop_reason
        state["state_identity"] = semantic_identity({
            "iterations": iterations,
            "cumulative_commands": state["cumulative_commands"],
            "cumulative_stdout_bytes": state["cumulative_stdout_bytes"],
            "cumulative_stderr_bytes": state["cumulative_stderr_bytes"],
            "stop_reason": stop_reason,
        })
        self.path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return state
