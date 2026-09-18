from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .agent_outcome_benchmark import BenchmarkError, Outcome, compare, load_outcomes


def main() -> None:
    outcomes = [
        Outcome(task_id="localized-python", mode="baseline", correct=True, ci_activations=3, files_opened=12, evidence_bytes=20000, context_tokens_estimate=9000, tool_calls=20, repair_iterations=3),
        Outcome(task_id="localized-python", mode="bridge", correct=True, ci_activations=1, files_opened=5, evidence_bytes=8000, context_tokens_estimate=3500, tool_calls=9, local_commands=4, repair_iterations=1, local_ci_agree=True),
        Outcome(task_id="broad-after-focused", mode="baseline", correct=True, ci_activations=2, files_opened=10, evidence_bytes=15000, context_tokens_estimate=7000, tool_calls=16, repair_iterations=2),
        Outcome(task_id="broad-after-focused", mode="bridge", correct=True, ci_activations=1, files_opened=6, evidence_bytes=9000, context_tokens_estimate=4000, tool_calls=10, local_commands=5, repair_iterations=2, local_ci_agree=True),
    ]
    result = compare(outcomes)
    assert result["correctness"]["paired_tasks"] == 2
    assert result["metrics"]["ci_activations"]["delta"] == -3.0
    assert result["promotion_evidence"]["correctness_not_reduced"] is True
    assert result["authority"]["automatic_promotion"] is False
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "outcomes.jsonl"
        path.write_text("\n".join(json.dumps(o.__dict__) for o in outcomes) + "\n", encoding="utf-8")
        loaded = load_outcomes(path)
        assert len(loaded) == 4
        try:
            compare([outcomes[0]])
        except BenchmarkError:
            pass
        else:
            raise AssertionError("unpaired benchmark must fail closed")
    print(json.dumps({"status": "PASS", "paired_tasks": 2, "automatic_promotion": False}, sort_keys=True))


if __name__ == "__main__":
    main()
