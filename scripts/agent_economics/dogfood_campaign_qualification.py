from __future__ import annotations

import json
import tempfile
from copy import deepcopy
from pathlib import Path

from .agent_outcome_benchmark import BenchmarkError, Outcome
from .dogfood_campaign import DogfoodCampaignError, load_campaign, validate_campaign


def _expect_error(fn) -> None:
    try:
        fn()
    except BenchmarkError:
        return
    raise AssertionError("expected DogfoodCampaignError")


def _pair(
    task_id: str,
    scenario: str,
    repository_id: str,
    *,
    role: str = "primary",
    index: int,
) -> tuple[list[Outcome], dict[str, object]]:
    treatment_id = "p10"
    shared = dict(
        task_id=task_id,
        treatment_id=treatment_id,
        correct=True,
        repository_id=repository_id,
        task_fixture_id=f"fixture:{task_id}",
        corpus_id="corpus:v1",
        initial_source_id=f"source:{task_id}:initial",
        agent_profile="agent:v1",
        execution_environment_id="env:v1",
        oracle_opened_after_freeze=True,
    )
    baseline_run = f"session:{index}:baseline"
    bridge_run = f"session:{index}:bridge"
    baseline = Outcome(
        mode="baseline",
        run_id=baseline_run,
        final_source_id=f"source:{task_id}:baseline-final",
        ci_evidence_id=f"ci:{task_id}:baseline",
        **shared,
    )
    bridge = Outcome(
        mode="bridge",
        run_id=bridge_run,
        bridge_implementation_id="git:agentscookbook-main",
        manifest_id=f"manifest:{task_id}",
        local_qualification_id=f"local:{task_id}",
        final_source_id=f"source:{task_id}:bridge-final",
        ci_evidence_id=f"ci:{task_id}:bridge",
        local_ci_agree=True,
        **shared,
    )
    row = {
        "task_id": task_id,
        "treatment_id": treatment_id,
        "scenario": scenario,
        "repository_role": role,
        "repository_id": repository_id,
        "measurement_contract_id": "measurement:v1",
        "baseline_session_id": baseline_run,
        "bridge_session_id": bridge_run,
        "baseline_isolation_evidence_id": f"isolation:{task_id}:baseline",
        "bridge_isolation_evidence_id": f"isolation:{task_id}:bridge",
        "baseline_freeze_receipt_id": f"freeze:{task_id}:baseline",
        "bridge_freeze_receipt_id": f"freeze:{task_id}:bridge",
        "baseline_oracle_access_receipt_id": f"oracle:{task_id}:baseline",
        "bridge_oracle_access_receipt_id": f"oracle:{task_id}:bridge",
    }
    return [baseline, bridge], row


def _fixture() -> tuple[list[Outcome], dict[str, object]]:
    specs = [
        ("localized-python", "localized-assertion", "repo:hashmarks", "primary"),
        ("syntax-import", "syntax-import", "repo:hashmarks", "primary"),
        (
            "affected-dependent",
            "wrong-test-affected-dependent",
            "repo:hashmarks",
            "primary",
        ),
        (
            "focused-pass-broad-fail",
            "focused-pass-broad-fail",
            "repo:hashmarks",
            "primary",
        ),
        ("portable-localized", "localized-assertion", "repo:oh-goon", "independent"),
    ]
    outcomes: list[Outcome] = []
    tasks: list[dict[str, object]] = []
    for index, (task_id, scenario, repository_id, role) in enumerate(specs, start=1):
        pair, row = _pair(
            task_id,
            scenario,
            repository_id,
            role=role,
            index=index,
        )
        outcomes.extend(pair)
        tasks.append(row)
    campaign: dict[str, object] = {
        "schema": {"name": "agent-economics-dogfood-campaign", "version": 1},
        "campaign_id": "campaign:v1",
        "implementation_id": "git:agentscookbook-main",
        "corpus_id": "corpus:v1",
        "measurement_contract_id": "measurement:v1",
        "primary_repository_id": "repo:hashmarks",
        "tasks": tasks,
        "consumer_cleanup_evidence": [
            {"repository_id": "repo:hashmarks", "evidence_id": "cleanup:hashmarks"},
            {"repository_id": "repo:oh-goon", "evidence_id": "cleanup:oh-goon"},
        ],
        "final_agentscookbook_ci_evidence_id": "ci:agentscookbook:final",
    }
    return outcomes, campaign


def main() -> None:
    outcomes, campaign = _fixture()
    result = validate_campaign(outcomes, campaign)
    assert result["schema"]["version"] == 1
    assert result["paired_tasks"] == 5
    assert result["run_identities"] == 10
    assert result["independent_repositories"] == ["repo:oh-goon"]
    assert result["benchmark"]["promotion_evidence"]["strict_dogfood_protocol"] is True
    assert result["authority"]["automatic_promotion"] is False

    missing = deepcopy(campaign)
    missing["tasks"] = [
        row
        for row in campaign["tasks"]
        if row["scenario"] != "wrong-test-affected-dependent"
    ]
    _expect_error(lambda: validate_campaign(outcomes, missing))

    no_portability = deepcopy(campaign)
    no_portability["tasks"] = [
        row for row in campaign["tasks"] if row["repository_role"] == "primary"
    ]
    _expect_error(
        lambda: validate_campaign(outcomes[:8], no_portability)
    )

    duplicate_run = deepcopy(campaign)
    duplicate_run["tasks"][1]["baseline_session_id"] = campaign["tasks"][0][
        "baseline_session_id"
    ]
    _expect_error(lambda: validate_campaign(outcomes, duplicate_run))

    bad_measurement = deepcopy(campaign)
    bad_measurement["tasks"][0]["measurement_contract_id"] = "measurement:other"
    _expect_error(lambda: validate_campaign(outcomes, bad_measurement))

    no_cleanup = deepcopy(campaign)
    no_cleanup["consumer_cleanup_evidence"] = [
        {"repository_id": "repo:hashmarks", "evidence_id": "cleanup:hashmarks"}
    ]
    _expect_error(lambda: validate_campaign(outcomes, no_cleanup))

    mismatched_repo = list(outcomes)
    mismatched_repo[0] = Outcome(
        **{**mismatched_repo[0].__dict__, "repository_id": "repo:other"}
    )
    _expect_error(lambda: validate_campaign(mismatched_repo, campaign))

    reused_outcome_run = list(outcomes)
    reused_outcome_run[2] = Outcome(
        **{**reused_outcome_run[2].__dict__, "run_id": outcomes[0].run_id}
    )
    campaign_reused = deepcopy(campaign)
    campaign_reused["tasks"][1]["baseline_session_id"] = outcomes[0].run_id
    _expect_error(lambda: validate_campaign(reused_outcome_run, campaign_reused))

    unregistered = list(outcomes)
    extra_pair, _ = _pair(
        "extra",
        "localized-assertion",
        "repo:hashmarks",
        role="primary",
        index=99,
    )
    unregistered.extend(extra_pair)
    _expect_error(lambda: validate_campaign(unregistered, campaign))

    with tempfile.TemporaryDirectory() as raw:
        path = Path(raw) / "campaign.json"
        path.write_text(json.dumps(campaign), encoding="utf-8")
        assert load_campaign(path) == campaign

    print(
        json.dumps(
            {
                "status": "PASS",
                "paired_tasks": 5,
                "primary_scenarios": 4,
                "independent_repositories": 1,
                "strict_campaign": True,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
