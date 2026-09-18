from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _git_worktree(root: Path) -> bool:
    if shutil.which("git") is None:
        return False
    result = subprocess.run(
        ("git", "-C", str(root), "rev-parse", "--is-inside-work-tree"),
        capture_output=True, text=True, timeout=3, check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def _pyproject(root: Path) -> dict[str, object]:
    path = root / "pyproject.toml"
    if not path.is_file():
        return {}
    try:
        value = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _source_candidates(root: Path) -> list[str]:
    candidates: list[Path] = []
    src = root / "src"
    if src.is_dir():
        for child in sorted(src.iterdir()):
            if child.is_dir() and (child / "__init__.py").is_file():
                candidates.append(child)
    for child in sorted(root.iterdir()):
        if (
            child.is_dir()
            and child.name not in {"tests", "test", "scripts", "docs", "benchmarks"}
            and (child / "__init__.py").is_file()
        ):
            candidates.append(child)
    return [_relative(path, root) for path in candidates]


def doctor(repository_root: Path) -> dict[str, object]:
    root = repository_root.resolve()
    if not root.is_dir():
        raise ValueError(f"repository root does not exist: {root}")
    pyproject = _pyproject(root)
    sources = _source_candidates(root)
    tests = [name for name in ("tests", "test") if (root / name).is_dir()]
    ruff = shutil.which("ruff")
    ruff_version = None
    if ruff is not None:
        result = subprocess.run((ruff, "--version"), capture_output=True, text=True, timeout=3, check=False)
        if result.returncode == 0:
            ruff_version = result.stdout.strip()
    package_suggestions = [
        Path(item).name for item in sources if Path(item).name.isidentifier()
    ]
    ambiguity = []
    if len(sources) != 1:
        ambiguity.append("source_root")
    if len(tests) != 1:
        ambiguity.append("tests_root")
    return {
        "schema": {"name": "agent-economics-doctor", "version": 1},
        "repository": {
            "root": ".",
            "git_worktree": _git_worktree(root),
            "pyproject": bool(pyproject),
        },
        "environment": {
            "python": sys.version.split()[0],
            "ruff": {"available": ruff is not None, "resolved_executable": ruff, "version": ruff_version},
        },
        "suggestions": {
            "source_roots": sources,
            "tests_roots": tests,
            "package_names": package_suggestions,
        },
        "ambiguity": ambiguity,
        "readiness": {
            "context_focus": "READY",
            "hotspot_focus": "READY" if len(sources) == 1 else "NEEDS_SOURCE_ROOT",
            "test_focus": "READY" if len(sources) == 1 and len(tests) == 1 else "NEEDS_CONFIG",
            "quality_debt": "NEEDS_LIMITS" if ruff is not None else "NEEDS_RUFF",
        },
        "interpretation": {
            "suggestions_are_not_repository_authority": True,
            "doctor_modifies_repository": False,
        },
    }


def _human(payload: dict[str, object]) -> str:
    repo = payload["repository"]
    env = payload["environment"]
    suggestions = payload["suggestions"]
    readiness = payload["readiness"]
    assert isinstance(repo, dict) and isinstance(env, dict)
    assert isinstance(suggestions, dict) and isinstance(readiness, dict)
    ruff = env["ruff"]
    assert isinstance(ruff, dict)
    lines = [
        "AGENT ECONOMICS DOCTOR",
        f"Git worktree ............ {'YES' if repo['git_worktree'] else 'NO'}",
        f"pyproject.toml ........... {'FOUND' if repo['pyproject'] else 'NOT FOUND'}",
        f"Python ................... {env['python']}",
        f"Ruff ..................... {ruff['version'] or 'NOT AVAILABLE'}",
        f"Source suggestions ....... {', '.join(suggestions['source_roots']) or 'AMBIGUOUS / NOT FOUND'}",
        f"Test suggestions ......... {', '.join(suggestions['tests_roots']) or 'AMBIGUOUS / NOT FOUND'}",
        f"Package suggestions ...... {', '.join(suggestions['package_names']) or 'AMBIGUOUS / NOT FOUND'}",
        "",
        "READINESS",
    ]
    lines.extend(f"{name:25} {state}" for name, state in readiness.items())
    lines.extend(("", "Detected values are suggestions, not repository authority."))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Inspect Agent Economics readiness without modifying the repository.")
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        payload = doctor(args.repository_root)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise SystemExit(f"doctor: {exc}") from exc
    print(json.dumps(payload, indent=2, sort_keys=True) if args.json else _human(payload))


if __name__ == "__main__":
    main()
