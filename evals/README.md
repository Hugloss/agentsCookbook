# Evaluations

Evaluation ownership is repository-level, not OpenCode-directory-level.

The fixed flow benchmark set lives in `scripts/run-opencode-benchmarks.js`. It covers full Ping-Pong planning and one-reviewer routing behavior, records sessions, validates runtime call structure, and checks final-answer contracts.

The sharp specialist benchmark is runtime-neutral:

- `evals/sharp-skill-cases.json` is the canonical positive/control/confusion corpus;
- `scripts/run-skill-benchmarks.js` validates and executes that corpus on OpenCode or Pi;
- `evals/sharp-skill-discrimination.md` documents the behavioral contract;
- `evals/fixtures/` contains bounded repository-backed cases where nearby failure classes must be distinguished from one another.

Loading a skill proves availability, not discrimination quality. A sharp skill is useful only when it finds its own defect and rejects safe or neighboring cases.

When adding evaluations:

- test standalone invocation separately from full-flow composition;
- include routing false positives/negatives for short descriptions;
- give every specialist at least one positive and one control case;
- add confusion cases where two skill families can plausibly inspect the same code;
- require evidence and reject cross-skill drift, not just plausible-sounding prose;
- test 98k context-pressure behavior with bounded evidence packets;
- execute the same behavioral corpus on OpenCode and Pi instead of maintaining two copies;
- distinguish install/discovery proof from model-backed behavioral proof;
- distinguish 12 installable agents from the exact eight mandatory flow reviewers;
- verify failed/skipped reviewer calls cannot be reported as successes.

Structural corpus validation is safe for CI:

```bash
node scripts/run-skill-benchmarks.js --validate-corpus
```

Model-backed runs belong in local runtime qualification because GitHub CI does not own the local endpoints or model profile.

Do not put canonical agent or skill sources under an evaluation or runtime-specific directory.
