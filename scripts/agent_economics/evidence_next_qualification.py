from __future__ import annotations

from .evidence_next import EvidenceNextError, next_evidence


def qualify() -> None:
    payload = {
        "schema": {"name": "agent-economics-probe", "version": 1},
        "tool": {"name": "quality-debt", "version": "0.15.0"},
        "candidates": [
            {
                "target": "pkg/hot.py",
                "required_next_evidence": [{
                    "kind": "test_focus",
                    "target": "pkg/hot.py",
                    "reason": "debt magnitude does not establish edit safety",
                }],
            },
            {
                "target": "pkg/other.py",
                "required_next_evidence": [{
                    "kind": "test_focus",
                    "target": "pkg/other.py",
                    "reason": "recover test ownership",
                }],
            },
        ],
    }
    profile = {
        "repository": {"package_roots": ["pkg"], "test_roots": ["tests"]},
    }
    try:
        next_evidence(payload, profile=profile)
    except EvidenceNextError:
        pass
    else:
        raise AssertionError("multiple candidates without --target must fail closed")

    multiple_required = dict(payload)
    multiple_required["candidates"] = [{
        "target": "pkg/hot.py",
        "required_next_evidence": [
            {"kind": "test_focus", "reason": "first"},
            {"kind": "test_focus", "reason": "second"},
        ],
    }]
    try:
        next_evidence(multiple_required, target="pkg/hot.py", profile=profile)
    except EvidenceNextError:
        pass
    else:
        raise AssertionError("multiple required-next-evidence items must fail closed")

    result = next_evidence(payload, target="pkg/hot.py", profile=profile)
    assert result["next_evidence"]["kind"] == "test_focus"
    assert result["command"] == [
        "python", "-m", "agent_economics", "test-focus",
        "--repository-root", ".", "--source-root", "pkg",
        "--tests-root", "tests", "--changed-path", "pkg/hot.py",
        "--artifact-path", ".agent-artifacts/test-focus.json",
    ]
    assert result["unresolved"] == []
    assert result["interpretation"]["does_not_execute_command"] is True
    assert result["interpretation"]["does_not_authorize_edit"] is True

    review_only_profile = {
        "status": "REVIEW_REQUIRED",
        "repository": {"package_roots": ["pkg"], "test_roots": ["tests"]},
        "interpretation": {"suggestion_is_not_repository_authority": True},
    }
    review_only = next_evidence(payload, target="pkg/hot.py", profile=review_only_profile)
    assert review_only["command"] is None
    assert review_only["unresolved"] == [
        "profile_review_required",
        "profile_not_repository_authority",
    ]

    missing_profile = next_evidence(payload, target="pkg/hot.py")
    assert missing_profile["command"] is None
    assert missing_profile["unresolved"] == ["profile"]

    ambiguous = next_evidence(
        payload,
        target="pkg/hot.py",
        profile={"repository": {"package_roots": ["pkg", "other"], "test_roots": ["tests"]}},
    )
    assert ambiguous["command"] is None
    assert ambiguous["unresolved"] == ["single_package_root"]

    try:
        next_evidence(payload, target="missing.py", profile=profile)
    except EvidenceNextError:
        pass
    else:
        raise AssertionError("unknown target must fail closed")

    unsupported = dict(payload)
    unsupported["candidates"] = [{
        "target": "pkg/hot.py",
        "required_next_evidence": [{"kind": "invented", "reason": "fixture"}],
    }]
    result = next_evidence(unsupported, profile=profile)
    assert result["command"] is None
    assert result["unresolved"] == ["unsupported_next_evidence:invented"]

    print('{"cases":8,"status":"PASS","tool":"evidence-next"}')


if __name__ == "__main__":
    qualify()
