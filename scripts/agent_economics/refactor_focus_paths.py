import os
import re
from datetime import datetime, timezone
from pathlib import Path

from .refactor_focus_models import DEFAULT_EXCLUDE_DIRS


def collect_python_files(root: Path) -> list[Path]:
    files: list[Path] = []
    if not root.exists():
        return files
    for path in root.rglob("*.py"):
        if not path.is_file():
            continue
        if any(part in DEFAULT_EXCLUDE_DIRS for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def collect_test_files(tests_root: Path) -> list[Path]:
    return [
        path
        for path in collect_python_files(tests_root)
        if path.name.startswith("test_") or path.name.endswith("_test.py")
    ]


def count_lines(path: Path) -> int:
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


def report_path(*, path: Path, anchor: Path) -> str:
    try:
        return path.resolve().relative_to(anchor.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def common_path_anchor(paths: list[Path]) -> Path:
    if not paths:
        return Path.cwd().resolve()
    resolved = [str(path.resolve()) for path in paths]
    return Path(os.path.commonpath(resolved))


def normalize_token(token: str) -> str:
    if token.endswith("ing") and len(token) > 5:
        token = token[:-3]
    if token.endswith("ies") and len(token) > 5:
        token = f"{token[:-3]}y"
    elif token.endswith("s") and len(token) > 4:
        token = token[:-1]
    return token


def tokenize(text: str) -> set[str]:
    tokens = {token for token in re.split(r"[^a-z0-9]+", text.lower()) if token}
    return {normalize_token(token) for token in tokens if normalize_token(token)}


def path_feature_tokens(path: Path) -> set[str]:
    tokens: set[str] = set()
    parts = list(path.parts)
    for index, part in enumerate(parts):
        feature_part = part
        if index == len(parts) - 1:
            suffix = Path(part).suffix
            if suffix:
                feature_part = part[: -len(suffix)]
        tokens.update(tokenize(feature_part))
    return tokens


def iso_utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace(
            "+00:00",
            "Z",
        )
    )


def module_path_for_file(
    *,
    path: Path,
    root: Path,
    package_name: str,
) -> str:
    relative = path.relative_to(root).with_suffix("")
    parts = list(relative.parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join((package_name, *parts))


def source_module_path(
    *,
    source_path: Path,
    source_root: Path,
    package_name: str,
) -> str:
    return module_path_for_file(
        path=source_path,
        root=source_root,
        package_name=package_name,
    )
