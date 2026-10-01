"""Independent deterministic benchmark oracles."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benchmarks.harness.identity import canonical_json
from benchmarks.harness.model import Observation, ParticipantIdentity, TrialContext
from scripts.agent_economics.bounded_process import ProcessLimits, run_bounded


def _text(payload: bytes) -> str:
    return payload.decode("utf-8", errors="replace")


def _parse_repository_location_message(
    value: str,
) -> tuple[dict[str, Any] | None, bool, str]:
    stripped = value.strip()
    format_compliant = True
    payload = stripped
    if stripped.startswith("```"):
        format_compliant = False
        lines = stripped.splitlines()
        if len(lines) < 3 or lines[0] != "```json" or lines[-1] != "```":
            return None, False, "answer is not one bare JSON object or one json fence"
        payload = "\n".join(lines[1:-1]).strip()
        if "```" in payload:
            return None, False, "answer contains nested or multiple code fences"
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        return None, False, f"agent final_message is not JSON: {exc.msg}"
    if not isinstance(parsed, dict):
        return None, False, "agent final_message JSON is not an object"
    return parsed, format_compliant, ""


def _normalize_repository_location(
    actual: dict[str, Any],
    *,
    workspace: Path,
) -> tuple[dict[str, str] | None, str | None]:
    if set(actual) != {"path", "symbol"}:
        return None, "repository location must contain exactly path and symbol"
    raw_path = actual.get("path")
    raw_symbol = actual.get("symbol")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None, "repository location path must be a non-empty string"
    if not isinstance(raw_symbol, str) or not raw_symbol.strip():
        return None, "repository location symbol must be a non-empty string"

    workspace_root = workspace.resolve()
    candidate = Path(raw_path.strip())
    resolved = candidate.resolve() if candidate.is_absolute() else (workspace_root / candidate).resolve()
    try:
        relative = resolved.relative_to(workspace_root)
    except ValueError:
        return None, "repository location path escapes the trial workspace"
    if relative == Path("."):
        return None, "repository location path must identify a repository file"

    symbol = raw_symbol.strip().rsplit(".", 1)[-1]
    if not symbol:
        return None, "repository location symbol is empty after qualification"
    return {"path": relative.as_posix(), "symbol": symbol}, None


@dataclass(frozen=True)
class RepositoryLocationOracle:
    participant_id: str
    version: str
    expected: dict[str, Any]

    def identity(self) -> ParticipantIdentity:
        return ParticipantIdentity(
            self.participant_id,
            "oracle",
            self.version,
            {"kind": "repository-location-json", "expected": self.expected},
        )

    def healthcheck(self, context: TrialContext) -> Observation:
        normalized, reason = _normalize_repository_location(
            self.expected,
            workspace=context.workspace,
        )
        healthy = normalized == self.expected and reason is None
        return Observation(
            {
                "healthy": healthy,
                "reason": None if healthy else reason or "expected repository location is not canonical",
            },
            "",
        )

    def grade(self, context: TrialContext, observation: Observation) -> Observation:
        final_message = observation.payload.get("final_message")
        if not isinstance(final_message, str):
            return Observation(
                {
                    "passed": False,
                    "valid": True,
                    "semantic_success": False,
                    "format_compliant": False,
                    "reason": "agent final_message is missing",
                },
                "",
            )

        actual, format_compliant, parse_reason = _parse_repository_location_message(
            final_message
        )
        if actual is None:
            return Observation(
                {
                    "passed": False,
                    "valid": True,
                    "semantic_success": False,
                    "format_compliant": format_compliant,
                    "reason": parse_reason,
                    "actual_text": final_message,
                },
                "",
            )

        structure_compliant = (
            set(actual) == {"path", "symbol"}
            and isinstance(actual.get("path"), str)
            and bool(actual["path"].strip())
            and isinstance(actual.get("symbol"), str)
            and bool(actual["symbol"].strip())
        )
        format_compliant = format_compliant and structure_compliant
        normalized_actual, normalize_reason = _normalize_repository_location(
            actual,
            workspace=context.workspace,
        )
        semantic_success = normalized_actual == self.expected
        reason = None if semantic_success else (
            normalize_reason or "repository location differs from frozen oracle"
        )
        return Observation(
            {
                "passed": semantic_success,
                "valid": True,
                "semantic_success": semantic_success,
                "format_compliant": format_compliant,
                "expected": self.expected,
                "actual": actual,
                "normalized_actual": normalized_actual,
                "reason": reason,
            },
            json.dumps(normalized_actual or actual, sort_keys=True),
        )


@dataclass(frozen=True)
class ExpectedJsonOracle:
    participant_id: str
    version: str
    expected: dict[str, Any]

    def identity(self) -> ParticipantIdentity:
        return ParticipantIdentity(
            self.participant_id,
            "oracle",
            self.version,
            {"kind": "expected-json", "expected": self.expected},
        )

    def healthcheck(self, context: TrialContext) -> Observation:
        try:
            canonical_json(self.expected)
        except (TypeError, ValueError) as exc:
            return Observation(
                {"healthy": False, "reason": f"invalid expected JSON: {exc}"},
                "",
            )
        return Observation({"healthy": True}, "")

    def grade(self, context: TrialContext, observation: Observation) -> Observation:
        final_message = observation.payload.get("final_message")
        if not isinstance(final_message, str):
            return Observation(
                {
                    "passed": False,
                    "valid": True,
                    "reason": "agent final_message is missing",
                },
                "",
            )
        try:
            actual = json.loads(final_message)
        except json.JSONDecodeError as exc:
            return Observation(
                {
                    "passed": False,
                    "valid": True,
                    "reason": f"agent final_message is not JSON: {exc.msg}",
                    "actual_text": final_message,
                },
                "",
            )
        passed = actual == self.expected
        return Observation(
            {
                "passed": passed,
                "valid": True,
                "expected": self.expected,
                "actual": actual,
                "reason": None if passed else "JSON answer differs from frozen oracle",
            },
            json.dumps(actual, sort_keys=True),
        )


@dataclass(frozen=True)
class CommandOracle:
    participant_id: str
    version: str
    health_argv: tuple[str, ...]
    grade_argv: tuple[str, ...]
    timeout_seconds: int = 60
    valid_exit_codes: tuple[int, ...] | None = None
    result_format: str = "text"

    def identity(self) -> ParticipantIdentity:
        return ParticipantIdentity(
            self.participant_id,
            "oracle",
            self.version,
            {"health_argv": self.health_argv, "grade_argv": self.grade_argv,
             "result_format": self.result_format},
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
            inherit_environment=False,
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
        valid = (
            not result.executable_missing
            and not result.timed_out
            and not result.stdout_truncated
            and not result.stderr_truncated
            and result.return_code is not None
            and (
                self.valid_exit_codes is None
                or result.return_code in self.valid_exit_codes
            )
        )
        passed = valid and result.return_code == 0
        detail: dict[str, Any] = {}
        if valid and self.result_format == "lexigram-v1":
            try:
                value = json.loads(_text(result.stdout))
                if (
                    not isinstance(value, dict)
                    or value.get("schema") != "agents-cookbook-lexigram-oracle.v1"
                    or not isinstance(value.get("passed"), bool)
                    or value["passed"] != passed
                    or not isinstance(value.get("rubric"), dict)
                    or not isinstance(value.get("reason"), str)
                ):
                    raise ValueError("invalid structured oracle result")
                detail = {"rubric": value["rubric"], "reason": value["reason"]}
            except (ValueError, json.JSONDecodeError):
                valid = False
                passed = False
        return Observation(
            {
                "passed": passed,
                "valid": valid,
                **detail,
                "process": result.metrics(),
                "stderr": _text(result.stderr),
            },
            _text(result.stdout),
            {"duration_ms": result.elapsed_ms},
        )
