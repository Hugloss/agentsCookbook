---
name: adversarial-repair-campaign
description: Repeatedly feeds reproduced defects into one mutable campaign candidate and attacks each repaired candidate again.
license: MIT
---

# Adversarial Repair Campaign

Use this skill when a mutable candidate needs deeper stress testing than one finding followed by one small correction. The candidate may be a working tree, branch, PR, patch series, release candidate, generated artifact, or another explicitly identified mutable representation.

## INVARIANT

> **Every reproduced in-scope defect returns to the current campaign candidate, is repaired at its semantic owner, and the resulting candidate is immediately treated as new adversarial input. Do not end or fragment the campaign merely because one defect is fixed or one validation pass turns green.**

The unit of work is the **campaign**, not the individual defect or its transport mechanism.

A repair is not an endpoint. It creates a new candidate and starts the next attack loop.

## HUNT

Hunt for shallow repair campaigns where:
- the first reproduced defect becomes the whole campaign;
- a green focused regression is treated as sufficient stress evidence;
- validation success ends discovery while adjacent attacks remain unexplored;
- each small defect creates a new campaign despite sharing one semantic surface;
- the repaired implementation is never attacked in composition with earlier repairs;
- later probes run against the original candidate instead of the newest repaired candidate;
- fixes accumulate wrappers, shims, duplicated validators, or local workarounds instead of strengthening the semantic owner;
- repair-introduced maintainability, authority, compatibility, or test-contract debt is not fed back into the loop;
- the campaign repeats one defect class instead of broadening into mutation, composition, identity, completeness, failure, and cross-surface attacks;
- expensive full qualification runs after every tiny correction even though adversarial discovery can continue safely.

## PROVE

Before changing the candidate, establish:
- **authoritative base** — the source authority from which the campaign started;
- **campaign surface** — the semantic owner plus directly affected public/runtime boundaries;
- **candidate identity** — exact current bytes/state/representation being attacked;
- **reproduction** — concrete evidence that candidate behavior violates an owned contract;
- **repair owner** — the semantic owner where the invariant belongs;
- **regression** — focused observable proof of the reproduced defect;
- **next attack** — a materially different adversarial probe against the repaired candidate.

After every repair:
1. establish the new exact candidate identity;
2. run focused validation for that repair;
3. make the repaired candidate the only current attack target;
4. attack an adjacent or interacting failure class;
5. if another defect reproduces, feed it back into the campaign and repeat.

Do not carry stale conclusions across a repair when the repair can affect them.

## ATTACK LADDER

Prefer broadening attacks rather than repeating the original reproduction:

1. **Mutation** — tamper, re-sign, reorder, alias, omit, duplicate, truncate, or mutate after validation.
2. **Composition** — combine repaired behavior with retained state, deltas, caches, retries, persistence, or another repaired path.
3. **Identity / authority** — foreign authority, stale generation, semantic no-op, semantic change, provenance, current-authority binding.
4. **Completeness / negative evidence** — partial observation, bounded results, truncation, unknown state, absence claims.
5. **Failure sequencing** — invalid authority before work, partial effects, failure after state mutation.
6. **Cross-surface convergence** — API, CLI, MCP, persisted packet, report, compact projection, artifact.
7. **Repair interaction** — attack the combined repairs for contradictory assumptions or duplicated ownership.
8. **Maintainability of authority** — verify the stronger boundary did not create wrappers, parallel validators, or duplicated policy.

Use specialist agentsCookbook skills for the actual failure class. This skill owns the **campaign feedback loop**, not every defect oracle.

## CAMPAIGN CONTINUITY

Keep reproduced in-scope defects in the same campaign when they belong to the same semantic surface and can be repaired without changing the true owner.

Campaign continuity does **not** require one Git branch or PR. Preserve the strongest exact candidate identity available for the environment.

Do not force local continuity when:
- the true semantic owner is another repository or independently versioned component;
- the new defect is materially outside the campaign surface;
- governing policy requires an independent repair stream;
- continuing would destroy evidence identity or make independent qualification impossible.

For an upstream-owned defect, repair upstream first, then re-establish the dependent candidate and resume. Never hide an upstream defect with a downstream workaround merely to keep one campaign moving.

## BATCHING

Prefer several meaningful reproduced defects per campaign before expensive broad qualification when safe.

Do not use a defect quota. A campaign with one defect can be valid if subsequent broad attacks are genuinely clean. A campaign with many defects is not complete if its newest repaired candidate has not been attacked.

Focused checks belong inside the loop. Broad qualification belongs after the attack surface stops yielding meaningful in-scope defects, unless a broad check is needed earlier to unblock discovery.

## STOP CONDITION

Do not stop because:
- the candidate has accumulated several repairs;
- one regression passes;
- CI or another validation surface is green;
- the original reported issue is fixed;
- no defect appeared in one narrow follow-up probe.

Hand off to `dogfood-saturation-loop` for final saturation/qualification semantics. A broad pass that finds another qualifying defect resets any clean-pass count because the candidate changed.

## PREFER

```text
establish authoritative base + exact candidate
-> attack candidate broadly
-> reproduce qualifying defect
-> repair at semantic owner
-> add focused regression
-> focused validation
-> establish repaired candidate identity
-> attack repaired candidate again
-> reproduce next defect
-> feed it back into the same campaign
-> attack repair interactions
-> broaden across mutation / composition / identity / completeness / surfaces
-> repeat until broad attacks stop yielding qualifying defects
-> hand exact candidate to saturation/final qualification
```

Avoid prematurely fragmenting one semantic campaign into independent tiny repair cycles merely because the environment happens to represent candidates as commits, branches, PRs, patches, or artifacts.

## OUTPUT

Return `# Adversarial Repair Campaign` with:
- authoritative base;
- current candidate identity and representation;
- campaign surface;
- reproduced defect queue;
- repairs and semantic owners;
- regressions and focused validation;
- attack classes already exercised;
- next materially different attack;
- repair interactions checked;
- unresolved or upstream-owned defects;
- whether broad qualification is intentionally deferred.

End with exactly one:
- `ATTACK_AGAIN` — a current candidate exists and further in-scope adversarial work remains;
- `READY_FOR_SATURATION` — repeated broad attacks against the latest candidate yielded no new qualifying in-scope defect and it can move to final saturation/qualification;
- `BLOCKED_INCOMPLETE` — required authority, reproduction, identity, upstream repair, or attack evidence is unavailable.
