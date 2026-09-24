---
name: dogfood-saturation-loop
description: Runs same-branch dogfood repair campaigns that re-test patched behavior and defer broad CI until saturation.
license: MIT
---

# Dogfood Saturation Loop

Standalone repair-campaign skill for driving one bounded semantic surface through repeated dogfood and repair until the latest candidate survives fresh probing and required broad validation.

## INVARIANT

> **A repair campaign is complete only when the latest candidate has no unresolved in-scope qualifying defect, survives fresh adversarial dogfood of the repaired surface, and passes required broad validation on that same candidate identity.**

A green known regression is local evidence, not campaign completion.

A source or artifact change invalidates any earlier proof whose result is not demonstrably bound to the resulting candidate identity. If noninterference with the selected surface cannot be established, rerun the affected proof.

## HUNT

Hunt for premature or stale campaign closure such as:
- known regressions turn green and the branch immediately moves to CI or PR;
- the patched behavior is never dogfooded after a repair batch;
- the claimed "fresh" pass merely replays already-known regressions;
- dogfood or broad-validation evidence belongs to an older candidate than the one being qualified;
- a post-repair pass exposes an in-scope qualifying defect but the defect is deferred to another PR without a real scope boundary;
- an unresolved in-scope qualifying defect is recorded but the surface is still called saturated;
- broad or CI-equivalent validation runs after each small repair while the same bounded surface still has obvious unexercised interactions;
- CI exposes an in-scope defect, the defect is repaired, and saturation is retained without another fresh dogfood pass;
- the surface is saturated but required final validation is FAIL or INCOMPLETE and the campaign still claims completion;
- the campaign expands without limit into unrelated repository defects instead of preserving a bounded semantic surface.

## PROVE

Before reporting premature closure, identify:
- **Starting authority** — the repository/source identity from which the campaign began;
- **Campaign surface** — the bounded semantic/product surface intentionally being exhausted;
- **Current candidate identity** — the exact source/artifact identity being claimed as the result;
- **Latest candidate-affecting repair** — the last change relevant to the surface or final qualification;
- **Known validation** — focused regressions or checks proving already-reproduced defects;
- **Fresh dogfood evidence** — probing performed against the current candidate after the latest relevant repair;
- **Freshness** — evidence that the pass attacks patched semantics or adjacent/interacting variants rather than only replaying the known regression;
- **Scope relation** — whether any newly exposed defect belongs to the selected campaign surface;
- **Continuation decision** — whether an in-scope qualifying defect returned to the same branch and defect queue;
- **Final qualification** — required broad/CI-equivalent validation and the candidate identity it actually exercised.

A qualifying fresh pass should exercise the changed behavior plus relevant neighboring invariants where they exist. Examples include boundary/over-bound, omitted/empty, positive/negative evidence, complete/truncated observation, fresh/stale identity, ordering/repetition, repair interactions, or equivalent public/runtime surfaces.

Do not require every example category when it is irrelevant. Require evidence that the selected variants are causally related to the repaired semantics.

Evidence is stale when it was produced from a different candidate identity and no explicit noninterference argument makes that difference irrelevant to the claimed proof.

## DO NOT REPORT

Do not report merely because:
- a campaign contains only one real defect, if that repair received meaningful fresh post-repair dogfood and no new in-scope defect was found;
- several independently reproduced defects are repaired in one PR;
- focused validation is used between repair batches;
- full CI is deferred until surface saturation;
- broad validation is run early because it is required to unblock further dogfood or establish missing execution evidence;
- fresh dogfood exposes an unrelated defect outside the declared campaign surface, when that defect is preserved as separate evidence rather than silently discarded;
- an unrelated change occurs after surface dogfood when its noninterference with the surface is actually established; final qualification must still bind the candidate being shipped;
- no arbitrary minimum number of defects was found.

Do not turn "more testing is possible" into a finding. The question is whether the current candidate received meaningful fresh attack on the bounded surface, whether newly exposed in-scope defects were resolved, and whether required final qualification passed on the candidate being shipped.

## PREFER

Optimize for semantic-surface exhaustion rather than PR count, commit count, repeated proof of the same repair, fixed defect quotas, or fixed elapsed time.

Prefer:

```text
establish starting authority and bounded surface
-> dogfood current behavior
-> queue independently reproduced in-scope defects
-> batch repairs at owning semantic boundaries
-> establish current candidate identity
-> focused validation bound to that candidate
-> fresh dogfood of that candidate's patched behavior
-> repair newly exposed in-scope defects
-> new candidate identity; prior affected proof becomes stale
-> repeat until the current candidate yields NO_QUALIFYING_DEFECT
-> mark surface SATURATED, not campaign complete
-> required broad/CI-equivalent validation bound to the same current candidate
-> if broad validation causes an in-scope repair, revoke surface saturation and re-enter focused validation + fresh dogfood
-> if any required final validation is FAIL or INCOMPLETE, campaign is BLOCKED_INCOMPLETE
-> only a fully qualified current candidate may end SATURATED
```

Spend campaign budget on discovering second-order defects and repair interactions instead of repeatedly proving one already-closed reproduction.

## EXECUTION LOOP

### Establish authority and candidate identity

At campaign start:
- establish current repository/source authority and record the exact starting identity;
- select one bounded semantic/product surface;
- identify its owning implementation, focused verifiers, and expensive broad validation;
- keep one branch and one live defect queue.

Track the evolving **current candidate identity** separately from the immutable starting authority. The identity may be a commit/tree, content digest, package/archive digest, or another repository-owned identity strong enough to prove which bytes or semantics were exercised.

After a candidate-affecting repair, establish the new candidate identity before claiming subsequent validation or dogfood evidence for it.

Re-establish starting authority if the repository base or other governing source changes materially.

### Discover before narrowing

Prefer collecting multiple independent reproductions before expensive validation when the first defect does not block further exploration.

For each candidate defect record:
- observed behavior;
- violated behavioral invariant;
- minimal reproduction;
- likely owning semantic boundary;
- whether another queued defect already explains it;
- whether it belongs to the declared campaign surface.

Do not use a fixed defect quota.

### Repair in batches

Repair at owning semantic boundaries rather than stacking symptom patches.

During a batch:
- reuse already-established repository structure and commands;
- run only focused checks needed to keep the batch workable;
- batch nearby independent edits before expensive validation;
- add regressions for meaningful observable behavior, authority, security, isolation, identity, provenance, selection, receipts, or reproduced defects;
- avoid tests whose only purpose is proving internal names, decomposition, filenames, or refactor structure.

A green focused test closes a reproduction. It does not close the campaign.

Any in-scope repair invalidates prior surface saturation and any prior dogfood evidence that does not bind the new candidate.

### Re-dogfood the patch

Every in-scope repair batch must be dogfooded again before surface saturation.

Do not merely replay the original failing examples. Attack the semantics introduced by the patch with relevant adjacent or interacting variants.

Bind the dogfood result to the current candidate identity. If the exercised bytes or generation cannot be established, the evidence is incomplete.

A newly exposed **in-scope** qualifying defect returns to the same branch and defect queue.

A newly exposed **out-of-scope** defect is preserved as separate evidence or follow-up work and does not automatically expand the current campaign.

### Surface saturation

The selected surface reaches saturation only when:
- every reproduced in-scope qualifying defect is repaired;
- no unresolved in-scope qualifying defect remains;
- focused validation for the exercised surface passes against the current candidate;
- a fresh post-repair adversarial dogfood pass has been completed against that same current candidate;
- that pass yields no new in-scope qualifying correctness defect;
- relevant obvious neighboring variants and repair interactions have been exercised.

`PASS` from known regressions alone is not surface saturation.

`NO_QUALIFYING_DEFECT` is meaningful only for a fresh post-repair pass that actually challenges the current patched behavior.

An unresolved in-scope defect means `CONTINUE_DOGFOOD` when repair work can proceed or `BLOCKED_INCOMPLETE` when it cannot. It never permits surface saturation.

**Any subsequent in-scope repair revokes surface saturation.** The new candidate must return through focused validation and a fresh dogfood pass before the surface may be called saturated again.

### Final qualification

Surface saturation and candidate qualification are separate states.

After surface saturation, run every repository-required broad/CI-equivalent check needed for the candidate to be considered complete. Bind those results to the exact current candidate identity.

If required broad validation exposes an in-scope qualifying defect:
1. revoke surface saturation;
2. reproduce and repair it on the same branch;
3. establish the new candidate identity;
4. run affected focused validation;
5. dogfood the newly patched behavior again;
6. regain surface saturation;
7. rerun required broad/CI-equivalent validation against that candidate.

If required broad validation exposes an out-of-scope defect that makes final qualification FAIL or INCOMPLETE, preserve the scope boundary but end `BLOCKED_INCOMPLETE`; surface saturation does not authorize shipping an unqualified candidate.

If the candidate changes after final qualification, final qualification is stale and must be rerun unless the repository's qualification authority explicitly proves the change non-semantic and admissible without rerun.

Do not use broad validation as a substitute for fresh post-repair dogfood.

Preserve observed `PASS`, `FAIL`, `INCOMPLETE`, and `NO_QUALIFYING_DEFECT` outcomes exactly. Do not convert incomplete evidence into success.

## OUTPUT

Return `# Dogfood Saturation Loop` with:
- starting authority;
- campaign surface and scope boundary;
- current candidate identity;
- reproduced defect queue;
- repair batches and candidate-identity changes;
- focused validation and bound candidate identity;
- fresh post-repair dogfood passes, variants exercised, and bound candidate identity;
- in-scope versus out-of-scope newly exposed defects;
- surface saturation invalidations/re-entry, if any;
- required broad/CI-equivalent validation and bound candidate identity;
- surface saturation status;
- final qualification status;
- unresolved evidence.

End with exactly one:
- `SATURATED` — the selected surface is saturated and all required final qualification is PASS for the current candidate;
- `CONTINUE_DOGFOOD` — in-scope repair or fresh dogfood work remains and can continue;
- `BLOCKED_INCOMPLETE` — required evidence/qualification is incomplete or failing, an unresolved defect cannot currently be repaired, or candidate identity cannot be proven.
