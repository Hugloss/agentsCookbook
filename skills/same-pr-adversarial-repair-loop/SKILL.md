---
name: same-pr-adversarial-repair-loop
description: Stress-tests one PR by feeding every reproduced defect back into the same campaign branch and attacking the repaired head again.
license: MIT
---

# Same-PR Adversarial Repair Loop

Use this skill when a PR or candidate branch needs deeper stress testing than one finding followed by one small correction.

## INVARIANT

> **Every reproduced in-scope defect is repaired on the current campaign branch at its semantic owner, and the repaired head is immediately treated as new adversarial input. Do not split the campaign merely because one defect is fixed or CI turns green.**

The unit of work is the **campaign**, not the individual defect.

A repair is not an endpoint. It changes the attack surface and starts the next loop.

## HUNT

Hunt for shallow PR campaigns where:
- the first reproduced defect becomes the whole PR;
- a green focused regression is treated as sufficient stress evidence;
- CI success ends discovery while adjacent attacks remain unexplored;
- each small defect creates a new branch or PR despite sharing one semantic campaign surface;
- the repaired implementation is never attacked as a composition with earlier repairs;
- later probes run against the original base instead of the newest repaired head;
- fixes accumulate wrappers, shims, duplicated validators, or local workarounds instead of strengthening the semantic owner;
- a repair introduces maintainability, formatting, authority, compatibility, or test-contract debt that is not fed back into the loop;
- the campaign repeatedly proves the same defect class instead of broadening into mutation, composition, identity, completeness, failure, and cross-surface attacks;
- expensive full qualification runs after every tiny correction even though useful adversarial discovery can continue first.

## PROVE

Before changing code, establish:
- **campaign base** — exact authoritative base identity;
- **campaign branch / PR** — one current branch that receives in-scope repairs;
- **campaign surface** — the semantic owner plus directly affected public/runtime boundaries;
- **current head identity** — exact bytes being attacked;
- **reproduction** — concrete evidence that a candidate behavior violates an owned contract;
- **repair owner** — the semantic owner where the invariant belongs;
- **regression** — focused observable proof of the reproduced defect;
- **next attack** — at least one materially different adversarial probe against the repaired head.

After every repair:
1. identify the new exact head;
2. run focused validation for the repair;
3. treat that repaired head as the only current attack candidate;
4. attack an adjacent or interacting failure class;
5. if another defect reproduces, repair it on the same campaign branch and repeat.

Do not carry stale conclusions across a repair when the repair can affect them.

## ATTACK LADDER

Prefer broadening attacks rather than repeating the original reproduction:

1. **Mutation** — tamper, re-sign, reorder, alias, omit, duplicate, truncate, or mutate after validation.
2. **Composition** — combine repaired behavior with retained state, deltas, caches, retries, persistence, or another repaired path.
3. **Identity / authority** — foreign repository, stale generation, semantic no-op, semantic change, provenance, current-authority binding.
4. **Completeness / negative evidence** — partial observation, bounded results, truncation, unknown state, absence claims.
5. **Failure sequencing** — invalid authority before work, partial effects, failure after state mutation.
6. **Cross-surface convergence** — API, CLI, MCP, persisted packet, report, compact projection, artifact.
7. **Repair interaction** — attack the combined set of fixes for contradictory assumptions or duplicated ownership.
8. **Maintainability of authority** — verify the stronger boundary did not create wrappers, parallel validators, or new policy duplication.

Use specialist agentsCookbook skills for the actual failure class. This skill owns the **campaign feedback loop**, not every defect oracle.

## SAME-BRANCH RULE

Keep reproduced in-scope defects on the same campaign branch/PR when they belong to the same repository and campaign surface.

Do **not** force same-branch locality when:
- the true semantic owner is another repository;
- the new defect is materially outside the declared campaign surface;
- repository policy requires a separate security/release branch;
- continuing would destroy evidence identity or make independent qualification impossible.

For an upstream-owned defect, repair upstream first, then re-establish the downstream campaign head and resume. Never hide an upstream defect with a downstream workaround just to preserve one PR.

## BATCHING

Prefer several meaningful reproduced defects per campaign before expensive broad qualification when safe.

Do not use a defect quota. A campaign with one defect can be valid if subsequent broad attacks are genuinely clean. A campaign with ten defects is not complete if the newest repaired head has not been attacked.

Focused checks belong inside the loop. Repository-wide qualification belongs after the attack surface stops yielding meaningful in-scope defects, unless a broad check is needed earlier to unblock discovery.

## STOP CONDITION

Do not stop because:
- the PR has grown;
- one regression passes;
- CI is green;
- the original reported issue is fixed;
- no defect appeared in one narrow follow-up probe.

Hand off to `dogfood-saturation-loop` for final saturation/qualification semantics. As a strong default, require repeated broad post-repair passes with no new qualifying in-scope defect before considering the campaign stable.

If a broad pass finds another defect, the clean-pass count resets because the candidate changed.

## PREFER

```text
establish fresh base + campaign branch
-> attack current head broadly
-> reproduce qualifying defect
-> repair at semantic owner
-> add focused regression
-> focused validation
-> attack repaired head again
-> reproduce next defect
-> repair on same branch
-> add regression
-> attack repair interactions
-> broaden across mutation / composition / identity / completeness / surfaces
-> repeat until broad passes stop yielding qualifying defects
-> hand current exact head to saturation/final qualification
```

Avoid:

```text
find one defect
-> make tiny PR
-> wait for CI
-> merge
-> start over
```

when the same campaign surface can still be attacked meaningfully.

## OUTPUT

Return `# Same-PR Adversarial Repair Loop` with:
- authoritative base;
- campaign PR/branch;
- current exact head;
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
- `ATTACK_AGAIN` — repaired head exists and further in-scope adversarial work remains;
- `READY_FOR_SATURATION` — repeated broad attacks against the latest head yielded no new qualifying in-scope defect and it can move to final saturation/qualification;
- `BLOCKED_INCOMPLETE` — required authority, reproduction, identity, upstream repair, or attack evidence is unavailable.
