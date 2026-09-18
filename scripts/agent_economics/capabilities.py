from __future__ import annotations

import json
import platform
import shutil
from pathlib import Path

from .command_manifest import CommandManifestError, load_command_manifest

PROBES = (
    "refactor-focus", "context-focus", "test-focus", "change-impact",
    "coupling-focus", "hotspot-focus",
)


def capabilities(*, repository_root: Path, manifest_path: Path | None = None) -> dict[str, object]:
    root = repository_root.resolve()
    workspace = root.is_dir()
    git = shutil.which("git")
    result: dict[str, object] = {
        "schema": {"name": "agent-economics-capabilities", "version": 1},
        "repository": {"workspace_available": workspace, "root": "." if workspace else None},
        "platform": {"system": platform.system(), "python": platform.python_version()},
        "capabilities": {
            "git": {"available": git is not None},
            "process_tree_termination": {"available": True, "mechanism": "process-group" if platform.system() != "Windows" else "process-handle"},
            "network_isolation": {"available": False, "reason": "not enforced by AgentCookbook"},
            "sandbox_isolation": {"available": False, "reason": "not enforced by AgentCookbook"},
            "probes": {"available": list(PROBES)},
        },
        "commands": {},
        "warnings": [],
    }
    if not workspace:
        result["warnings"].append({"code": "repository_bytes_unavailable"})
        return result
    if manifest_path is not None:
        target = manifest_path if manifest_path.is_absolute() else root / manifest_path
        try:
            manifest = load_command_manifest(target)
        except (OSError, CommandManifestError) as exc:
            result["warnings"].append({"code": "command_manifest_unavailable", "detail": type(exc).__name__})
        else:
            result["command_manifest_identity"] = manifest.identity
            result["commands"] = {
                name: {
                    "configured": True,
                    "available": shutil.which(spec.argv[0]) is not None,
                    "stage": spec.stage,
                }
                for name, spec in manifest.commands.items()
            }
    return result


def main(argv: list[str] | None = None) -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Report portable AgentCookbook environment capabilities.")
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    payload = capabilities(repository_root=args.repository_root, manifest_path=args.manifest)
    print(json.dumps(payload, indent=2, sort_keys=True) if args.json else json.dumps(payload, sort_keys=True))
