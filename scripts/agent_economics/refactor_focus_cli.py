import argparse
import json
import sys
from pathlib import Path

from .refactor_focus_workflow import refactor_focus_audit


def emit(level: str, event: str, **payload: object) -> None:
    print(
        json.dumps(
            {
                "level": level,
                "event": event,
                **payload,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        file=sys.stderr,
    )


def exit_code(code: int) -> None:
    raise SystemExit(code)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Find bounded Python refactoring candidates and the evidence an agent "
            "should inspect before editing."
        ),
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        required=True,
        help="Python package source root, for example src/my_package.",
    )
    parser.add_argument(
        "--tests-root",
        type=Path,
        default=Path("tests"),
        help="Test tree root. Default: tests.",
    )
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=None,
        help=(
            "Repository/reporting root. If omitted, the common ancestor of "
            "source-root and tests-root is used."
        ),
    )
    parser.add_argument(
        "--package-name",
        default=None,
        help="Import package name. If omitted, source-root basename is used.",
    )
    parser.add_argument(
        "--tests-package-name",
        default=None,
        help="Tests import package name. If omitted, tests-root basename is used.",
    )
    parser.add_argument(
        "--artifact-path",
        type=Path,
        default=Path(".agent-artifacts/refactor-focus.json"),
        help="JSON report destination.",
    )
    parser.add_argument("--file-line-threshold", type=int, default=800)
    parser.add_argument("--function-line-threshold", type=int, default=80)
    parser.add_argument("--top-n", type=int, default=3)
    parser.add_argument("--transitive-max-depth", type=int, default=2)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    refactor_focus_audit(
        emit=emit,
        exit_code=exit_code,
        source_root=args.source_root,
        tests_root=args.tests_root,
        repository_root=args.repository_root,
        artifact_path=args.artifact_path,
        package_name=args.package_name,
        tests_package_name=args.tests_package_name,
        file_line_threshold=args.file_line_threshold,
        function_line_threshold=args.function_line_threshold,
        top_n=args.top_n,
        transitive_max_depth=args.transitive_max_depth,
    )


if __name__ == "__main__":
    main()
