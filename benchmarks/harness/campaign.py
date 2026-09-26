"""Resumable campaign identities, paths, and status."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .bundle import verify_bundle
from .identity import definition_id, execution_id
from .receipt import is_complete_receipt
from .suite import SuiteDefinition


class CampaignError(ValueError):
    pass


@dataclass(frozen=True)
class TrialSpec:
    experiment: dict[str, Any]
    task: dict[str, Any]
    condition: dict[str, Any]
    trial: int
    seed: int
    subject_identity: dict[str, Any]
    agent_identity: dict[str, Any]
    oracle_identity: dict[str, Any]
    harness_identity: dict[str, Any]
    environment_identity: dict[str, Any]
    mutation_identity: dict[str, Any] | None = None

    @property
    def definition_id(self) -> str:
        return definition_id(
            experiment=self.experiment,
            task=self.task,
            condition=self.condition,
            trial=self.trial,
            seed=self.seed,
        )

    @property
    def id(self) -> str:
        return execution_id(
            definition=self.definition_id,
            subject_identity=self.subject_identity,
            agent_identity=self.agent_identity,
            oracle_identity=self.oracle_identity,
            harness_identity=self.harness_identity,
            environment_identity=self.environment_identity,
            mutation_identity=self.mutation_identity,
        )


@dataclass(frozen=True)
class CampaignPaths:
    root: Path | None
    cache: Path | None
    work: Path | None
    results: Path

    def as_dict(self) -> dict[str, str | None]:
        return {
            "root": str(self.root) if self.root is not None else None,
            "cache": str(self.cache) if self.cache is not None else None,
            "work": str(self.work) if self.work is not None else None,
            "results": str(self.results),
        }


def pending(specs: list[TrialSpec], results_root: Path) -> list[TrialSpec]:
    return [
        spec
        for spec in specs
        if not is_complete_receipt(results_root / spec.id)
    ]


def resolve_campaign_paths(
    *,
    root: Path | None,
    cache: Path | None,
    work: Path | None,
    results: Path | None,
    need_execution: bool,
) -> CampaignPaths:
    if root is not None:
        if any(value is not None for value in (cache, work, results)):
            raise CampaignError(
                "--root cannot be combined with --cache, --work, or --results"
            )
        root = root.resolve()
        return CampaignPaths(
            root=root,
            cache=root / "cache" if need_execution else None,
            work=root / "work" if need_execution else None,
            results=root / "results",
        )

    if results is None:
        raise CampaignError("provide --root or --results")
    if need_execution and (cache is None or work is None):
        raise CampaignError(
            "execution requires --root or all of --cache, --work, and --results"
        )
    return CampaignPaths(
        root=None,
        cache=cache.resolve() if cache is not None else None,
        work=work.resolve() if work is not None else None,
        results=results.resolve(),
    )


def campaign_status(
    *,
    suite: SuiteDefinition,
    results_root: Path,
    selected_definitions: set[str],
) -> dict[str, Any]:
    all_rows = suite.trial_definitions()
    all_definitions = {
        str(row["definition_id"]): row for row in all_rows
    }
    definitions = {
        key: row
        for key, row in all_definitions.items()
        if key in selected_definitions
    }
    if set(definitions) != selected_definitions:
        raise CampaignError(
            "status selection contains definitions outside frozen suite"
        )

    receipts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    corrupt: list[dict[str, str]] = []
    foreign: list[dict[str, str]] = []
    if results_root.exists():
        for directory in sorted(
            path for path in results_root.iterdir() if path.is_dir()
        ):
            if directory.name.startswith("."):
                continue
            valid, reason = verify_bundle(directory)
            if not valid:
                corrupt.append(
                    {"directory": str(directory), "reason": str(reason)}
                )
                continue
            value = json.loads(
                (directory / "result.json").read_text(encoding="utf-8")
            )
            definition = value.get("definition_id")
            if not isinstance(definition, str):
                corrupt.append(
                    {
                        "directory": str(directory),
                        "reason": "verified bundle has no definition_id",
                    }
                )
                continue
            if definition in definitions:
                receipts[definition].append(value)
            elif definition not in all_definitions:
                foreign.append(
                    {
                        "directory": str(directory),
                        "definition_id": definition,
                    }
                )

    rows: list[dict[str, Any]] = []
    state_counts: Counter[str] = Counter()
    outcome_counts: Counter[str] = Counter()
    for definition, row in definitions.items():
        found = receipts.get(definition, [])
        if not found:
            state = "PENDING"
            outcome = None
            trial_ids: list[str] = []
        elif len(found) == 1:
            state = "COMPLETE"
            outcome = str(found[0].get("status"))
            outcome_counts[outcome] += 1
            trial_ids = [str(found[0].get("trial_id"))]
        else:
            state = "CONFLICT"
            outcome = None
            trial_ids = sorted(
                str(value.get("trial_id")) for value in found
            )
        state_counts[state] += 1
        rows.append(
            {
                "definition_id": definition,
                "task_id": row["task_id"],
                "condition_id": row["condition_id"],
                "trial": row["trial"],
                "state": state,
                "outcome": outcome,
                "trial_ids": trial_ids,
            }
        )

    return {
        "expected_trials": len(definitions),
        "complete_trials": state_counts["COMPLETE"],
        "pending_trials": state_counts["PENDING"],
        "conflicting_trials": state_counts["CONFLICT"],
        "outcomes": dict(sorted(outcome_counts.items())),
        "corrupt_bundles": corrupt,
        "foreign_bundles": foreign,
        "complete": (
            state_counts["COMPLETE"] == len(definitions)
            and not corrupt
            and state_counts["CONFLICT"] == 0
        ),
        "rows": sorted(
            rows,
            key=lambda value: (
                str(value["task_id"]),
                str(value["condition_id"]),
                int(value["trial"]),
            ),
        ),
    }
