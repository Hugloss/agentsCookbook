---
name: known-good-contract-reconstruction
description: Uses a verified known-good revision to recover behavioral contracts and design future-resilient fixes instead of restoring historical implementation details.
license: MIT
---

# Known-Good Contract Reconstruction

Use when a historical commit, tag, release, or fixture appears to behave correctly but the current implementation regresses, becomes brittle, or depends on incidental external-library return shapes. This is an evidence-led repair skill, not a blanket rollback instruction.

## INVARIANT

> **Preserve justified observable behavior, not accidental historical structure. Treat a known-good revision as evidence to investigate, not unquestionable authority over today's contract. Normalize supported representation differences at their rightful boundary; never conceal semantic differences or unknown evidence.**

## HUNT

- Regressions where a previously passing path breaks after dependency upgrades, parser/schema revisions, return-type refinements, runtime differences, or refactoring.
- Fixes that restore old branches, private types, implicit defaults, exception strings, or fallback heuristics solely because the old commit used them.
- Callers independently interpreting a third-party result instead of consuming one explicit boundary contract.
- Tests that compare to historical snapshots or concrete types but fail to protect semantic behavior.
- A compatibility wrapper that silently turns malformed, ambiguous, or unsupported values into success/empty/false.

## PROVE

1. **Pin the evidence.** Record repository, exact historical revision, current revision, affected entrypoints, dependencies, and relevant versions/environment. If the SHA cannot be verified, say so. Avoid claiming a baseline is working solely because it was labeled stable.
2. **Reproduce and compare.** Run the same meaningful input through both revisions when feasible; capture observed results and failures. If execution is unavailable, distinguish static inference from reproduction. Identify the first relevant semantic or interface divergence, not merely the first changed line.
3. **Reconstruct intent.** Derive the intended observable contract from documented requirements, public interfaces, consumers, tests, and historical behavior. Classify each historical property as guaranteed, accidental, obsolete, or unresolved. Check whether today's specification intentionally changed.
4. **Locate the owner.** Identify the single component responsible for interpreting/normalizing incoming representations; separate external dependency contract, local boundary conversion, domain semantics, and downstream consumers. Do not move authority into a second competing adapter.
5. **Design the correction.** Prefer one narrow, typed/canonical internal representation and explicit handling of each *documented or observed supported* external variant. Preserve semantic distinctions; fail clearly on invalid, ambiguous, or unsupported values. Do not guess future shapes or broadly catch all exceptions.
6. **Validate behavior and resilience.** Add a focused regression for the original failure; paired tests for historical and current supported shapes yielding equal semantics; an invalid/unknown control that fails or stays unknown; and a downstream/entrypoint test proving the observable obligation. Where feasible test an actual integration with supported dependency versions.
7. **Inspect the change surface.** Confirm no duplicate interpretation, shadow owner, newly hidden fallback, unintended API break, or performance/cost regression. Compare actual behavior after the fix, not only unit tests of the adapter.
8. **Report uncertainty.** State evidence not obtained, untested versions or representations, and any compatibility policy requiring maintainer decisions.

## DECISION RULES

- If the old behavior contradicts a deliberate documented new contract, do **not** restore it; define an explicit migration or report `LEAVE ALONE`.
- If the two revisions differ because the underlying fact changed, do **not** force equal outputs.
- If the public dependency contract only permits one type, do **not** add speculative alternatives merely for imagined future-proofing.
- If multiple return shapes have the same meaning, adapt them at one rightful boundary and test semantic equivalence.
- If supported variants have different meanings, represent that distinction explicitly rather than flattening them.
- If a stable commit is unavailable or unverifiable, investigate current contracts; mark the historical comparison as unverified.

## DO NOT REPORT

- Harmless representation changes handled by a documented interface.
- Intended breaking changes with an explicit migration path.
- Differences caused by input, configuration, or environmental drift unless controlled for.
- A supposed regression inferred solely from a source diff, passing old tests, or a commit message.
- A reason to build generic normalization infrastructure without multiple real supported consumers or variants.

## NEIGHBORING SKILLS

- `canonical-consumer-contract-review`: a known canonical result grows more precise and a downstream consumer incorrectly depends on its former shape.
- `single-source-of-truth-review`: multiple independently accepted owners for the same fact.
- `semantic-redecision-review`: a consumer recomputes upstream meaning.
- `resolved-fact-regression-review`: a previously resolved fact is discarded and rebuilt.
- `test-contract-coupling-review`: tests freeze incidental internals instead of observable behavior.

This skill owns **historical behavioral contract recovery and durable repair design**. Route independently proven ownership defects to their narrow specialist rather than raising duplicate repairs.

## PREFER

Small contract-preserving change > broad compatibility framework. One interpretation boundary > distributed call-site patches. Real supported variation > speculative future variants. Typed explicit results > exception-text/string guessing. Focused counterfactual tests > snapshots of historical implementation.

## OUTPUT

Return `# Known-Good Contract Reconstruction` with:

- **Baseline:** historical/current revision, verification status, environment and evidence.
- **Contract:** observable promises, evidence, intentional changes, uncertain assumptions.
- **Divergence:** first semantic/interface break and its reachable consequence.
- **Ownership:** external producer, canonical normalizer/owner, affected consumers.
- **Correction:** smallest implementation, deleted workarounds, and why it survives proven supported variations.
- **Proof matrix:** same-meaning old/current supported cases, invalid/ambiguous control, affected entrypoint, integration coverage and results.
- **Limits:** unchecked versions, uninspected paths, unresolved decisions.

End with exactly one:

- `FINDING` — reproduced or otherwise decisively established regression with a justified durable correction.
- `CLEAN` — verified scoped variants obey the established contract.
- `LEAVE ALONE` — the suspected regression is positively explained by intentional contract evolution or verified supported behavior; unresolved baseline or contract evidence belongs to `INSUFFICIENT EVIDENCE`.
- `INSUFFICIENT EVIDENCE` — baseline, contract, or divergence not established.

Do not claim tests passed unless they actually ran. If implementing, preserve the project's existing change/test workflow and add a focused regression for each reproduced defect.
