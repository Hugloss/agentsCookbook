---
name: codebase-finding-derivation
description: Derives defensible findings from real code paths, violated expectations, evidence, and production consequences.
license: MIT
---

# Codebase Finding Derivation

Standalone, read-only evidence-derivation skill for turning inspected codebase behavior into defensible findings.

## INVARIANT

> **A codebase observation becomes a finding only when inspected evidence proves a reachable behavior or governed boundary, a violated expectation, and a material consequence; absence of findings is claimable only inside a completed inspected scope.**

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

### Five questions for evidence calibration

Use these prompts where they resolve the review's uncertainty. They summarize
the proof below without prescribing a fixed order, another report template, or
an approval gate. Keep unavailable evidence `unknown`.

1. **What is actually implemented?** Identify the inspected source and revision,
   relevant callers or governed boundary, and existing tests. Distinguish source
   evidence from an executed test result; a grep hit or stale review is a lead.
2. **What fact and owner are involved?** State the fact and scope; include
   generation or freshness when it affects meaning. Separate declarations from
   effective native-tool behavior and execution/custody facts. Similar names,
   formats or hashing algorithms do not establish competing authority.
3. **Which contract fails in accepted use?** Trace input -> producer -> consumer
   decision -> consequence. A split-authority finding requires two independent
   accepted authorities for the same fact, scope and generation; unsupported
   reconstruction, weakened qualifications or lost typed meaning can violate
   other contracts without a second producer. For structural contracts, identify
   the governed boundary rather than inventing a runtime trace. A witnessed
   violation can suffice; absence or clean claims need the complete defined scope.
   Cite the applicable requirement and supporting evidence; a preferred design
   or parser's presence is not a defect.
4. **What could disprove the claim?** Inspect relevant guards, protocol guarantees
   and the nearest safe case. Reuse existing tests or source evidence where
   decisive; a new test pair is not a prerequisite to every finding. Separate
   source-proved repeated work from measured cost or speedup claims, which need
   suitable observations.
5. **Which bounded verdict and repair follow?** Use `FINDING` for a proved
   violation and consequence, `LEAVE ALONE` for a justified safe case, and
   `INSUFFICIENT EVIDENCE` for unresolved claims. `CLEAN` requires complete
   inspection of its declared scope. A proved finding survives unrelated
   unresolved scope. Name the responsible owner or coordinated owners; an
   upstream capability may need repair before a consumer can migrate.

Concrete safe controls: a native Git command owner may both execute and observe
Git without being a second repository-intelligence authority; file digests for
different custody facts are not duplicate identities; parsing a documented
machine-readable Git status format is not inherently brittle; and removing
names from top-down `os.walk`'s mutable `directories` list prevents descent.
Verify each control in the actual target code before applying it.

Check qualified meaning as well as value equality: accepting boolean `true` as
integer `1` can violate a typed packet contract even when host-language equality
equates them. A pure packet-consistency check also does not establish sender
authenticity or current source freshness; those need their own admitted evidence.

A finding needs all of these:

1. **Observation** — what the code appears to do.
2. **Reachable path or governed boundary** — how production or test behavior reaches it, or the exact scope of an explicit structural/absence contract.
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
Reachable path / governed boundary:
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
