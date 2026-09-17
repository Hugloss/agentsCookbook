from __future__ import annotations

import argparse
import json
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .refactor_focus_models import MATCH_AUTHORITY
from .refactor_focus_workflow import refactor_focus_audit

Expectation = Literal[
    "relevant_confirmed",
    "relationship_supporting",
    "heuristic_candidate",
    "irrelevant",
    "unsupported",
]


@dataclass(frozen=True)
class QualificationCase:
    name: str
    source_path: str
    expected_test_path: str
    expectation: Expectation
    expected_match_type: str | None = None


CASES = (
    QualificationCase(
        "exact_import",
        "src/samplepkg/exact_case.py",
        "tests/test_exact_relation.py",
        "relevant_confirmed",
        "import_exact",
    ),
    QualificationCase(
        "helper_loader",
        "src/samplepkg/helper_case.py",
        "tests/test_helper_behavior.py",
        "relevant_confirmed",
        "support_loader",
    ),
    QualificationCase(
        "package_init_import",
        "src/samplepkg/package/__init__.py",
        "tests/test_package_import_behavior.py",
        "relevant_confirmed",
        "import_exact",
    ),
    QualificationCase(
        "exact_overrides_same_name",
        "src/samplepkg/exact_named.py",
        "tests/test_exact_named.py",
        "relevant_confirmed",
        "import_exact",
    ),
    QualificationCase(
        "mirrored_path_only",
        "src/samplepkg/mirrored_only.py",
        "tests/test_mirrored_only.py",
        "relationship_supporting",
        "mirrored_path",
    ),
    QualificationCase(
        "direct_name_only",
        "src/samplepkg/name_only_case.py",
        "tests/nested/test_name_only_case.py",
        "relationship_supporting",
        "direct_name",
    ),
    QualificationCase(
        "transitive_owner",
        "src/samplepkg/transitive_target.py",
        "tests/test_transitive_bridge_target.py",
        "relationship_supporting",
        "transitive_owner",
    ),
    QualificationCase(
        "feature_candidate",
        "src/samplepkg/feature_alpha_beta.py",
        "tests/test_feature_alpha_beta_behavior.py",
        "heuristic_candidate",
        "feature_fallback",
    ),
    QualificationCase(
        "same_name_without_import",
        "src/samplepkg/shadow_name.py",
        "tests/test_shadow_name.py",
        "irrelevant",
        "mirrored_path",
    ),
    QualificationCase(
        "unrelated_negative",
        "src/samplepkg/unrelated.py",
        "tests/test_other_behavior.py",
        "irrelevant",
        None,
    ),
    QualificationCase(
        "unsupported_importlib",
        "src/samplepkg/unsupported_dynamic.py",
        "tests/test_runtime_dynamic_check.py",
        "unsupported",
        None,
    ),
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _oversized_source(*lines: str, minimum_lines: int = 25) -> str:
    body = list(lines)
    while len(body) < minimum_lines:
        body.append(f"# qualification padding {len(body) + 1}")
    return "\n".join(body) + "\n"


def materialize_corpus(root: Path) -> None:
    _write(root / "src/samplepkg/__init__.py", "# qualification package\n")

    _write(root / "src/samplepkg/exact_case.py", _oversized_source("VALUE = 1"))
    _write(root / "tests/test_exact_relation.py", "import samplepkg.exact_case\n")

    _write(root / "src/samplepkg/helper_case.py", _oversized_source("VALUE = 2"))
    _write(root / "tests/support/helper_loader.py", "import samplepkg.helper_case\n")
    _write(root / "tests/test_helper_behavior.py", "import checks.support.helper_loader\n")

    _write(
        root / "src/samplepkg/package/__init__.py",
        _oversized_source("PACKAGE_VALUE = 3"),
    )
    _write(root / "tests/test_package_import_behavior.py", "import samplepkg.package\n")

    _write(root / "src/samplepkg/exact_named.py", _oversized_source("VALUE = 4"))
    _write(root / "tests/test_exact_named.py", "import samplepkg.exact_named\n")

    _write(root / "src/samplepkg/mirrored_only.py", _oversized_source("VALUE = 5"))
    _write(root / "tests/test_mirrored_only.py", "def test_placeholder():\n    assert True\n")

    _write(root / "src/samplepkg/name_only_case.py", _oversized_source("VALUE = 6"))
    _write(
        root / "tests/nested/test_name_only_case.py",
        "def test_placeholder():\n    assert True\n",
    )

    _write(root / "src/samplepkg/transitive_target.py", _oversized_source("VALUE = 7"))
    _write(
        root / "src/samplepkg/transitive_bridge.py",
        "import samplepkg.transitive_target\n",
    )
    _write(
        root / "tests/test_transitive_bridge_target.py",
        "import samplepkg.transitive_bridge\n",
    )

    _write(root / "src/samplepkg/feature_alpha_beta.py", _oversized_source("VALUE = 8"))
    _write(
        root / "tests/test_feature_alpha_beta_behavior.py",
        "def test_placeholder():\n    assert True\n",
    )

    _write(root / "src/samplepkg/shadow_name.py", _oversized_source("VALUE = 9"))
    _write(root / "tests/test_shadow_name.py", "def test_unrelated():\n    assert True\n")

    _write(root / "src/samplepkg/unrelated.py", _oversized_source("VALUE = 10"))
    _write(root / "tests/test_other_behavior.py", "def test_other():\n    assert True\n")

    _write(
        root / "src/samplepkg/unsupported_dynamic.py",
        _oversized_source("VALUE = 11"),
    )
    _write(
        root / "tests/test_runtime_dynamic_check.py",
        'import importlib\n\ndef test_dynamic():\n    assert importlib.import_module("samplepkg.unsupported_dynamic")\n',
    )


def _run_probe(root: Path, *, top_n: int, artifact_name: str) -> tuple[dict[str, object], float]:
    artifact_path = root / artifact_name
    exit_codes: list[int] = []

    def emit(_level: str, _event: str, **_payload: object) -> None:
        return None

    def exit_code(code: int) -> None:
        exit_codes.append(code)

    started = time.perf_counter()
    refactor_focus_audit(
        emit=emit,
        exit_code=exit_code,
        source_root=root / "src/samplepkg",
        tests_root=root / "tests",
        repository_root=root,
        artifact_path=artifact_path,
        package_name="samplepkg",
        tests_package_name="checks",
        file_line_threshold=20,
        function_line_threshold=10,
        top_n=top_n,
        transitive_max_depth=2,
    )
    elapsed = time.perf_counter() - started
    if exit_codes != [0]:
        raise RuntimeError(f"probe exit codes were {exit_codes!r}")
    return json.loads(artifact_path.read_text(encoding="utf-8")), elapsed


def _classification(
    case: QualificationCase,
    row: dict[str, object],
) -> tuple[str, dict[str, object] | None, list[str]]:
    matches = row.get("matches", [])
    assert isinstance(matches, list)
    expected_match = next(
        (
            match
            for match in matches
            if isinstance(match, dict)
            and match.get("test_path") == case.expected_test_path
        ),
        None,
    )
    failures: list[str] = []

    if expected_match is not None:
        match_type = str(expected_match.get("match_type"))
        expected_authority = MATCH_AUTHORITY.get(match_type, "candidate")
        if expected_match.get("evidence_authority") != expected_authority:
            failures.append(
                f"authority mismatch: {match_type} expected {expected_authority} "
                f"got {expected_match.get('evidence_authority')}"
            )
        if case.expected_match_type and match_type != case.expected_match_type:
            failures.append(
                f"match type expected {case.expected_match_type} got {match_type}"
            )

    authority = expected_match.get("evidence_authority") if expected_match else None
    if case.expectation == "relevant_confirmed":
        classification = "TRUE_RELEVANT" if authority == "confirmed" else "MISSED_RELEVANT"
    elif authority == "confirmed":
        classification = "FALSE_RELEVANT"
    elif case.expectation == "irrelevant" and expected_match is None:
        classification = "TRUE_NEGATIVE"
    else:
        classification = "UNKNOWN"

    if authority != "confirmed":
        forbidden_actions = {
            "split_existing_test_file",
            "update_existing_test_file",
            "keep_existing_test_file",
        }
        if row.get("has_corresponding_tests"):
            failures.append("non-confirmed evidence set has_corresponding_tests=true")
        if row.get("test_sync_required_if_split"):
            failures.append("non-confirmed evidence set test_sync_required_if_split=true")
        if row.get("max_test_lines") != 0:
            failures.append("non-confirmed evidence influenced max_test_lines")
        if row.get("recommended_test_action") in forbidden_actions:
            failures.append("non-confirmed evidence prescribed a confirmed-test action")

    return classification, expected_match, failures


def qualify(artifact_path: Path | None = None) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="agent-economics-refactor-focus-") as tmp:
        root = Path(tmp)
        materialize_corpus(root)

        full, elapsed = _run_probe(root, top_n=100, artifact_name="full.json")
        bounded, bounded_elapsed = _run_probe(root, top_n=3, artifact_name="bounded.json")

        rows = full["rows"]
        assert isinstance(rows, list)
        rows_by_source = {
            row["source_path"]: row
            for row in rows
            if isinstance(row, dict) and isinstance(row.get("source_path"), str)
        }

        counts = {
            "TRUE_RELEVANT": 0,
            "FALSE_RELEVANT": 0,
            "MISSED_RELEVANT": 0,
            "UNKNOWN": 0,
            "TRUE_NEGATIVE": 0,
        }
        case_results: list[dict[str, object]] = []
        failures: list[str] = []

        for case in CASES:
            row = rows_by_source.get(case.source_path)
            if row is None:
                counts["MISSED_RELEVANT"] += int(case.expectation == "relevant_confirmed")
                failures.append(f"{case.name}: source row missing: {case.source_path}")
                case_results.append(
                    {
                        "name": case.name,
                        "classification": "ROW_MISSING",
                        "expectation": case.expectation,
                    }
                )
                continue

            classification, match, case_failures = _classification(case, row)
            counts[classification] += 1
            failures.extend(f"{case.name}: {message}" for message in case_failures)
            case_results.append(
                {
                    "name": case.name,
                    "expectation": case.expectation,
                    "classification": classification,
                    "source_path": case.source_path,
                    "expected_test_path": case.expected_test_path,
                    "observed_match": match,
                    "correspondence_status": row.get("correspondence_status"),
                    "recommended_test_action": row.get("recommended_test_action"),
                    "recommended_strategy": row.get("recommended_strategy"),
                }
            )

        if counts["FALSE_RELEVANT"]:
            failures.append("qualification introduced false authority")
        if counts["MISSED_RELEVANT"]:
            failures.append("qualification missed a relationship that must be confirmed")

        tp = counts["TRUE_RELEVANT"]
        fp = counts["FALSE_RELEVANT"]
        fn = counts["MISSED_RELEVANT"]
        precision = tp / (tp + fp) if tp + fp else 1.0
        recall = tp / (tp + fn) if tp + fn else 1.0

        oversized = int(full["oversized_source_count"])
        selected = int(bounded["selected_count"])
        candidate_reduction = 1.0 - (selected / oversized) if oversized else 0.0

        python_files = sorted(root.rglob("*.py"))
        python_bytes = sum(path.stat().st_size for path in python_files)
        files_at_least_once = int(full["source_files_scanned"]) + int(
            full["test_python_files_scanned"]
        )

        bounded_rows = bounded["rows"]
        assert isinstance(bounded_rows, list)
        evidence_paths = {
            str(row["source_path"])
            for row in bounded_rows
            if isinstance(row, dict)
        }
        for row in bounded_rows:
            if not isinstance(row, dict):
                continue
            for match in row.get("matches", []):
                if isinstance(match, dict) and isinstance(match.get("test_path"), str):
                    evidence_paths.add(match["test_path"])
        evidence_reduction = (
            1.0 - (len(evidence_paths) / len(python_files)) if python_files else 0.0
        )

        result: dict[str, object] = {
            "probe": "refactor-focus",
            "qualification_phase": 1,
            "passed": not failures,
            "authority_counts": counts,
            "precision": precision,
            "recall": recall,
            "economics": {
                "oversized_source_candidates": oversized,
                "bounded_selected": selected,
                "candidate_reduction": candidate_reduction,
                "bounded_evidence_files": len(evidence_paths),
                "corpus_python_files": len(python_files),
                "evidence_reduction": evidence_reduction,
                "full_probe_runtime_ms": round(elapsed * 1000, 3),
                "bounded_probe_runtime_ms": round(bounded_elapsed * 1000, 3),
                "python_files_parsed_at_least_once": files_at_least_once,
                "bytes_read_lower_bound": python_bytes,
                "accounting_note": (
                    "P1 records a lower bound. Exact read/AST-parse invocation accounting "
                    "is Phase 2 parse-once work."
                ),
            },
            "cases": case_results,
            "failures": failures,
        }

        if artifact_path is not None:
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(
                json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the stdlib-only P1 qualification corpus for refactor-focus.",
    )
    parser.add_argument(
        "--artifact-path",
        type=Path,
        default=Path(".agent-artifacts/refactor-focus-qualification.json"),
        help="Qualification JSON destination.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    result = qualify(args.artifact_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
