---
name: test-removal-review
description: Reviews deleted, disabled, or weakened tests against active requirements and replacement evidence.
---

# Test Removal Review

Perform a standalone, read-only review of lost test protection across a change. Answer:

1. What requirement did the affected test check?
2. Does that requirement still apply?
3. What evidence now demonstrates the behavior and would detect its failure?

## INVARIANT

> **Removing or weakening a valid test does not repair the defect it exposes. An active requirement still needs meaningful verification; a green pipeline after removing its check is not evidence that the behavior works.**

Review the requirement and the evidence without assuming that the historical test must survive unchanged.

## HUNT

Inspect changes that reduce effective verification:

- deleted, renamed, moved, skipped, quarantined, or expected-to-fail tests;
- removed assertions, boundary cases, fixtures, parameters, or supported environments;
- broader tolerances, accepted errors, swallowed failures, or snapshots changed to accept incorrect behavior;
- mocks that replace the behavior being verified or assertions that only check a call happened;
- collection filters, CI conditions, job removal, non-blocking jobs, or exit-status handling that stop a relevant failure from affecting the claimed gate.

Treat these as investigation leads. Neither fewer tests nor lower coverage alone proves a defect.

## PROVE

1. **Bound the comparison.** Record the repository, base and candidate revisions, requested scope, and available diff/history. Inspect the full affected test changes, their production paths, and relevant discovery/CI configuration. Follow directly implicated replacements and supported variants beyond the initial filenames; do not shrink scope to discard a discovered gap. If the comparison or relevant files are unavailable, identify the missing evidence.
2. **Recover the obligation.** Read the old assertions, fixtures, and triggering inputs. Trace their intended observable outcome or explicit architectural constraint to the current contract, accepted decisions, and supported consumers. Classify the requirement as active, changed, retired, or unresolved. A historical test, candidate implementation, or green CI result does not alone establish the requirement. Use the project's existing decision authority; do not invent approvals or compatibility promises. Examine a claimed requirement change independently of whether it makes the candidate pass.
3. **Validate the old test.** Establish whether its oracle and setup actually check that obligation. Separate sound assertions from incorrect expectations, private choreography, nondeterministic setup, and environmental failures. A restored test failing to import or initialize is not proof of a product defect. A flaky failure can come from either the test or the product; inspect the cause before deciding.
4. **Trace replacement protection.** Locate the retained or replacement checks and compare their meaningful inputs, boundaries, failure cases, assertions, production path, and supported configurations. Check collection, execution, skip conditions, and whether failures reach the relevant gate. A matching name, executed line, mock call, test count, or passing unrelated suite does not establish equivalence. Judge coverage at the level of behavior; parameterized, property-based, integration, or differently named tests may be adequate replacements. Do not require every test to run in every job; establish which verification obligation and gate actually apply.
5. **Demonstrate the consequence.** Identify a concrete violation of an active requirement that the old valid check detected and the remaining relevant checks would miss. Use a historical regression, focused reproducer, decisive source trace, or plausible broken implementation tied to a reachable production path. Distinguish an observed product defect from a counterexample demonstrating lost failure detection. Explain whether each problem was introduced by the change, already existed, or remains unestablished. Inspect any claim that the defect was fixed against current behavior, independently of pipeline color.
6. **Challenge the conclusion.** Look for a valid requirement change, invalid old oracle, genuinely equivalent replacement, independently enforced constraint, or explicitly accepted temporary verification exception. Reconcile that evidence before reporting a finding. A quarantine or exception can acknowledge a gap; it does not demonstrate that the underlying behavior was repaired. State remaining risk without inventing a product failure.

Keep the reviewed checkout unchanged. Run focused checks only within the host's allowed execution scope. If restoring a test or injecting a counterexample is useful and permitted, do it in a disposable workspace and record adaptations; preserve the behavioral assertion. Otherwise use inspected evidence and mark execution `NOT RUN`. Record command, revision, relevant environment, and `PASS`, `FAIL`, `BLOCKED`, or `NOT RUN` for execution evidence. Never describe a proposed check or another revision's result as an executed candidate check.

## FINDING THRESHOLD

Report a material **verification gap** only when the active obligation, valid removed protection, relevant remaining verification, and concrete escaped failure are established. Cite the before/after test locations and the affected production path. State explicitly when current product behavior is unproven.

Report a **product defect** only with evidence of a reachable contract violation, such as an executed reproducer or decisive code trace. Test deletion by itself does not prove broken behavior. Distinguish a pre-existing defect whose detection was removed from a defect introduced by this change.

When the contract, replacement search, CI scope, or failure sensitivity is unresolved, record an evidence gap and the smallest check needed to resolve it. Do not promote that uncertainty to a product defect or a clean result. Use the project's severity scheme and actual impact; do not make every test deletion a blocker or require a fixed number of findings.

## DO NOT REPORT

Do not report a removal solely because:

- the requirement or supported feature was deliberately changed or retired under the project's existing authority;
- an invalid assertion or incidental implementation constraint was removed;
- a test moved, was consolidated, or was replaced by adequate behavioral verification;
- test count, line coverage, runtime, or filenames changed;
- old tests fail against intentionally changed interfaces before reaching an applicable behavioral assertion.

Check any surviving supported obligations before accepting these explanations. Do not infer intent, dishonesty, concealment, or a person's character from a technical diff.

## PREFER

Recommend the smallest correction that preserves the current requirement: repair the real defect and retain a focused regression; correct a faulty oracle; restore omitted cases or assertions; or make an adequate replacement discoverable and enforceable at its proper gate. Accept deletion of obsolete or redundant tests. Avoid preserving private implementation details or creating duplicate suites merely to retain historical test counts.

## NEIGHBORING SKILLS

- `source-change-review` owns whether a source delta fulfills the applicable requirement; this skill owns lost failure detection through a test or test-execution change. Both may inspect source and tests as evidence.
- `coverage-design-review` owns general missing behavioral coverage; this skill owns protection lost through a specific test or test-execution change.
- `test-contract-coupling-review` owns whether a test freezes incidental internals; use that distinction when judging the removed assertion.
- `baseline-self-authorization-review` owns candidate changes that weaken their own governing policy or oracle; route an independently proven authority defect there without duplicating the finding.
- `known-good-contract-reconstruction` owns historical contract recovery and repair design; this skill remains a review of the removal's justification and consequence.

These boundaries do not require loading other skills to complete this review.

When paired with `source-change-review`, use the same comparison and applicable requirements. Establish each conclusion from inspected evidence. Reconcile a shared source defect and its removed detection into one causal finding while preserving the distinct source and verification consequences. Keep independent gaps and each review's unresolved scope visible; one verdict cannot substitute for the other.

## OUTPUT

Return `# Test Removal Review` with:

- **Scope and evidence:** base/candidate revisions, inspected changes, applicable gates, and limits.
- **Requirement/evidence map:** for each affected behavior, identify the changed test/check, requirement and authority, current applicability, removal rationale and old-test validity, replacement protection and execution status, and conclusion. Group equivalent cases without hiding omitted variants.
- **Findings:** distinguish verification gaps from product defects; give evidence locations, triggering conditions, consequence, smallest correction, and decisive verification. Use `None` if none meet the threshold.
- **Justified removals and unresolved evidence:** explain accepted changes, acknowledged residual risk, missing information, and checks not run.

End with exactly one bounded verdict:

- `FINDING` — at least one material verification gap or product defect meets the proof threshold; retain any unresolved scope explicitly.
- `CLEAN` — the complete declared comparison was inspected and no loss of required protection was found; state if there were no relevant changes.
- `LEAVE ALONE` — the examined removals are positively justified by contract/test correction or adequate replacement, with no unresolved question material to that conclusion.
- `INSUFFICIENT EVIDENCE` — no finding is established and a material part of the contract, comparison, replacement protection, or execution obligation remains unresolved.

Do not turn a scoped verdict into repository-wide approval. A static conclusion can be valid, but execution remains `NOT RUN` unless it occurred.

## SOURCE

Use [Google's code-review guidance on tests](https://google.github.io/eng-practices/review/reviewer/looking-for.html#tests) for the underlying review principle: assess whether tests are valid and detect broken behavior. The repository's current requirements remain the authority for the behavior under review.
