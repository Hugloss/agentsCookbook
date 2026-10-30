---
name: hidden-authority-cucumber-attack
description: Finds name-based privilege, historical exceptions, or compatibility residue acting as authority without a current semantic contract.
license: MIT
---

# Hidden Authority / Cucumber Attack

Standalone, read-only review of identity-based authority. Identify corrections and verification; do not execute repairs or delete tests unless separately authorized.

## INVARIANT

> **Behavior follows a current capability, requirement or policy. A historical name, alias or exception must not independently grant authority that its semantic contract does not justify.**

A **cucumber** is a special case kept alive by recognition of a name, path, version, environment or test expectation rather than a current requirement. Identity can itself be semantic: the issue is unsupported authority, not the existence of a special case.

## HUNT

Trace real production, build, admission, recovery, compatibility and test paths for:
- privileged name sets, allowlists/denylists and exception maps;
- branches on incidental command, target, path, version, environment or fixture names;
- a canonical capability declaration overridden by a downstream identity list;
- aliases, fallback recognition, migration shims or generated contracts preserving an expired exception;
- tests, counts or snapshots that appear to be the only remaining reason for a special rule.

Follow `identity/exception -> decision -> accepted behavior -> current consumer`. Grep matches, old names and comments are leads, not findings.

If a repair bundle, log or generated report becomes source merely because of its staging location, use `source-transport-contamination-review`. That question needs a source-membership comparison, not a rename challenge.

## PROVE

For each proposed finding:

1. Identify the exact identity-sensitive branch and trace a reachable consumer or demonstrably obsolete test/generated dependency.
2. Establish the current normative requirement, support policy and semantic owner. Do not let the suspicious implementation define its own necessity.
3. Show the privilege, bypass, fallback or accepted meaning that changes because of the identifier.
4. Apply an equivalent-identity control: preserve relevant capability, scope and policy while changing the incidental name. Explain why behavior changes incorrectly. Do not rename an identifier that the public/security contract intentionally treats as semantic.
5. Check current consumers, compatibility windows, migrations and external interfaces. When claiming none remain, state the completed search boundary and why external obligations are resolved. No local caller is not proof of no supported consumer.
6. Show the material consequence and every directly related alias, generated form or fallback that could restore the same authority.
7. Name the rightful owner and smallest correction. Separate a missing contract requiring clarification from a proved obsolete exception.

An independently established current rule can prove a conflicting exception even when some unrelated paths are unavailable. Preserve those limits; do not force all findings into an absence-of-owner proof.

## DO NOT REPORT

Preserve:
- identifiers explicitly promised by a supported public protocol or compatibility window;
- policy rules intentionally naming a principal, resource, jurisdiction or externally governed identifier;
- migration aliases with current consumers and a supported removal condition;
- filenames or paths that are the actual documented interface;
- tests naming one example while checking a general invariant;
- deliberate distinct semantics for superficially similar identities.

Do not delete compatibility because it is old or delete a test because it alone exposed the requirement. Establish whether the requirement still applies. Missing history, ownership or external-consumer evidence is uncertainty, not permission to remove a contract.

## PREFER

When equivalent identities should behave equally, place the reason at the existing declaration/semantic owner and consume its resolved capability or policy. Delete duplicate downstream identity tables rather than moving or widening them.

When a requirement has demonstrably expired, remove the exception and its obsolete aliases/generated residue together. When a real compatibility or policy requirement remains, make its owner and applicable scope explicit.

Avoid new registries, adapters or compatibility frameworks if an existing owner can express the distinction.

## VERIFY THE CORRECTION

Specify focused controls:
- the formerly privileged identity;
- an equivalent renamed identity with the same semantics;
- a legitimate different identity whose governing policy requires different behavior.

For an implemented repair, inspect related aliases, fallback branches, generated contracts and test expectations so the same authority cannot silently reappear. Run the relevant semantic checks. Report actual execution separately from proposed checks; a read-only review does not prove deletion or successful repair.

## OVERLAP

- `source-transport-contamination-review` owns incidental repair/evidence staging changing source membership or qualification inputs.
- `single-source-of-truth-review` owns two current accepted owners of the same fact.
- `native-tool-authority-review` owns repository recreation of native/external semantics.
- `alternate-path-removal-review` owns an obsolete implementation beside a canonical path without identity-based privilege.
- `test-contract-coupling-review` owns tests coupled to incidental internals; `test-removal-review` owns whether removing protection loses a still-active requirement.
- `baseline-self-authorization-review` owns a candidate weakening its governing oracle.

Report one causal defect once, under its narrowest proved owner.

## OUTPUT

Return `# Hidden Authority / Cucumber Attack` with:
- inspected identity/exception scope and uninspected boundaries;
- governing requirements, semantic owners and current consumers;
- reachable special cases and equivalent-identity controls;
- proved unsupported authority, consequences and smallest corrections;
- legitimate identity-sensitive contracts to retain;
- directly related aliases/generated residue and focused verification.

End with exactly one:
- `FINDING` — an identity-sensitive path demonstrably grants unsupported authority or preserves an established obsolete exception; retain unresolved scope separately;
- `CLEAN` — all materially relevant identity/exception and consumer paths in the declared scope were traced and their authority was justified;
- `LEAVE ALONE` — the suspected exception is positively required by a current supported contract;
- `INSUFFICIENT EVIDENCE` — no violation is established and missing reachability, governing policy or consumer evidence prevents a bounded conclusion.
