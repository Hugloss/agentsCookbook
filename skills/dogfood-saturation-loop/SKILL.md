---
name: dogfood-saturation-loop
description: Runs same-branch dogfood repair campaigns that re-test patched behavior and defer broad CI until saturation.
license: MIT
---

# Dogfood Saturation Loop

Standalone repair-campaign execution skill for driving one semantic surface through repeated dogfood and repair until fresh probing stops finding qualifying correctness defects.

## INVARIANT

> **A repair campaign is not complete merely because its known regressions pass; patched behavior must survive a fresh adversarial dogfood pass without exposing another qualifying defect.**

## RUN

At campaign start:
- establish current repository/source authority once and record the exact starting identity;
- select one bounded semantic/product surface;
- identify its owning implementation, focused verifiers, and expensive broad validation;
- keep one branch and one live defect queue for the campaign.

Use this control loop:

```text
dogfood current surface
-> reproduce qualifying defects
-> batch repairs at owning semantic boundaries
-> run cheapest focused validation needed for the batch
-> dogfood the patched surface again
-> expand around neighboring invariants and fix interactions
-> repeat until a fresh adversarial pass yields no qualifying defect
-> run broad/CI-equivalent validation
```

A green focused test closes one reproduction. It does not close the campaign.

## DISCOVER BEFORE NARROWING

Prefer collecting multiple independent reproductions before expensive validation when the first defect does not block further exploration.

Keep each defect distinct by recording:
- observed behavior;
- violated behavioral invariant;
- minimal reproduction;
- likely owning semantic boundary;
- whether another queued defect already explains it.

Do not use a fixed defect quota. Continue while the chosen surface still yields evidence-backed qualifying defects.

## REPAIR IN BATCHES

Repair at the owning semantic boundary rather than stacking symptom patches.

During a repair batch:
- reuse already-established repository structure and commands instead of rediscovering unchanged context;
- run only focused checks needed to keep the batch workable;
- batch nearby independent edits before expensive validation;
- add regressions for meaningful observable behavior, authority, security, isolation, identity, provenance, selection, receipts, or reproduced defects;
- do not add tests whose only purpose is proving internal names, decomposition, filenames, or refactor structure.

Do not run full CI merely because one repair becomes green.

## RE-DOGFOOD THE PATCH

Every repair batch must be dogfooded again before campaign completion.

Do not merely replay the original failing examples. Attack the semantics introduced by the patch with adjacent and interacting cases such as:
- exact-bound versus over-bound;
- omitted versus explicit-empty;
- positive versus negative evidence;
- complete versus truncated observation;
- fresh versus stale identity or provenance;
- repeated execution and ordering changes;
- interactions between two repairs;
- source/package/runtime or API/CLI/MCP equivalents when relevant.

A newly exposed defect returns to the same branch and defect queue.

## SATURATION

The surface reaches saturation only when:
- every reproduced qualifying defect is repaired or explicitly preserved as unresolved evidence;
- focused validation for the exercised surface passes;
- a fresh post-repair adversarial dogfood pass has been completed;
- that fresh pass yields no new qualifying correctness defect;
- obvious neighboring variants and interactions of the repaired behavior have been exercised.

`PASS` from known regressions alone is not saturation.

`NO_QUALIFYING_DEFECT` is meaningful only for the fresh post-repair dogfood pass that actually exercised the patched behavior.

## BROAD VALIDATION

Defer repository-wide and CI-equivalent validation until saturation unless a broad check is required to unblock the campaign.

After broad validation:
- treat newly exposed failures as campaign evidence;
- repair qualifying defects on the same branch when they belong to the selected surface;
- rerun affected focused/broad checks;
- return to full CI-equivalent validation only when the campaign is again ready.

Preserve observed `PASS`, `FAIL`, `INCOMPLETE`, and `NO_QUALIFYING_DEFECT` outcomes exactly. Do not convert incomplete evidence into success.

## DO NOT REPORT

Do not call a campaign incomplete merely because:
- it contains several independent repairs in one PR;
- focused validation was used between repair batches;
- full CI was intentionally deferred until saturation;
- no arbitrary minimum number of defects was found.

Do report premature closure when known regressions are green but no fresh post-repair dogfood pass challenged the patched behavior, or when that pass exposed a qualifying defect and the campaign stopped anyway.

## PREFER

Optimize for semantic-surface exhaustion rather than PR count, commit count, repeated proof of the same repair, or fixed elapsed time.

Spend the campaign budget on discovering additional defects and second-order interactions. Once sufficient evidence establishes that one repair works, attack a neighboring invariant instead of repeatedly proving the same case.

## REVIEW MODE

When reviewing an existing campaign rather than executing one, apply the same invariant.

Return a finding only when the campaign claims completion without a qualifying fresh post-repair dogfood pass, ignores a qualifying defect found by that pass, or repeatedly escalates to expensive broad validation while the same bounded surface still has unexercised repair interactions.

## OUTPUT

Return `# Dogfood Saturation Loop` with:
- starting authority;
- selected semantic surface;
- reproduced defect queue;
- repair batches;
- focused validation performed;
- post-repair dogfood passes and expansions;
- saturation status;
- broad/CI-equivalent validation;
- unresolved evidence.

End with one of:
- `SATURATED`
- `CONTINUE_DOGFOOD`
- `BLOCKED_INCOMPLETE`
