---
name: codebase-finding-derivation
description: Derives defensible findings from real code paths, violated expectations, evidence, and production consequences.
license: MIT
---

# Codebase Finding Derivation

Standalone, read-only evidence-derivation skill for turning inspected codebase behavior into defensible findings.

## INVARIANT

> **A codebase observation becomes a finding only when inspected evidence proves a real path, a violated expectation, and a material consequence; absence of findings is claimable only inside a completed inspected scope.**

## HUNT

Start from real repository behavior, not smells. Hunt for:
- production or test paths where ownership, state, effects, validation, retries, cleanup, or failure behavior diverge from the apparent contract;
- contradictions between declared invariants and reachable implementation behavior;
- branches, fallbacks, recovery paths, or alternate entry points that change semantics materially;
- repeated decisions, representations, observations, or effects only when they operate on the same logical fact or operation;
- tests that expose hidden production complexity, missing completion contracts, or unrealistic boundaries;
- comments, docs, names, or types that claim one behavior while reachable code implements another;
- obsolete or duplicate paths only when current callers can still reach them.

For each candidate, follow the path far enough to answer:

```text
ENTRY / TRIGGER
-> relevant calls, state, or data flow
-> decision / effect / transition
-> externally meaningful result
```

## PROVE

### Five quick QA questions for low-reasoning reviewers

Answer these in order from the inspected source; write `unknown` rather than filling
a gap from pattern recognition. These are a short route through the proof below,
not another skill, score, or approval gate.

1. **What is actually implemented?** Name the inspected revision, exact symbol,
   caller, and relevant existing tests. A grep hit, old review, or familiar API
   name does not establish behavior.
2. **What fact and owner are involved?** State the fact, scope, and generation.
   Distinguish repository declarations/relationships from effective native-tool
   configuration, Git/process execution witnesses, and independent custody
   identities. Similar names or SHA-256 algorithms do not prove one authority.
3. **Where is the accepted violation?** Trace entry -> producer -> consumer
   decision -> observable consequence. Quote the contract that fails; a preferred
   design, manual parser, or repeated helper is not a failure by itself.
4. **What could disprove the claim?** Inspect the closest safe case and
   existing tests. Check protocol guarantees, parsing edge cases, the moment
   filesystem traversal prunes directories, and any deliberate trust boundary.
   Try to show a violation/control pair rather than assert fragility or cost.
5. **Which bounded verdict and next action follow?** Report `FINDING` only
   with a real path, violation, and consequence; `LEAVE ALONE` for a justified
   safe case; `INSUFFICIENT EVIDENCE` when decisive inputs are missing; and a
   scoped `CLEAN` only after its scope is complete. Prefer one focused proof
   and the smallest correction over a new service, abstraction, or gate.

Concrete safe controls: a native Git command owner may both execute and observe
Git without being a second repository-intelligence authority; file digests for
different custody facts are not duplicate identities; parsing a documented
machine-readable Git status format is not inherently brittle; and removing
names from top-down `os.walk`'s mutable `directories` list prevents descent.
Verify each control in the actual target code before applying it.

A finding needs all of these:

1. **Observation** — what the code appears to do.
2. **Reachable path** — how real production or test behavior reaches it.
3. **Expectation** — the contract, invariant, ownership rule, or behavior it should satisfy.
4. **Violation** — the exact point where actual behavior diverges.
5. **Consequence** — correctness, reliability, performance, testability, operability, or maintenance impact that can actually occur.
6. **Evidence** — concrete files, symbols, callers, state transitions, tests, or runtime behavior supporting the claim.
7. **Disconfirmation check** — guards, callers, ownership rules, or constraints inspected that might make the candidate safe.

If one of those is missing, downgrade the candidate to `INSUFFICIENT EVIDENCE` instead of inventing certainty.

Also record the **inspection boundary** used for the derivation pass and any material paths, callers, evidence sources, or repository areas that were skipped, unavailable, or truncated.

## DO NOT REPORT

Do not turn these into findings by themselves:
- large files or long functions;
- TODOs, naming, formatting, or stylistic preferences;
- grep similarity or duplicated syntax without shared semantics;
- theoretical races or failures with no reachable ordering/path;
- unused-looking code without caller or reachability evidence;
- many dependencies when they form one coherent domain aggregate;
- tests that are complex because the public scenario is genuinely complex;
- alternative designs that are merely different rather than demonstrably better.

Do not recommend a new manager, coordinator, registry, facade, generic repository, wrapper, cache, or framework just to give the finding a solution.

## PREFER

Prefer the smallest defensible statement the evidence supports.

When the finding clearly belongs to a narrower specialist skill, name that skill instead of solving the whole problem here. Examples:
- stale older work -> `stale-work-race-review`;
- repeated semantic decision -> `semantic-redecision-review`;
- duplicate durable commit authority -> `durable-commit-path-review`;
- partial externally visible operation -> `atomic-operation-review`;
- retry repeats a one-shot effect -> `retry-idempotency-review`;
- repeated observation -> `single-observation-review`;
- invalid state representation -> `invalid-state-model-review`;
- test timing based on scheduler luck -> `deterministic-causality-test-review`.

Prefer deletion, consolidation, clearer ownership, or a shorter authoritative path when the evidence supports a correction direction.

## OUTPUT

Return `# Codebase Finding Derivation` and state the actual inspection boundary plus whether the requested derivation scope was complete.

For each defensible finding include:

```text
## <finding title>

Observation:
Reachable path:
Violated expectation:
Material consequence:
Evidence:
Disconfirmation checked:
Confidence: HIGH | MEDIUM | LOW
Best specialist: <skill name | None>
What should disappear or become authoritative:
```

Then include:

```text
## Insufficient Evidence
<candidates that looked suspicious but could not be proved, or None>
```

If no defensible finding exists after the declared inspection boundary is complete, say `No defensible findings in inspected scope.` Do not manufacture findings to fill the report. If the requested derivation scope could not be completed, return `INSUFFICIENT EVIDENCE` instead of a no-finding claim.
