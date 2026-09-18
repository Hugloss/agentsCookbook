from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path


class CommandManifestError(ValueError):
    pass


@dataclass(frozen=True)
class CommandSpec:
    name: str
    argv: tuple[str, ...]
    cwd: str
    stage: str
    append_selected_tests: bool
    must_not_modify_tracked_files: bool
    allowed_mutation_paths: tuple[str, ...]


@dataclass(frozen=True)
class CommandManifest:
    version: int
    commands: dict[str, CommandSpec]
    identity: str


def _safe_relative(value: str) -> str:
    candidate = Path(value.replace("\\", "/"))
    if candidate.is_absolute() or any(part in {"", ".."} for part in candidate.parts):
        raise CommandManifestError(f"path must be repository-relative: {value!r}")
    return candidate.as_posix() if candidate != Path(".") else "."


def load_command_manifest(path: Path) -> CommandManifest:
    raw = path.read_bytes()
    if len(raw) > 1_000_000:
        raise CommandManifestError("command manifest exceeds 1,000,000 byte bound")
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise CommandManifestError("invalid UTF-8 TOML command manifest") from exc
    if data.get("version") != 1:
        raise CommandManifestError("command manifest version must be 1")
    raw_commands = data.get("commands")
    if not isinstance(raw_commands, dict) or not raw_commands:
        raise CommandManifestError("command manifest requires [commands.*] entries")
    commands: dict[str, CommandSpec] = {}
    for name, value in sorted(raw_commands.items()):
        if not isinstance(name, str) or not name or not isinstance(value, dict):
            raise CommandManifestError("invalid command entry")
        argv = value.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
            raise CommandManifestError(f"command {name!r} requires non-empty argv string array")
        cwd = _safe_relative(str(value.get("cwd", ".")))
        stage = str(value.get("stage", "component"))
        if stage not in {"focused", "affected", "component", "repository"}:
            raise CommandManifestError(f"command {name!r} has invalid stage")
        allowed = value.get("allowed_mutation_paths", [])
        if not isinstance(allowed, list) or not all(isinstance(x, str) for x in allowed):
            raise CommandManifestError(f"command {name!r} allowed_mutation_paths must be strings")
        commands[name] = CommandSpec(
            name=name,
            argv=tuple(argv),
            cwd=cwd,
            stage=stage,
            append_selected_tests=bool(value.get("append_selected_tests", False)),
            must_not_modify_tracked_files=bool(value.get("must_not_modify_tracked_files", True)),
            allowed_mutation_paths=tuple(_safe_relative(x) for x in allowed),
        )
    identity = "sha256:" + hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return CommandManifest(version=1, commands=commands, identity=identity)
