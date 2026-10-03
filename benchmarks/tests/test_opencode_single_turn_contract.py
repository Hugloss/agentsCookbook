from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "scripts/opencode-runtime.js"
AGENT = (
    ROOT
    / "benchmarks/suites/repository-intelligence/heldout-v1/agents/opencode-native.json"
)


class OpenCodeSingleTurnContractTests(unittest.TestCase):
    def test_benchmark_overlay_disables_and_verifies_auto_compaction(self) -> None:
        source = RUNTIME.read_text(encoding="utf-8")

        self.assertIn("compaction: { auto: false }", source)
        self.assertIn("effective.compaction.auto !== false", source)
        self.assertIn(
            "benchmark OpenCode auto-compaction must be disabled for single-turn trials",
            source,
        )
        self.assertIn("compaction_auto: false", source)

    def test_opencode_agent_identity_versions_execution_runtime(self) -> None:
        agent = json.loads(AGENT.read_text(encoding="utf-8"))
        self.assertEqual(agent["identity"]["version"], "native-config-v3")


if __name__ == "__main__":
    unittest.main()
