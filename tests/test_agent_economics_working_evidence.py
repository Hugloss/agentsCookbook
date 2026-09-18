from scripts.agent_economics.working_evidence import (
    SCHEMA,
    new_working_evidence,
    validate_working_evidence,
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
