---
name: source-change-review
description: Reviews source changes against active or explicitly changed requirements across directly affected reachable paths.
---

# Source Change Review

Perform a standalone, read-only review of implemented behavior across a source change. Answer:

1. What requirement should this change add, preserve, revise, or retire?
2. What do the affected entrypoints actually do before and after the change?
3. What evidence shows that the candidate fulfills the applicable requirement?

## INVARIANT

> **Added, modified, or removed source behavior must satisfy the applicable contract across directly affected supported paths. A passing test suite or resemblance to the previous implementation does not establish that contract.**

Own the connection between a specific source delta and its required behavior. Review additions and incomplete promised behavior as well as regressions and removals.

## HUNT

Follow source changes that alter:

- validation, defaults, boundaries, filtering, ordering, normalization, or public result shapes;
- decisions, state transitions, required effects, error propagation, cancellation, or cleanup;
- entrypoints, dispatch, registration, configuration propagation, or calls to the component that owns the behavior;
- supported callers, backends, configurations, or dependency boundaries affected by a changed contract;
- an existing protection or behavior while tests, snapshots, or documentation are changed to accept the new result.

Inspect the source that governs behavior wherever it lives; do not restrict the review to a directory named `src`. Treat these changes as leads, not findings. Follow only failure classes and supported variants made relevant by the delta or its requirements.

## PROVE

1. **Bound the comparison.** Record the repository, base and candidate revisions, or the exact supplied comparison when commits are unavailable. Inspect added, modified, deleted, and moved source, with enough surrounding code to understand its effect. Include directly implicated callers, registrations, consumers, configuration, and generated-source boundaries. Expand the scope when evidence shows another affected supported path; do not shrink it to discard a problem. Record unavailable or uninspected material without claiming repository-wide coverage.
2. **Establish the obligation.** Trace the requested behavior to the user's instruction, accepted requirements or decisions, documented interfaces, and supported consumers. Use tests and historical behavior as supporting evidence. Classify obligations as retained, added, changed, retired, or unresolved. Neither the old implementation, candidate implementation, changed tests, nor a claim in the change description alone makes a disputed contract authoritative. Use the project's existing authority; do not invent approvals, migration requirements, or compatibility promises. Accept an explicit legitimate contract change while checking obligations that remain active.
3. **Trace before and after.** Follow a supported trigger or state through the real entrypoint, relevant decisions and effects, and observable result. Compare the same relevant conditions across revisions. Check boundaries, failure paths, lifecycle effects, and supported variants where this delta makes them material. For new behavior, inspect whether dispatch, registration, argument propagation, and the actual consumer reach its owner. A required path missing from the candidate can itself be the defect; do not dismiss unwired functionality because the new helper has no callers.
4. **Prove the divergence and its attribution.** Establish the required outcome, candidate outcome, exact source-level divergence, and material consequence through a focused execution or decisive source trace. Classify it as an introduced defect, a worsened pre-existing defect, or an unmet accepted new requirement/fix. The base is a comparison point, not automatically correct. An unchanged defect unrelated to the requested change is not a new regression; keep it separate from the change verdict. A promised fix still failing its target requirement is relevant even if the defect existed before.
5. **Examine verification independently.** Read pertinent tests and evidence to understand what they establish at the reviewed revision. Candidate tests or snapshots adjusted to accept a result do not independently justify changing the requirement. A green suite, a new helper's unit test, or a deleted failing assertion cannot substitute for tracing the actual behavior. Conversely, missing tests or a hypothetical broken implementation do not prove that this candidate's source is defective. Label such concerns as verification gaps and route them to the appropriate test skill.
6. **Challenge the finding.** Inspect guards, caller preconditions, alternative enforcement at the rightful owner, intentional migrations, retirement scope, and other evidence that could make the candidate correct. Verify that a supposed removed obligation is not fulfilled elsewhere. For consumer failures after a valid canonical result refinement, locate the broken consumer obligation rather than restoring an incorrect old producer shape. State the smallest correction at the actual causal owner and the check that would demonstrate it.

Keep the reviewed checkout unchanged. Run focused checks only within the host's allowed execution scope; use a disposable workspace if a reproducer requires edits and the host permits them. Record command, revision, relevant environment, and `PASS`, `FAIL`, `BLOCKED`, or `NOT RUN` for execution evidence. Label static deductions and supplied logs separately from checks actually executed. A setup/import failure does not demonstrate a behavioral failure, and unavailable execution does not invalidate otherwise decisive source evidence.

## FINDING THRESHOLD

Report a material **source-change defect** only when all of these are established:

- an applicable requirement and the evidence that gives it authority;
- a supported trigger, state, or entrypoint required to expose the behavior;
- a specific candidate divergence with an observable consequence;
- a causal connection to this delta or an accepted requirement/fix the candidate must fulfill;
- the relevant disconfirming guards and intentional contract changes checked.

Cite the before/after source locations and affected caller or required entrypoint. Separate source proof from verification evidence. Use the project's severity scheme and actual impact; do not invent a finding quota or mark every behavior difference as a blocker.

When a material contract, caller, configuration, or comparison is missing, retain the uncertainty and name the smallest evidence needed. A finding elsewhere does not resolve that gap. Do not turn an inability to reproduce a suspected defect into a clean conclusion.

## DO NOT REPORT

Do not report these alone as source-change defects:

- intentional contract changes, feature retirement, or breaking changes permitted by the applicable requirements;
- simplification, renamed or moved code, or different internal representations that preserve required behavior;
- removed code whose obligation is fulfilled at another valid boundary or has no supported use;
- unsupported inputs, speculative interleavings, or environments excluded by the actual contract and guards;
- unrelated pre-existing defects presented as introduced regressions;
- missing tests, lower coverage, code size, naming, style, or preference for another design;
- historical tests failing on intentionally changed interfaces before reaching an applicable behavioral assertion.

Do not infer intent or a person's character from a technical change. Do not require historical compatibility when the current contract does not require it.

## PREFER

Recommend the smallest correction at the existing owner of the violated contract. Preserve justified simplifications and explicit new behavior. Recommend a focused regression for each reproduced defect, including the supported entrypoint or omitted path that exposed it. Avoid speculative compatibility layers, duplicated decisions, or a broad rewrite when a narrow correction closes the demonstrated gap.

## NEIGHBORING SKILLS

- `test-removal-review` owns lost failure detection through a specific test or test-execution change; this skill owns whether the source delta fulfills the applicable requirement. Both may inspect source and tests as evidence.
- `coverage-design-review` owns behavior that tests fail to prove, including plausible broken implementations; this skill requires a violation in the actual candidate.
- `codebase-finding-derivation` owns the general standard for deriving a finding from an observation; this skill adds a bounded source comparison, changed-contract accounting, and attribution to the delta.
- `known-good-contract-reconstruction` owns historical contract recovery and durable repair design; this review does not require a known-good revision or a repair campaign.
- Narrow semantic, lifecycle, failure, or ownership specialists own their particular causal defect. Name the relevant specialist when helpful; retain one causal finding and a coherent correction rather than duplicating their checklists or repairs.

When paired with `test-removal-review`, use the same comparison and applicable requirements. Establish each conclusion from inspected evidence. Reconcile a shared source defect and its removed detection into one causal finding while preserving the distinct source and verification consequences. Keep independent gaps and each review's unresolved scope visible; one verdict cannot substitute for the other. Neither skill requires the other to run.

## OUTPUT

Return `# Source Change Review` with:

- **Scope and evidence:** base/candidate, inspected source changes and directly affected paths, supporting evidence, and limits.
- **Requirement/behavior map:** group changes by behavior; identify the requirement and authority, retained/added/changed/retired/unresolved status, base and candidate outcomes, affected consumers or required wiring, and conclusion.
- **Findings:** give triggering conditions, source divergence, attribution, consequence, disconfirmation checked, smallest correction, and decisive verification. Use `None` when none meet the threshold.
- **Justified changes and unresolved evidence:** explain accepted simplification or contract evolution, distinguish separate verification concerns and unrelated pre-existing observations, and state checks not run.

End with exactly one bounded verdict:

- `FINDING` — at least one material source-change defect meets the proof threshold; retain any unresolved scope explicitly.
- `CLEAN` — the complete declared comparison and material directly affected supported behaviors were inspected and no applicable contract violation was found; state if there were no relevant source changes.
- `LEAVE ALONE` — the examined suspicious changes are positively justified by equivalent behavior, legitimate contract evolution, retirement, or lack of supported reachability, with no material unresolved obligation.
- `INSUFFICIENT EVIDENCE` — no finding is established and missing contract, comparison, caller/configuration, or decisive evidence prevents a scoped conclusion.

Keep the verdict local to the completed inspection. A static verdict is not a claim that runtime validation passed.
