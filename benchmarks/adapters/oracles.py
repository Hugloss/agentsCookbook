"""Independent bounded command oracle with positive health and answer input."""
from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from benchmarks.harness.identity import canonical_json
from benchmarks.harness.model import Observation, ParticipantIdentity, TrialContext
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
        context: TrialContext,
        argv: tuple[str, ...],
        *,
        environment: dict[str, str] | None = None,
    ):
        effective_environment = dict(context.environment)
        if environment:
            effective_environment.update(environment)
        return run_bounded(
            repository_root=context.workspace,
            argv=argv,
            environment=effective_environment,
            limits=ProcessLimits(
                timeout_seconds=self.timeout_seconds,
                max_stdout_bytes=5_000_000,
                max_stderr_bytes=2_000_000,
            ),
        )

    def healthcheck(self, context: TrialContext) -> Observation:
        result = self._run(context, self.health_argv)
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

    def grade(self, context: TrialContext, observation: Observation) -> Observation:
        with tempfile.TemporaryDirectory(
            prefix="benchmark-oracle-",
            dir=context.environment.get("TMPDIR"),
        ) as tmp:
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
                context,
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
