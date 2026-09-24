---
name: dogfood-saturation-loop
description: Runs same-branch repair campaigns until fresh post-patch dogfood and required final validation both pass.
license: MIT
---

# Dogfood Saturation Loop

Use this skill to keep one bounded repair campaign moving after the first green regression instead of turning every defect into a new PR or CI cycle.

## INVARIANT

> **Do not complete the campaign until the latest candidate has no unresolved in-scope qualifying defect, a complete fresh adversarial dogfood pass finds no new one, and repository-required final validation passes for the candidate or artifact being shipped.**

A green regression closes one reproduction. It does not close the campaign.

Any in-scope repair makes earlier post-repair dogfood stale for the repaired candidate.

## HUNT

Hunt for premature closure when:
- repaired behavior is not dogfooded again before completion;
- a "fresh" pass only replays already-known regressions;
- the required probe set is chosen or reduced after results are known;
- timeout, truncation, skipped required probes, or unknown state becomes `NO_QUALIFYING_DEFECT`;
- campaign scope is narrowed after a hard defect appears;
- evidence comes from different bytes, representation, or materially different execution context without repository-backed equivalence;
- an unresolved in-scope defect coexists with a saturation claim;
- required final validation is missing, self-selected, FAIL, or INCOMPLETE;
- broad CI runs after each small repair even though the same surface still has unexercised interactions.

## PROVE

Before reporting premature closure, establish:

- **Frozen scope** — the semantic surface and inclusion/exclusion boundary fixed before substantive discovery.
- **Qualification authority** — repository-owned policy, commands, or checks that define required final validation. Establish this before interpreting candidate success. If it cannot be determined, final status is `BLOCKED_INCOMPLETE`.
- **Current evidence identity** — exact exercised bytes plus representation and only the execution-context dimensions that materially affect interpretation.
- **Latest repair** — the last in-scope change affecting that identity.
- **Probe contract** — adversarial probes derived from the changed semantics and declared before the fresh pass runs.
- **Probe completeness** — all required probes completed without unresolved timeout, truncation, skipped work, or unknown state.
- **Freshness** — the pass challenges patched semantics or relevant adjacent/interacting cases rather than only replaying the original defect.
- **Defect disposition** — every newly exposed in-scope qualifying defect returns to the same branch and defect queue.
- **Final validation** — the repository-required qualification set passes against the current shipping candidate/artifact.

The probe contract may grow when new evidence suggests another relevant attack. Do not remove a required probe after observing its result merely to obtain a clean pass.

`NO_QUALIFYING_DEFECT` is admissible only from a complete fresh pass.

## EVIDENCE BINDING

Use the smallest identity strong enough to prove what was exercised.

- A commit or branch name is insufficient when staged, modified, untracked, generated, overlaid, or projected content changes behavior.
- A deterministic working-tree/content digest is valid; do not require checkpoint commits merely to create identity.
- When source becomes a ZIP, wheel, image, generated bundle, or installed artifact, bind source identity to artifact identity through repository-backed provenance.
- Reuse evidence across candidate, representation, or execution-context changes only when repository-backed dependency/provenance/contract evidence proves noninterference or equivalence. Otherwise rerun the affected proof.
- An agent's unsupported assertion that a change "cannot matter" is not equivalence evidence.

## DO NOT REPORT

Do not report merely because:
- only one real defect was found and a complete fresh post-repair pass found nothing else;
- several independent defects are repaired in one PR;
- focused validation is used between repair batches;
- broad validation is deferred until the surface is saturated;
- an early broad check is genuinely needed to unblock further dogfood;
- a fresh pass exposes an unrelated defect outside the frozen scope and that defect is preserved separately;
- repairs remain uncommitted while exact exercised bytes are deterministically identified;
- source dogfood is reused for a shipping artifact when repository-backed provenance proves the relevant semantics unchanged.

Do not require a fixed defect count, fixed elapsed time, or universal environment fingerprint.

## PREFER

Run one deep same-branch campaign:

```text
establish starting authority
-> freeze one semantic surface
-> establish repository-required final qualification
-> dogfood current behavior
-> queue multiple reproducible in-scope defects when possible
-> batch repairs at owning semantic boundaries
-> identify exact current candidate
-> run focused validation
-> declare post-repair adversarial probe contract
-> run complete fresh dogfood pass
-> if a new in-scope defect appears: repair and repeat
-> when complete fresh pass yields NO_QUALIFYING_DEFECT: surface saturated
-> build/bind shipping representation if needed
-> run repository-required final validation
-> SATURATED
```

If final validation exposes an in-scope defect, revoke saturation and return through repair, focused validation, a new probe contract, and fresh dogfood before final validation runs again.

If an out-of-scope failure makes required final validation FAIL or INCOMPLETE, preserve the scope boundary but end `BLOCKED_INCOMPLETE`; surface saturation alone does not authorize shipping.

Prefer collecting several independent reproductions before expensive validation when the first defect does not block further discovery. Spend the campaign budget on second-order defects and repair interactions, not repeated proof of the same closed case.

Preserve observed `PASS`, `FAIL`, `INCOMPLETE`, and `NO_QUALIFYING_DEFECT` exactly.

## OUTPUT

Return `# Dogfood Saturation Loop` with:
- starting authority and frozen scope;
- repository-required final qualification authority;
- current evidence identity;
- defect queue and repair batches;
- focused validation;
- declared fresh-pass probe contract and completeness;
- new in-scope/out-of-scope defects;
- source-to-artifact provenance when relevant;
- final validation;
- unresolved evidence.

End with exactly one:
- `SATURATED` — complete fresh dogfood and all repository-required final validation pass for the current shipping candidate/artifact;
- `CONTINUE_DOGFOOD` — in-scope repair or fresh dogfood work remains and can continue;
- `BLOCKED_INCOMPLETE` — required evidence, probe completion, qualification authority, identity, or final validation is unavailable, failing, or incomplete.
