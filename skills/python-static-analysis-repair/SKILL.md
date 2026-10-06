---
name: python-static-analysis-repair
description: Makes Ruff, Pyright, and ty clean while protecting behavior with focused tests before semantic repairs.
license: MIT
---

# Python Static Analysis Repair

Standalone repair discipline for Python repositories that use Ruff, Pyright, and ty.

This skill is for implementation work, not merely reporting static-analysis findings. The goal is a clean analyzer state without silently changing runtime behavior to satisfy the tools.

## INVARIANT

> **Static-analysis cleanliness must not be bought by an unproved runtime behavior change. Mechanical fixes may proceed directly; any semantic or uncertain fix must protect the relevant behavior with a focused test before production code changes.**

A green analyzer is evidence about the static model, not authority to redefine product behavior.

## ESTABLISH THE BASELINE

Before editing production code:

- identify the repository-owned test command and the repository-native invocations for Ruff, Pyright, and ty;
- run the smallest existing tests relevant to the failing files or symbols when practical;
- run all three analyzers and record the exact findings before repair;
- preserve repository configuration, analyzer scope, strictness, excludes, and target versions unless the task explicitly asks to change policy;
- treat an unavailable, skipped, crashed, or unconfigured analyzer as incomplete work, not clean.

Prefer the repository's existing entrypoints. If the project uses a native environment owner such as uv, invoke project-local tools through that owner rather than resolving or installing parallel global executables.

## CLASSIFY BEFORE FIXING

Classify each finding before editing.

### Mechanical

A change is mechanical only when there is no plausible effect on:

- control flow;
- returned values or raised exceptions;
- mutation or external effects;
- import-time behavior;
- defaults or data shape;
- lifecycle, concurrency, or ordering;
- public or persisted contracts.

Examples can include pure formatting or annotation-only changes that do not affect runtime evaluation in the supported Python versions.

A tool calling an autofix "safe" is useful evidence, but it does not override repository-specific runtime semantics.

### Semantic

Treat a change as semantic when it can alter executable behavior, including changes to:

- conditionals, branches, guards, assertions, or exception handling;
- Optional/None handling or fallback values;
- return values, defaults, coercion, parsing, or serialization;
- imports that may have runtime side effects;
- async ordering, resource lifetime, retries, state mutation, or persistence;
- callable signatures or protocol behavior observed by real callers;
- data-model shape or accepted/rejected inputs.

### Uncertain

If you cannot prove the change is mechanical, classify it as semantic.

Do not use uncertainty as permission to edit first and test later.

## PROTECT BEHAVIOR FIRST

For every semantic or uncertain repair:

1. Trace at least one real caller or execution path to the affected code.
2. State the observable behavior that must remain stable.
3. Add the smallest focused test that proves that behavior through the most stable boundary available.
4. Run that test **before** changing production code.
5. Require the pre-change test to pass when the task is behavior-preserving.
6. Make the production change.
7. Run the same test again and require it to keep passing.

Prefer outcome assertions over private call-order or helper-choreography assertions.

If static analysis exposes a real runtime defect and the intended task now requires behavior to change, do not disguise that as a behavior-preserving cleanup. Add a focused **failing regression** for the intended behavior first, make the repair, and explicitly report the intentional behavior change.

## REPAIR

Fix the type or lint truth at its real boundary.

Prefer:

- narrowing values where runtime evidence already guarantees a narrower type;
- making Optional/union branches explicit instead of assuming away None;
- returning the type the callable actually promises;
- making protocol, TypedDict, dataclass, model, or callable signatures match real supported behavior;
- converting external/untyped data once at an owned boundary;
- removing genuinely unreachable or dead code only when behavior evidence supports that conclusion;
- correcting imports, names, scopes, and annotations at the source of the mismatch;
- one representation that both Pyright and ty can understand when they expose the same underlying type fact.

Do not "fix" analyzer output by:

- adding new broad `# type: ignore`, `# pyright: ignore`, `# noqa`, file-wide disables, or configuration exclusions;
- weakening strictness or shrinking checked paths;
- replacing useful types with `Any`, `object`, or broad unions solely to silence errors;
- adding casts or assertions that claim facts not established by runtime structure or validation;
- deleting tests because they expose the behavior that makes a type fix difficult;
- changing runtime semantics merely because one analyzer prefers a different shape;
- installing or selecting a second toolchain when the repository already owns how these tools run.

A narrow cast or suppression can remain only when it represents a real, externally imposed type-system limitation and the repository already accepts that policy. It must not be the default repair strategy, and it must be called out in the result.

## ITERATE

Work in small slices:

1. choose one coherent finding cluster;
2. classify it;
3. add behavior protection first when required;
4. repair the root cause;
5. run the focused test;
6. rerun the analyzer or analyzers that exposed the cluster;
7. continue only after that slice is understood.

When Pyright and ty disagree, inspect the real runtime contract instead of coding to whichever diagnostic is easier to silence.

Ruff findings that require executable code changes follow the same semantic-fix rule as type findings.

## FINAL GATE

Do not declare success until:

- focused behavior-preservation/regression tests pass;
- the repository's relevant broader tests pass;
- Ruff passes clean for the repository-owned scope;
- Pyright passes clean for the repository-owned scope;
- ty passes clean for the repository-owned scope;
- no analyzer was skipped or hidden by a newly weakened configuration;
- no new suppression, broad `Any`, or unproved cast was introduced merely to obtain green output.

If repository policy includes `ruff format --check` in addition to `ruff check`, both must pass.

## DO NOT EXPAND THE TASK

Do not turn analyzer cleanup into unrelated architecture redesign.

Do not add broad tests for already mechanical edits. The test-first requirement exists where the code change can affect behavior.

Do not use this skill to decide whether Ruff, Pyright, or ty are the correct repository tools. Use the repository's declared tool authority. `native-tool-authority-review` owns duplicated or shadow executable/tool authority.

Do not use this skill as a general coverage audit. `coverage-design-review` owns whether the repository is missing important behavioral coverage beyond what is needed to protect this repair.

Do not treat analyzer diagnostics as proof of a runtime defect. `static-evidence-overclaim-review` owns analyzers or downstream consumers that claim stronger semantic certainty than their proof model supports.

## OUTPUT

Return `# Python Static Analysis Repair` with:

- baseline test and analyzer commands/results;
- finding clusters and their mechanical/semantic classification;
- focused behavior tests added before semantic changes;
- production repairs made;
- any intentional behavior change and its failing regression;
- final Ruff, Pyright, ty, and test receipts;
- any remaining blocker or analyzer that could not be run.

End with exactly one:

- `CLEAN` — relevant tests pass and Ruff, Pyright, and ty all pass for the unchanged repository-owned analysis scope;
- `INCOMPLETE` — a required analyzer/test could not be run or remaining findings still exist;
- `BLOCKED` — the requested clean state requires an unresolved behavior/product decision rather than a safe static-analysis repair.
