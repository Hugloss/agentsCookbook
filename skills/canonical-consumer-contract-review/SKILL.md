---
name: canonical-consumer-contract-review
description: Finds consumers whose behavior breaks when a canonical semantic owner legitimately refines its result, because they depend on undocumented classifications, sentinels, or implementation details.
license: MIT
---

# Canonical Consumer Contract Review

Standalone, read-only review of **consumer compatibility across canonical-owner evolution**.

## INVARIANT

> **A consumer must depend on the declared meaning of one canonical owner's result, not on accidental result shapes, historical unknown/default classifications, private parsing behavior, or fallback conventions. A legitimate owner refinement must not silently erase an independent consumer obligation.**

This is not a demand that every output stay identical after an intentional semantic change. It is a demand that **every resulting behavior change is explained by the public contract**, and that obligations outside the changed meaning remain protected.

## HUNT

Start at a semantic owner and trace its real downstream consumers. Look for:
- a consumer recognizing a known import, symbol, capability, path, or identity only because the owner previously returned `unknown`, `None`, a generic status, or a fallback marker;
- consumers branching on one historical enum value, incidental ordering, raw string format, exception text, private field, implementation type, or absence of a newer result variant;
- a richer result added upstream while a downstream consumer silently discards, rejects, or treats it as negative;
- downstream special-case tables or duplicate parsers that reconstruct the owner's meaning instead of consuming its resolved identity;
- separate entrypoints, adapters, test paths, and projections interpreting the same result shape differently;
- tests that lock in accidental owner behavior, or owner-only tests that never verify downstream observations.

Example: a static filesystem consumer detects `pathlib` only while its import owner returns `unknown`. The owner later correctly returns `module(pathlib)`, and detection disappears. The failure is **consumer reliance on an undocumented historical classification**, not evidence that the more precise import result is wrong.

## PROVE

1. Name the **canonical owner**, the specific result and its declared meaning, and a reachable consumer. Establish the intended contract from code, tests, schemas, or documentation; do not invent it.
2. Trace the concrete result path into the consumer's branch, output, action, or observation. Identify the exact accidental assumption.
3. Construct a **paired counterfactual** for the *same relevant source fact*: the historical/less-precise owner result and an allowed more-precise/refined owner result. Hold the consumer's independent obligation constant. If the contract does not allow both forms, state that and investigate an explicit migration instead.
4. Show the actual or logically forced consumer behavior for both results, including a material loss, false conclusion, bypass, or inconsistent outcome that the declared contract does not justify.
5. Check `unknown`, unresolved, ambiguous, absent, and invalid cases separately. Never make a consumer "compatible" by pretending unsupported evidence is proven.
6. Identify the smallest correction that consumes the **canonical typed semantic result**, deletes redundant reconstruction if present, and keeps the relevant independent observation/behavior. Preserve genuine validation and trust-boundary checks.
7. Specify a focused **consumer-level regression** exercising both supported result forms, a genuinely unknown/ambiguous control, and any affected entrypoint. Test observable contract rather than private call order.
8. State the inspected owner/consumer paths and the remaining uninspected scope. A clean verdict requires a completed declared scope, not a grep-only search.

If the counterfactual changes the fact itself or changes a declared consumer obligation, it is **not** proof of this failure class.

## DO NOT REPORT

Do not report:
- a deliberate, documented contract-breaking version migration whose consumers are updated together;
- consumers enforcing different legitimate responsibilities, including integrity validation at a trust boundary;
- independently scoped facts merely because they use similar words or representations;
- conservative `unknown` or ambiguous results where the owner cannot prove an exact relationship;
- display-only formatting that does not change interpreted meaning or an independent obligation;
- duplicate implementation *alone* without a demonstrated consumer-contract dependency. Use the neighboring ownership specialist.

### Neighboring skills

- `single-source-of-truth-review` — different production paths independently establish the same authoritative fact.
- `semantic-redecision-review` — consumers independently answer the same semantic question.
- `resolved-fact-regression-review` — a resolved fact is discarded and reconstructed from raw input.
- `unknown-state-collapse-review` — uncertainty is collapsed into false/empty/zero/success, irrespective of owner evolution.
- `static-evidence-overclaim-review` — an analyzer claims exact evidence it cannot prove.
- `test-contract-coupling-review` — tests freeze internal choreography rather than meaningful behavior.

Use **this** skill when a canonical owner is identifiable but a *consumer relies on historical or accidental owner-result behavior*, and a legitimate owner refinement exposes the dependency.

## PREFER

Keep one owner-produced, explicit semantic result and make consumers exhaustively handle contract-relevant cases. Delete duplicate interpretation and obsolete fallbacks where supported. Preserve useful downstream domain behavior without teaching the consumer how the owner reached its answer.

Prefer paired semantic-obligation regressions over snapshots of owner internals. Avoid new generic adapters, compatibility wrappers, redundant gatekeepers, or "fixes" that force the owner to keep returning an incorrect old classification.

## OUTPUT

Return `# Canonical Consumer Contract Review` with:
- owner, declared result contract, and reviewed consumer paths;
- historical and refined result for the same fact;
- the exact consumer assumption and proven difference in behavior;
- whether the difference is unauthorized or intentionally contract-driven;
- smallest canonical-consumption correction, redundant code that can disappear;
- paired consumer regressions and uncertainty controls;
- inspected and uninspected scope.

End with one:
- `FINDING` — a reachable consumer demonstrably violates its independent obligation because of an incidental owner-result dependency;
- `CLEAN` — the declared owner/consumer scope was traced, relevant refinements were exercised, and no such dependency remained;
- `LEAVE ALONE` — the suspected change is an intentional contract transition or distinct responsibility;
- `INSUFFICIENT EVIDENCE` — the owner contract, reachable consumer, or decisive counterfactual could not be established.
