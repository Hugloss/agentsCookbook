---
name: dogfood-saturation-loop
description: Runs same-branch dogfood repair campaigns that re-test patched behavior and defer broad CI until saturation.
license: MIT
---

# Dogfood Saturation Loop

Standalone repair-campaign skill for driving one bounded semantic surface through repeated dogfood and repair until the latest candidate survives fresh probing and required broad validation.

## INVARIANT

> **A repair campaign is complete only when the latest candidate has no unresolved in-scope qualifying defect, survives a complete fresh adversarial dogfood pass of the repaired surface, and passes required broad validation on the exact candidate or shipping artifact being qualified.**

A green known regression is local evidence, not campaign completion.

Evidence is admissible only when it is bound strongly enough to identify:
- the exact bytes or semantics exercised;
- the relevant execution context when that context can change behavior;
- the representation exercised, such as source tree, package, archive, image, or installed artifact;
- the declared campaign scope and probe completeness needed to interpret negative evidence.

A later candidate-affecting change invalidates any earlier proof whose noninterference with that proof has not been established.

## HUNT

Hunt for premature or stale campaign closure such as:
- known regressions turn green and the branch immediately moves to CI or PR;
- the patched behavior is never dogfooded after a repair batch;
- the claimed "fresh" pass merely replays already-known regressions;
- a timeout, truncation, skipped required probe, or unknown execution state is reported as `NO_QUALIFYING_DEFECT`;
- campaign scope is narrowed after a difficult defect appears so that the defect becomes "out of scope";
- dogfood or broad-validation evidence belongs to older or different bytes than the candidate being qualified;
- a commit or branch name is used as candidate identity while staged, tracked, untracked, or generated content changes the bytes actually exercised;
- source-tree evidence is reused for a packaged or shipping artifact without provenance-bound transformation or relevant artifact replay;
- evidence from one materially relevant execution mode or environment is reused as if it proved another;
- a post-repair pass exposes an in-scope qualifying defect but the defect is deferred to another PR without a real predeclared scope boundary;
- an unresolved in-scope qualifying defect is recorded but the surface is still called saturated;
- broad or CI-equivalent validation runs after each small repair while the same bounded surface still has obvious unexercised interactions;
- CI exposes an in-scope defect, the defect is repaired, and saturation is retained without another fresh dogfood pass;
- the surface is saturated but required final validation is FAIL or INCOMPLETE and the campaign still claims completion;
- the campaign expands without limit into unrelated repository defects instead of preserving its bounded semantic surface.

## PROVE

Before reporting premature closure, identify:
- **Starting authority** — the repository/source identity from which the campaign began;
- **Frozen campaign scope** — the semantic/product surface fixed before substantive discovery;
- **Current candidate identity** — the exact bytes or semantic identity being claimed as the current result;
- **Representation** — source, package, archive, image, installed artifact, or other form actually exercised;
- **Execution context** — only dimensions materially relevant to interpretation, such as native/hosted mode, runtime mode, feature flags, platform, or authority environment;
- **Latest candidate-affecting repair** — the last change relevant to the surface or final qualification;
- **Known validation** — focused regressions or checks proving already-reproduced defects;
- **Fresh dogfood evidence** — probing performed against the current candidate after the latest relevant repair;
- **Probe completeness** — whether every declared required probe completed without unresolved timeout, truncation, skipped required work, or unknown execution state;
- **Freshness** — evidence that the pass attacks patched semantics or adjacent/interacting variants rather than only replaying the known regression;
- **Scope relation** — whether any newly exposed defect belongs to the frozen campaign surface;
- **Continuation decision** — whether an in-scope qualifying defect returned to the same branch and defect queue;
- **Representation provenance** — when source is transformed into a shipping artifact, how the artifact is bound to the qualified source and whether relevant semantics require replay on the artifact;
- **Final qualification** — required broad/CI-equivalent validation and the exact candidate/artifact plus relevant context it exercised.

A qualifying fresh pass should exercise the changed behavior plus relevant neighboring invariants where they exist. Examples include boundary/over-bound, omitted/empty, positive/negative evidence, complete/truncated observation, fresh/stale identity, ordering/repetition, repair interactions, or equivalent public/runtime surfaces.

Do not require every example category when it is irrelevant. Require evidence that the selected variants are causally related to the repaired semantics.

`NO_QUALIFYING_DEFECT` is admissible only when the declared required dogfood probe set completed. If required probing timed out, truncated, was skipped, or ended in unknown state, preserve `INCOMPLETE` and do not infer absence.

Evidence is stale when it was produced from different bytes, a materially different execution context, or a different representation and no explicit admissible equivalence or noninterference argument connects it to the current claim.

## DO NOT REPORT

Do not report merely because:
- a campaign contains only one real defect, if that repair received meaningful complete fresh post-repair dogfood and no new in-scope defect was found;
- several independently reproduced defects are repaired in one PR;
- focused validation is used between repair batches;
- full CI is deferred until surface saturation;
- broad validation is run early because it is required to unblock further dogfood or establish missing execution evidence;
- fresh dogfood exposes an unrelated defect outside the frozen campaign surface, when that defect is preserved as separate evidence rather than silently discarded;
- an unrelated change occurs after surface dogfood when its noninterference with the surface is actually established; final qualification must still bind the candidate being shipped;
- the current candidate is not committed, when a deterministic identity covers the exact working-tree/generated bytes actually exercised;
- source evidence is reused for a shipping artifact when repository authority proves a deterministic provenance-bound transformation and the exercised semantics are representation-invariant;
- no arbitrary minimum number of defects was found.

Do not turn "more testing is possible" into a finding. The question is whether the current candidate received meaningful complete fresh attack on the frozen surface, whether newly exposed in-scope defects were resolved, and whether required final qualification passed on the candidate or artifact being shipped.

## PREFER

Optimize for semantic-surface exhaustion rather than PR count, commit count, repeated proof of the same repair, fixed defect quotas, or fixed elapsed time.

Prefer:

```text
establish starting authority
-> freeze bounded campaign scope
-> dogfood current behavior
-> queue independently reproduced in-scope defects
-> batch repairs at owning semantic boundaries
-> establish exact current candidate identity over exercised bytes
-> focused validation bound to candidate + relevant context + representation
-> complete fresh dogfood bound to the same evidence identity
-> repair newly exposed in-scope defects
-> new candidate identity; prior affected proof becomes stale
-> repeat until a complete fresh pass yields NO_QUALIFYING_DEFECT
-> mark surface SATURATED, not campaign complete
-> bind source -> shipping artifact when a representation transition exists
-> required broad/CI-equivalent validation on the exact shipping candidate/artifact
-> if broad validation causes an in-scope repair, revoke surface saturation and re-enter focused validation + fresh dogfood
-> if required final validation is FAIL or INCOMPLETE, campaign is BLOCKED_INCOMPLETE
-> only a fully qualified current candidate/artifact may end SATURATED
```

Spend campaign budget on discovering second-order defects and repair interactions instead of repeatedly proving one already-closed reproduction.

## EXECUTION LOOP

### Establish authority, freeze scope, and identify candidates

At campaign start:
- establish current repository/source authority and record the exact starting identity;
- select and **freeze** one bounded semantic/product surface before substantive defect discovery;
- record enough inclusion/exclusion criteria to classify later findings without redefining scope opportunistically;
- identify the surface's owning implementation, focused verifiers, and expensive broad validation;
- keep one branch and one live defect queue.

A later scope change requires explicit evidence that the original boundary was wrong or execution became impossible. Do not retroactively reclassify an already-observed defect solely to obtain saturation. Preserve both the original classification evidence and the reason for any admitted scope change.

Track the evolving **current candidate identity** separately from immutable starting authority.

Candidate identity must cover the exact bytes or semantics actually exercised. A commit, tree, or branch identity is insufficient when staged, modified, untracked, generated, overlaid, or projected content changes exercised behavior. A deterministic working-tree/content digest is acceptable and does not require committing every repair batch.

Re-establish starting authority if the repository base or another governing source changes materially.

### Discover before narrowing

Prefer collecting multiple independent reproductions before expensive validation when the first defect does not block further exploration.

For each candidate defect record:
- observed behavior;
- violated behavioral invariant;
- minimal reproduction;
- likely owning semantic boundary;
- whether another queued defect already explains it;
- whether it belongs to the frozen campaign surface.

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

### Bind evidence to context and representation

For each focused or dogfood result, bind only the execution dimensions that can materially change the result. Examples may include:
- native versus hosted execution;
- source versus packaged/installable form;
- runtime or authority mode;
- platform/runtime version when relevant;
- feature/configuration state when relevant.

Do not create a universal environment fingerprint. Bind the dimensions required to interpret the evidence safely.

When the candidate moves from source to another representation such as ZIP, wheel, container, generated bundle, or installed artifact:
- record the source candidate identity;
- record the resulting artifact identity;
- record the transformation/provenance that connects them;
- determine whether the dogfooded semantics are invariant under that transformation.

If invariance is proven by repository authority, source dogfood may remain admissible. Otherwise replay the relevant dogfood against the shipping representation.

### Re-dogfood the patch

Every in-scope repair batch must be dogfooded again before surface saturation.

Do not merely replay the original failing examples. Attack the semantics introduced by the patch with relevant adjacent or interacting variants.

Bind the dogfood result to the exact current candidate bytes, relevant execution context, and representation.

A fresh pass may produce `NO_QUALIFYING_DEFECT` only after all declared required probes complete. Timeout, truncation, skipped required probes, or unknown execution state produces `INCOMPLETE`, not negative evidence.

A newly exposed **in-scope** qualifying defect returns to the same branch and defect queue.

A newly exposed **out-of-scope** defect is preserved as separate evidence or follow-up work and does not automatically expand the current campaign.

### Surface saturation

The selected surface reaches saturation only when:
- every reproduced in-scope qualifying defect is repaired;
- no unresolved in-scope qualifying defect remains;
- focused validation for the exercised surface passes against the current evidence identity;
- a complete fresh post-repair adversarial dogfood pass has been completed against that same evidence identity;
- that pass yields no new in-scope qualifying correctness defect;
- relevant obvious neighboring variants and repair interactions have been exercised.

`PASS` from known regressions alone is not surface saturation.

`NO_QUALIFYING_DEFECT` from incomplete observation is inadmissible.

An unresolved in-scope defect means `CONTINUE_DOGFOOD` when repair work can proceed or `BLOCKED_INCOMPLETE` when it cannot. It never permits surface saturation.

**Any subsequent in-scope repair revokes surface saturation.** The new candidate must return through focused validation and a complete fresh dogfood pass before the surface may be called saturated again.

### Final qualification

Surface saturation and candidate qualification are separate states.

After surface saturation, run every repository-required broad/CI-equivalent check needed for the candidate to be considered complete. Bind those results to the exact current shipping candidate/artifact and relevant execution context.

If required broad validation exposes an in-scope qualifying defect:
1. revoke surface saturation;
2. reproduce and repair it on the same branch;
3. establish the new exact candidate identity;
4. run affected focused validation;
5. dogfood the newly patched behavior again with complete required probes;
6. regain surface saturation;
7. rebuild/rebind any shipping representation affected by the repair;
8. rerun required broad/CI-equivalent validation against that exact candidate/artifact.

If required broad validation exposes an out-of-scope defect that makes final qualification FAIL or INCOMPLETE, preserve the frozen scope boundary but end `BLOCKED_INCOMPLETE`; surface saturation does not authorize shipping an unqualified candidate.

If the candidate or shipping artifact changes after final qualification, final qualification is stale unless repository authority explicitly proves the change non-semantic for that proof.

Do not use broad validation as a substitute for fresh post-repair dogfood.

Preserve observed `PASS`, `FAIL`, `INCOMPLETE`, and `NO_QUALIFYING_DEFECT` outcomes exactly. Do not convert incomplete evidence into success.

## OUTPUT

Return `# Dogfood Saturation Loop` with:
- starting authority;
- frozen campaign surface and inclusion/exclusion boundary;
- current candidate identity covering the exact exercised bytes;
- representation and materially relevant execution context;
- reproduced defect queue;
- repair batches and candidate-identity changes;
- focused validation and bound evidence identity;
- fresh post-repair dogfood passes, declared required probes, completeness, variants exercised, and bound evidence identity;
- in-scope versus out-of-scope newly exposed defects;
- any admitted scope changes and their evidence;
- source-to-artifact provenance/equivalence when a shipping representation exists;
- surface saturation invalidations/re-entry, if any;
- required broad/CI-equivalent validation and bound shipping identity/context;
- surface saturation status;
- final qualification status;
- unresolved evidence.

End with exactly one:
- `SATURATED` — the frozen surface is saturated and all required final qualification is PASS for the exact current shipping candidate/artifact;
- `CONTINUE_DOGFOOD` — in-scope repair or complete fresh dogfood work remains and can continue;
- `BLOCKED_INCOMPLETE` — required evidence/qualification is incomplete or failing, a required probe did not complete, an unresolved defect cannot currently be repaired, or the exercised/shipping identity cannot be proven.
