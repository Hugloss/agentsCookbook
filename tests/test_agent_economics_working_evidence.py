from scripts.agent_economics.working_evidence import (
    SCHEMA,
    dirty_gate_delta_facts,
    provider_reference,
    repeated_action_without_new_evidence,
    validate_provider_reference,
    new_working_evidence,
    validate_invalidation,\n    validate_working_evidence,
)


def test_working_evidence_is_small_file_oriented_task_state() -> None:
    payload = new_working_evidence(goal="reduce repeated verification discovery")

    assert payload == {
        "schema": SCHEMA,
        "task": {"goal": "reduce repeated verification discovery"},
        "known": [],
        "decisions": [],
        "remaining": [],
    }
    assert validate_working_evidence(payload) == []


def test_working_evidence_rejects_repository_intelligence_copies() -> None:
    payload = new_working_evidence(goal="keep ownership singular")
    payload["ownership_graph"] = {"copied": True}

    errors = validate_working_evidence(payload)

    assert any("must not duplicate repository intelligence" in error for error in errors)


def test_repository_generation_invalidation_requires_provider_reference() -> None:
    errors = validate_invalidation({"kind": "repository-generation"})

    assert errors == [
        "repository-generation invalidation requires provider_reference; "
        "working evidence must not own repository generation"
    ]
    assert validate_invalidation(
        {
            "kind": "repository-generation",
            "provider_reference": "hashmarks:repository-generation",
        }
    ) == []


def test_environment_lifetime_is_task_local_and_does_not_need_repository_owner() -> None:
    assert validate_invalidation({"kind": "environment-change"}) == []


def test_provider_reference_points_to_repository_evidence_without_copying_it() -> None:
    reference = provider_reference(
        provider="hashmarks",
        evidence_identity="sha256:evidence",
        repository_identity="sha256:repository",
        generation=42,
    )

    assert reference == {
        "provider": "hashmarks",
        "evidence_identity": "sha256:evidence",
        "repository_identity": "sha256:repository",
        "generation": 42,
    }
    assert validate_provider_reference(reference) == []


def test_provider_reference_rejects_embedded_repository_facts() -> None:
    errors = validate_provider_reference(
        {
            "provider": "hashmarks",
            "evidence_identity": "sha256:evidence",
            "ownership_graph": {"copied": True},
        }
    )

    assert errors == [
        "provider reference must not embed repository intelligence: ownership_graph"
    ]


def test_identical_acquisition_without_new_evidence_is_detected() -> None:
    reference = provider_reference(
        provider="hashmarks",
        evidence_identity="sha256:delta-a",
        generation=42,
    )
    previous = {
        "action": "discover-related-tests",
        "inputs": ["src/b.py", "src/a.py"],
        "evidence_references": [reference],
    }
    current = {
        "action": "discover-related-tests",
        "inputs": ["src/a.py", "src/b.py"],
        "evidence_references": [reference],
    }

    assert repeated_action_without_new_evidence(previous, current) is True


def test_new_provider_evidence_allows_same_acquisition_to_be_reconsidered() -> None:
    previous = {
        "action": "repository-typecheck",
        "inputs": ["pyproject.toml"],
        "evidence_references": [
            {"provider": "hashmarks", "evidence_identity": "sha256:generation-41"}
        ],
    }
    current = {
        "action": "repository-typecheck",
        "inputs": ["pyproject.toml"],
        "evidence_references": [
            {"provider": "hashmarks", "evidence_identity": "sha256:generation-42"}
        ],
    }

    assert repeated_action_without_new_evidence(previous, current) is False


def test_dirty_gate_facts_do_not_treat_same_count_as_same_diagnostics() -> None:
    facts = dirty_gate_delta_facts(
        {
            "diagnostics": {
                "before_count": 1841,
                "after_count": 1841,
                "added": [{"identity": "new-a"}, {"identity": "new-b"}],
                "removed": [{"identity": "old-a"}, {"identity": "old-b"}],
                "unchanged_count": 1839,
                "added_in_changed_scope": [],
            }
        }
    )

    assert facts == {
        "usable": True,
        "global_before_count": 1841,
        "global_after_count": 1841,
        "new_diagnostics": 2,
        "removed_diagnostics": 2,
        "new_diagnostics_in_changed_scope": 0,
        "unchanged_diagnostics": 1839,
    }


def test_dirty_gate_facts_require_provider_delta_shape() -> None:
    assert dirty_gate_delta_facts({"diagnostics": {"before_count": 10}}) == {
        "usable": False,
        "reason": "invalid-added-diagnostics",
    }
