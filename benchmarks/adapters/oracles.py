"""Independent bounded command oracle with positive health and answer input."""
from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from benchmarks.harness.identity import canonical_json
from benchmarks.harness.model import Observation, ParticipantIdentity
from scripts.agent_economics.bounded_process import ProcessLimits, run_bounded


def _text(payload: bytes) -> str:
    return payload.decode("utf-8", errors="replace")


@dataclass(frozen=True)
class CommandOracle:
    participant_id: str
    version: str
    health_argv: tuple[str, ...]
    grade_argv: tuple[str, ...]
    timeout_seconds: int = 60

    def identity(self) -> ParticipantIdentity:
        return ParticipantIdentity(
            self.participant_id,
            "oracle",
            self.version,
            {"health_argv": self.health_argv, "grade_argv": self.grade_argv},
        )

    def _run(
        self,
        workspace: str,
        argv: tuple[str, ...],
        *,
        environment: dict[str, str] | None = None,
    ):
        return run_bounded(
            repository_root=Path(workspace),
            argv=argv,
            environment=environment,
            limits=ProcessLimits(
                timeout_seconds=self.timeout_seconds,
                max_stdout_bytes=5_000_000,
                max_stderr_bytes=2_000_000,
            ),
        )

    def healthcheck(self, workspace: str) -> Observation:
        result = self._run(workspace, self.health_argv)
        healthy = (
            not result.executable_missing
            and not result.timed_out
            and result.return_code == 0
            and not result.stdout_truncated
            and not result.stderr_truncated
        )
        return Observation(
            {
                "healthy": healthy,
                "process": result.metrics(),
                "stderr": _text(result.stderr),
            },
            _text(result.stdout),
            {"duration_ms": result.elapsed_ms},
        )

    def grade(self, workspace: str, observation: Observation) -> Observation:
        with tempfile.TemporaryDirectory(prefix="benchmark-oracle-") as tmp:
            observation_path = Path(tmp) / "observation.json"
            observation_path.write_bytes(
                canonical_json(
                    {
                        "payload": observation.payload,
                        "raw": observation.raw,
                        "measurements": observation.measurements,
                    }
                )
            )
            result = self._run(
                workspace,
                self.grade_argv,
                environment={"BENCHMARK_OBSERVATION_PATH": str(observation_path)},
            )
        passed = (
            not result.executable_missing
            and not result.timed_out
            and result.return_code == 0
            and not result.stdout_truncated
            and not result.stderr_truncated
        )
        return Observation(
            {
                "passed": passed,
                "process": result.metrics(),
                "stderr": _text(result.stderr),
            },
            _text(result.stdout),
            {"duration_ms": result.elapsed_ms},
        )
