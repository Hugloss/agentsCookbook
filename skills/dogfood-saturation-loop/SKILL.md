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
- the minimum campaign scope omits the repaired behavior's owning semantic boundary or directly affected interfaces;
- later evidence proves another behavior is directly affected but campaign scope refuses to expand;
- campaign scope shrinks after a hard defect appears;
- suspicion or an investigation lead is treated as a qualifying defect without reproduced evidence;
- a reproduced in-scope defect is dismissed as "non-qualifying" without defect-proof evidence;
- evidence comes from different bytes, base authority, representation, or materially different execution context without repository-backed equivalence;
- a downstream workaround is used for a defect whose owning semantic boundary is upstream merely to keep work on one branch;
- an unresolved in-scope qualifying defect coexists with a saturation claim;
- required final validation is missing, self-selected, self-weakened by the candidate, FAIL, or INCOMPLETE;
- broad CI runs after each small repair even though the same surface still has unexercised interactions.

## PROVE

Before reporting premature closure, establish:

- **Authoritative base** — the repository/base identity and governing sources from which campaign scope and qualification authority are derived.
- **Minimum campaign scope** — before substantive discovery, freeze the repaired behavior's owning semantic boundary plus known directly affected public/runtime interfaces. This is the minimum scope, not a maximum.
- **Monotonic scope expansion** — later evidence may add directly affected behaviors, interfaces, or repair interactions. Scope may expand when evidence requires it; it must not shrink merely to discard an observed defect.
- **Qualification authority** — repository-owned policy, commands, or checks that define required final validation, established independently of candidate success. An authority that explicitly declares no additional final validation is a valid empty set; unknown authority is `BLOCKED_INCOMPLETE`.
- **Current evidence identity** — exact exercised bytes plus representation and only the execution-context dimensions that materially affect interpretation.
- **Latest repair** — the last in-scope change affecting that identity.
- **Probe contract** — adversarial probes derived from the changed semantics and declared before the fresh pass runs.
- **Probe completeness** — all required probes completed without unresolved timeout, truncation, skipped work, or unknown state.
- **Freshness** — the pass challenges patched semantics or relevant adjacent/interacting cases rather than only replaying the original defect.
- **Qualifying defect proof** — a qualifying defect is a reproduced, evidence-backed violation of the campaign surface's behavioral/authority contract, established by `codebase-finding-derivation` or the appropriate narrow specialist. A lead or suspicion alone is not qualifying evidence.
- **Defect ownership/disposition** — every newly exposed in-scope qualifying defect returns to the same campaign queue and is repaired at its actual owning semantic/repository boundary.
- **Final validation** — the independently established repository-required qualification set passes against the current shipping candidate/artifact.

The probe contract may grow when new evidence suggests another relevant attack. Any newly required probe must complete against the same candidate before that pass can be called complete. Already-completed probes do not need rerunning solely because another probe was added. If the new evidence causes a repair or invalidates a prior assumption, establish the new candidate identity and start a new fresh pass.

`NO_QUALIFYING_DEFECT` is admissible only from a complete fresh pass.

If the authoritative base or another governing source changes materially during the campaign, re-establish affected scope, qualification authority, and probe assumptions. Evidence whose interpretation depended on the old authority is stale.

If the candidate changes its own qualification workflow, threshold, baseline, allowlist, or policy, that mutation must be independently admitted against the previous governing authority before the changed authority can judge the candidate. The candidate cannot authorize itself by weakening its oracle.

## EVIDENCE BINDING

Use the smallest identity strong enough to prove what was exercised.

- A commit or branch name is insufficient when staged, modified, untracked, generated, overlaid, or projected content changes behavior.
- A deterministic working-tree/content digest is valid; do not require checkpoint commits merely to create identity.
- When source becomes a ZIP, wheel, image, generated bundle, or installed artifact, bind source identity to artifact identity through repository-backed provenance.
- Reuse evidence across candidate, base, representation, or execution-context changes only when repository-backed dependency/provenance/contract evidence proves noninterference or equivalence. Otherwise rerun the affected proof.
- An agent's unsupported assertion that a change "cannot matter" is not equivalence evidence.

## DO NOT REPORT

Do not report merely because:
- only one qualifying defect was found and a complete fresh post-repair pass found nothing else;
- an investigation lead or suspicious behavior was not promoted to a defect because proof is still insufficient;
- several independent defects are repaired in one campaign;
- focused validation is used between repair batches;
- broad validation is deferred until the surface is saturated;
- an early broad check is genuinely needed to unblock further dogfood;
- scope expands because new evidence proves another behavior/interface is directly affected;
- a fresh pass exposes an unrelated defect outside the current campaign scope and that defect is preserved separately;
- repairs remain uncommitted while exact exercised bytes are deterministically identified;
- an upstream-owned defect leaves the downstream candidate blocked while the upstream owner is repaired/qualified first;
- source dogfood is reused for a shipping artifact when repository-backed provenance proves the relevant semantics unchanged;
- repository authority explicitly establishes that there is no additional final validation beyond the completed evidence.

Do not require a fixed defect count, fixed elapsed time, universal environment fingerprint, or one-branch repair when the semantic owner is another repository.

## PREFER

Run one deep campaign:

```text
establish authoritative base
-> freeze minimum semantic scope
-> establish independent repository qualification authority
-> dogfood current behavior
-> prove qualifying defects
-> expand scope only when evidence proves a directly affected boundary
-> queue multiple reproducible in-scope defects when possible
-> batch repairs at actual owning semantic/repository boundaries
-> identify exact current candidate
-> run focused validation
-> declare post-repair adversarial probe contract
-> run complete fresh dogfood pass
-> if a new qualifying in-scope defect appears: repair and repeat
-> when complete fresh pass yields NO_QUALIFYING_DEFECT: surface saturated
-> build/bind shipping representation if needed
-> run independently established final validation
-> SATURATED
```

If an in-scope defect belongs upstream, repair or qualify the upstream owner first, then re-establish affected downstream candidate evidence. Do not hide the defect with a downstream workaround merely to preserve branch locality.

If final validation exposes an in-scope defect, revoke saturation and return through proof, repair, focused validation, a new probe contract, and fresh dogfood before final validation runs again.

If an out-of-scope failure makes required final validation FAIL or INCOMPLETE, preserve the scope boundary but end `BLOCKED_INCOMPLETE`; surface saturation alone does not authorize shipping.

If the base or governing authority changes materially, re-establish the affected campaign inputs before continuing.

Prefer collecting several independently proved defects before expensive validation when the first defect does not block further discovery. Spend campaign budget on second-order defects and repair interactions, not repeated proof of the same closed case.

Preserve observed `PASS`, `FAIL`, `INCOMPLETE`, and `NO_QUALIFYING_DEFECT` exactly.

## OUTPUT

Return `# Dogfood Saturation Loop` with:
- authoritative base;
- minimum scope plus evidence-backed expansions;
- repository-required final qualification authority;
- current evidence identity;
- qualifying defect queue, proof owner, and repair owner;
- focused validation;
- declared fresh-pass probe contract and completeness;
- new in-scope/out-of-scope defects;
- upstream/downstream ownership transitions when relevant;
- base/authority changes and evidence invalidated, if any;
- source-to-artifact provenance when relevant;
- final validation;
- unresolved evidence.

End with exactly one:
- `SATURATED` — complete fresh dogfood and all repository-required final validation pass for the current shipping candidate/artifact, including an authoritative empty final-validation set when applicable;
- `CONTINUE_DOGFOOD` — in-scope proof, repair, scope expansion, or fresh dogfood work remains and can continue;
- `BLOCKED_INCOMPLETE` — required evidence, probe completion, qualification authority, identity, upstream repair/qualification, or final validation is unavailable, failing, or incomplete.
