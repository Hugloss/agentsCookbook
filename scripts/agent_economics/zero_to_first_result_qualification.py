from __future__ import annotations

import contextlib
import io
import tempfile
from pathlib import Path

from .__main__ import main as package_main
from .capabilities import capabilities
from .command_catalog import COMMANDS, PROBE_COMMANDS
from .doctor import doctor


def qualify() -> None:
    with tempfile.TemporaryDirectory(prefix="agent-economics-doctor-") as raw:
        root = Path(raw)
        (root / "src/acme").mkdir(parents=True)
        (root / "src/acme/__init__.py").write_text("", encoding="utf-8")
        (root / "tests").mkdir()
        (root / "pyproject.toml").write_text("[project]\nname='acme'\nversion='0'\n", encoding="utf-8")
        before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
        payload = doctor(root)
        after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
        assert before == after
        assert payload["suggestions"]["source_roots"] == ["src/acme"]
        assert payload["suggestions"]["tests_roots"] == ["tests"]
        assert payload["suggestions"]["package_names"] == ["acme"]
        assert payload["interpretation"]["suggestions_are_not_repository_authority"] is True
        assert payload["readiness"]["test_focus"] == "READY"

        capability = capabilities(repository_root=root)
        assert capability["capabilities"]["probes"]["available"] == list(PROBE_COMMANDS)
        assert "quality-debt" in PROBE_COMMANDS

    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        package_main(["--help"])
    help_text = output.getvalue()
    for command in COMMANDS:
        assert command.name in help_text
    assert "Start in an unfamiliar repository" in help_text

    print('{"cases":4,"status":"PASS","tool":"zero-to-first-result"}')


if __name__ == "__main__":
    qualify()
