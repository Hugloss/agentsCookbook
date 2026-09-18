from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

from .bounded_process import ProcessLimits, run_bounded
from .capabilities import capabilities
from .command_manifest import CommandManifestError, load_command_manifest
from .command_runner import run_named_command
from .loop_state import LoopBudget, LoopSession
from .repair_packet import build_repair_packet


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        manifest = root / "agent-economics.toml"
        py = sys.executable.replace("\\", "\\\\")
        _write(manifest, f'''version = 1
[commands.pass]
argv = ["{py}", "-c", "print('ok')"]
stage = "focused"

[commands.fail]
argv = ["{py}", "-c", "raise AssertionError('boom')"]
stage = "affected"

[commands.literal]
argv = ["{py}", "-c", "import sys; print(sys.argv[1])"]
append_selected_tests = true
stage = "component"

[commands.flood]
argv = ["{py}", "-c", "print('x'*10000)"]
stage = "repository"

[commands.missing]
argv = ["definitely-not-an-agent-economics-executable"]
stage = "repository"
''')
        loaded = load_command_manifest(manifest)
        assert loaded.version == 1 and len(loaded.commands) == 5
        try:
            _write(root / "bad.toml", 'version=1\n[commands.x]\nargv=["x"]\ncwd="../escape"\n')
            load_command_manifest(root / "bad.toml")
        except CommandManifestError:
            pass
        else:
            raise AssertionError("cwd escape must fail closed")

        passed = run_named_command(repository_root=root, manifest_path=manifest, name="pass")
        assert passed["classification"] == "pass"
        failed = run_named_command(repository_root=root, manifest_path=manifest, name="fail")
        assert failed["classification"] == "assertion_test_failure"
        missing = run_named_command(repository_root=root, manifest_path=manifest, name="missing")
        assert missing["classification"] == "executable_missing"
        literal = run_named_command(
            repository_root=root, manifest_path=manifest, name="literal",
            selected_paths=["semi;colon.py"],
        )
        assert "semi;colon.py" in literal["stdout"]

        flood = run_bounded(
            repository_root=root,
            argv=(sys.executable, "-c", "print('x'*10000)"),
            limits=ProcessLimits(timeout_seconds=5, max_stdout_bytes=32, max_stderr_bytes=32),
        )
        assert flood.stdout_truncated
        timeout = run_bounded(
            repository_root=root,
            argv=(sys.executable, "-c", "import time; time.sleep(10)"),
            limits=ProcessLimits(timeout_seconds=0.05, max_stdout_bytes=32, max_stderr_bytes=32),
        )
        assert timeout.timed_out
        packet = build_repair_packet(repository_root=root, command_result=failed)
        assert packet["authority"]["repair_performed"] is False

        state_path = root / ".agent-artifacts/state.json"
        with LoopSession(state_path, budget=LoopBudget(max_iterations=5)) as session:
            first = session.record(
                source_identity="s", command_identity="c", failure_identity="f",
                evidence_identity="e", stdout_bytes=1, stderr_bytes=1,
            )
            second = session.record(
                source_identity="s", command_identity="c", failure_identity="f",
                evidence_identity="e", stdout_bytes=1, stderr_bytes=1,
            )
            assert first["stop_reason"] is None
            assert second["stop_reason"] == "NO_PROGRESS"
        lock = state_path.with_suffix(state_path.suffix + ".lock")
        lock.write_text("owned")
        try:
            with LoopSession(state_path):
                raise AssertionError("lock conflict admitted")
        except ValueError:
            pass
        lock.unlink()

        caps = capabilities(repository_root=root, manifest_path=manifest)
        assert caps["repository"]["workspace_available"] is True
        assert caps["capabilities"]["network_isolation"]["available"] is False

        print(json.dumps({
            "status": "PASS",
            "cases": [
                "versioned-manifest", "cwd-containment", "argv-literal",
                "pass-classification", "assertion-classification", "missing-executable",
                "stdout-hard-bound", "timeout", "repair-packet-no-edit-authority",
                "no-progress", "state-lock", "capability-honesty",
            ],
        }, sort_keys=True))


if __name__ == "__main__":
    main()
