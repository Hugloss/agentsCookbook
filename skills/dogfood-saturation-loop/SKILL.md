---
name: dogfood-saturation-loop
description: Runs same-branch dogfood repair campaigns that re-test patched behavior and defer broad CI until saturation.
license: MIT
---

# Dogfood Saturation Loop

Standalone repair-campaign skill for driving one bounded semantic surface through repeated dogfood and repair until fresh probing stops finding qualifying correctness defects.

## INVARIANT

> **A repair campaign is not complete merely because known regressions pass. The latest repaired candidate must survive a fresh adversarial dogfood pass without exposing another in-scope qualifying defect.**

Any repair made after the most recent qualifying dogfood pass invalidates saturation.

## HUNT

Hunt for premature campaign closure such as:
- known regressions turn green and the branch immediately moves to CI or PR;
- the patched behavior is never dogfooded after a repair batch;
- the claimed "fresh" pass merely replays already-known regressions;
- a post-repair pass exposes an in-scope qualifying defect but the defect is deferred to another PR without a real scope boundary;
- broad or CI-equivalent validation runs after each small repair while the same bounded surface still has obvious unexercised interactions;
- CI exposes an in-scope defect, the defect is repaired, and saturation is retained without another fresh dogfood pass;
- the campaign expands without limit into unrelated repository defects instead of preserving a bounded semantic surface.

## PROVE

Before reporting premature closure, identify:
- **Starting authority** — the repository/source identity that bounds the campaign;
- **Campaign surface** — the semantic/product surface intentionally being exhausted;
- **Latest repair** — the last source or behavior change that could affect that surface;
- **Known validation** — focused regressions or checks proving already-reproduced defects;
- **Fresh dogfood evidence** — probing performed after the latest repair;
- **Freshness** — evidence that the pass attacks patched semantics or adjacent/interacting variants rather than only replaying the known regression;
- **Scope relation** — whether any newly exposed defect belongs to the selected campaign surface;
- **Continuation decision** — whether an in-scope qualifying defect returned to the same branch and defect queue.

A qualifying fresh pass should exercise the changed behavior plus relevant neighboring invariants where they exist. Examples include boundary/over-bound, omitted/empty, positive/negative evidence, complete/truncated observation, fresh/stale identity, ordering/repetition, repair interactions, or equivalent public/runtime surfaces.

Do not require every example category when it is irrelevant. Require evidence that the selected variants are causally related to the repaired semantics.

## DO NOT REPORT

Do not report merely because:
- a campaign contains only one real defect, if that repair received a meaningful fresh post-repair dogfood pass and no new in-scope defect was found;
- several independently reproduced defects are repaired in one PR;
- focused validation is used between repair batches;
- full CI is deferred until saturation;
- broad validation is run early because it is required to unblock further dogfood or establish missing execution evidence;
- fresh dogfood exposes an unrelated defect outside the declared campaign surface, when that defect is preserved as separate evidence rather than silently discarded;
- no arbitrary minimum number of defects was found.

Do not turn "more testing is possible" into a finding. The question is whether the latest repaired candidate received a meaningful fresh attack on the bounded surface and whether newly exposed in-scope defects were pursued.

## PREFER

Optimize for semantic-surface exhaustion rather than PR count, commit count, repeated proof of the same repair, fixed defect quotas, or fixed elapsed time.

Prefer:

```text
establish authority and bounded surface
-> dogfood current behavior
-> queue independently reproduced in-scope defects
-> batch repairs at owning semantic boundaries
-> focused validation
-> fresh dogfood of the patched behavior
-> repair newly exposed in-scope defects
-> repeat until a fresh pass yields NO_QUALIFYING_DEFECT
-> broad/CI-equivalent validation
-> if broad validation causes another in-scope repair, invalidate saturation and re-enter fresh dogfood
-> final broad validation
```

Spend campaign budget on discovering second-order defects and repair interactions instead of repeatedly proving one already-closed reproduction.

## EXECUTION LOOP

### Establish authority once

At campaign start:
- establish current repository/source authority and record the exact starting identity;
- select one bounded semantic/product surface;
- identify its owning implementation, focused verifiers, and expensive broad validation;
- keep one branch and one live defect queue.

Re-establish authority if the repository base or other governing source changes materially.

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

### Re-dogfood the patch

Every repair batch must be dogfooded again before campaign completion.

Do not merely replay the original failing examples. Attack the semantics introduced by the patch with relevant adjacent or interacting variants.

A newly exposed **in-scope** qualifying defect returns to the same branch and defect queue.

A newly exposed **out-of-scope** defect is preserved as separate evidence or follow-up work and does not automatically expand the current campaign.

### Saturation

The surface reaches saturation only when:
- every reproduced in-scope qualifying defect is repaired or explicitly preserved as unresolved evidence;
- focused validation for the exercised surface passes;
- a fresh post-repair adversarial dogfood pass has been completed against the latest repaired candidate;
- that pass yields no new in-scope qualifying correctness defect;
- relevant obvious neighboring variants and repair interactions have been exercised.

`PASS` from known regressions alone is not saturation.

`NO_QUALIFYING_DEFECT` is meaningful only for a fresh post-repair pass that actually challenges the latest patched behavior.

**Any subsequent in-scope repair revokes saturation.** The candidate must return through focused validation and a new fresh dogfood pass before `SATURATED` may be claimed again.

### Broad validation

Defer repository-wide and CI-equivalent validation until saturation unless a broad check is required to unblock the campaign.

If broad validation exposes an in-scope qualifying defect:
1. revoke saturation;
2. reproduce and repair it on the same branch;
3. run affected focused validation;
4. dogfood the newly patched behavior again;
5. regain saturation;
6. rerun the necessary broad/CI-equivalent validation.

Do not use broad validation as a substitute for fresh post-repair dogfood.

Preserve observed `PASS`, `FAIL`, `INCOMPLETE`, and `NO_QUALIFYING_DEFECT` outcomes exactly. Do not convert incomplete evidence into success.

## OUTPUT

Return `# Dogfood Saturation Loop` with:
- starting authority;
- campaign surface and scope boundary;
- reproduced defect queue;
- repair batches;
- focused validation;
- fresh post-repair dogfood passes and variants exercised;
- in-scope versus out-of-scope newly exposed defects;
- saturation invalidations/re-entry, if any;
- broad/CI-equivalent validation;
- unresolved evidence.

End with exactly one:
- `SATURATED`
- `CONTINUE_DOGFOOD`
- `BLOCKED_INCOMPLETE`
