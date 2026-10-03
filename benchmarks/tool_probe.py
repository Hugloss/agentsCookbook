"""Prepare separate, tool-required OpenCode diagnostic suites."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from benchmarks.harness.identity import canonical_json, digest
from benchmarks.harness.oracle_reviews import validate_oracle_reviews
from benchmarks.harness.suite import load_suite


class ToolProbeError(ValueError):
    pass


DEFAULT_TASKS = (
    "locate-prefix-path-enumerator",
    "locate-directory-pruning",
    "locate-resource-invalidation",
)
REQUIRED_TOOLS = {"hashmarks": "hashmarks_task_evidence", "enola": "enola_explore"}


def prepare_tool_probe_suite(
    *, source_suite: Path, destination: Path, subject: str,
    task_ids: tuple[str, ...] = DEFAULT_TASKS,
) -> dict[str, Any]:
    if subject not in REQUIRED_TOOLS:
        raise ToolProbeError(f"unsupported tool-probe subject: {subject}")
    suite = load_suite(source_suite)
    validate_oracle_reviews(suite, require_complete=True)
    if not task_ids or len(set(task_ids)) != len(task_ids):
        raise ToolProbeError("select unique tool-probe tasks")
    unknown = set(task_ids) - set(suite.tasks)
    if unknown:
        raise ToolProbeError("unknown tool-probe tasks: " + ", ".join(sorted(unknown)))
    unsupported = set(task_ids) - set(DEFAULT_TASKS)
    if unsupported:
        raise ToolProbeError(
            "tool-probe tasks need a reviewed diagnostic design: "
            + ", ".join(sorted(unsupported))
        )
    for task_id in task_ids:
        if suite.tasks[task_id]["oracle"]["adapter"] != "repository-location-json":
            raise ToolProbeError(f"tool-probe task needs a location oracle: {task_id}")
    destination = destination.resolve()
    if destination.exists():
        raise ToolProbeError(f"tool-probe destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".tool-probe-", dir=destination.parent))
    required_tool = REQUIRED_TOOLS[subject]
    try:
        experiment = {
            "id": f"repository-intelligence-{subject}-required-tool-probe-v1",
            "version": 1,
            "suite": "repository-intelligence-tool-probe",
            "oracle_reviews": "qualification/oracle-reviews.json",
            "tasks": list(task_ids),
            "conditions": [{
                "id": f"{subject}-opencode-native-required",
                "subject": subject,
                "agent": "opencode-native",
                "trials": 3,
                "replicate_ids": [9101, 9102, 9103],
            }],
            "scoring": {
                "id": "repository-intelligence-tool-probe-score",
                "version": 1,
                "metrics": ["task_success", "subject_tool_invoked", "subject_mcp_calls"],
            },
        }
        (temporary / "experiment.json").write_bytes(canonical_json(experiment))
        for kind in ("tasks", "agents", "subjects", "qualification"):
            (temporary / kind).mkdir()
        (temporary / "agents/opencode-native.json").write_bytes(
            canonical_json(suite.agents["opencode-native"])
        )
        (temporary / f"subjects/{subject}.json").write_bytes(
            canonical_json(suite.subjects[subject])
        )
        source_reviews = json.loads(
            (suite.root / "qualification/oracle-reviews.json").read_text(encoding="utf-8")
        )
        reviews = {"schema": "agents-cookbook-oracle-reviews.v1", "tasks": {}}
        for task_id in task_ids:
            original = suite.tasks[task_id]
            task = dict(original)
            task["version"] = int(task["version"]) + 1
            task["prompt"] = (
                f"Diagnostic tool requirement: call {required_tool} for this repository "
                "task before using file search. Inspect source evidence before answering. "
                "The tool call is required even if you believe you already know the answer.\n\n"
                + str(original["prompt"])
            )
            (temporary / "tasks" / f"{task_id}.json").write_bytes(canonical_json(task))
            original_review = source_reviews["tasks"][task_id]
            reviews["tasks"][task_id] = {
                "task_digest": digest(task),
                "repository": task["repository"],
                "owner": original_review["owner"],
                "alternatives": original_review["alternatives"],
                "evidence": original_review["evidence"],
                "review_requirement": original_review["review_requirement"],
                "reviews": [],
            }
        (temporary / "qualification/oracle-reviews.json").write_bytes(canonical_json(reviews))
        (temporary / "score.py").write_text(
            "from pathlib import Path\n"
            "from benchmarks.tool_probe_score import main\n"
            "if __name__ == '__main__':\n"
            "    raise SystemExit(main(Path(__file__).resolve().parent))\n",
            encoding="utf-8",
        )
        environment_lines = [
            "# Copy this file, set the local subject source, and run from agentsCookbook.",
        ]
        if subject == "hashmarks":
            environment_lines.append("HASHMARKS_BENCH_SOURCE=/absolute/path/to/Hashmarks")
        environment_lines.extend([
            "BENCHMARK_AGENT=opencode-native",
            "BENCHMARK_OPENCODE_AGENT=build",
            "BENCHMARK_PASSTHROUGH_ENV_KEYS=",
            f"BENCHMARK_SUITE_PATH={destination}",
            f"BENCHMARK_CAMPAIGN_ROOT=.benchmark-runs/{subject}-required-tool-probe-v1",
            "BENCHMARK_HARNESS_REPO_ROOT=.",
            f"BENCHMARK_SCORE_SCRIPT_PATH={destination / 'score.py'}",
            "BENCHMARK_SCORE_OUTPUT_PATH=score.json",
        ])
        (temporary / ".env.example").write_text(
            "\n".join(environment_lines) + "\n", encoding="utf-8"
        )
        provenance = {
            "purpose": "diagnostic-only; excluded from heldout score",
            "source_suite": str(suite.root),
            "source_experiment_sha256": digest(suite.experiment),
            "subject": subject,
            "required_tool": required_tool,
            "tasks": list(task_ids),
            "replicates_per_task": 3,
            "oracle_reviews": "pending-independent-review",
        }
        (temporary / "diagnostic-source.json").write_bytes(canonical_json(provenance))
        load_suite(temporary)
        os.rename(temporary, destination)
        return provenance
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
