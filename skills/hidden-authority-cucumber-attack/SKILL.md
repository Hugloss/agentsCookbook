---
name: hidden-authority-cucumber-attack
description: Exposes hidden authority from historical identity, unexplained exceptions, or repair/transport artifacts that silently become source.
license: MIT
---

# Hidden Authority / Cucumber Attack

Standalone, read-only attack on hidden authority preserved by names, historical exceptions, compatibility residue, fallback recognition, tests that outlived the semantic contract they once protected, or repair/transport mechanisms that accidentally mutate the source authority they are supposed to repair.

## INVARIANT

> **Behavior should follow current semantic capability, purpose, requirement, or policy—not historical identity, unexplained special recognition, incidental artifact location, or an exception whose owner and consumer no longer exist. Repair machinery must not change canonical source membership merely by carrying its own artifacts into the subject it repairs.**

A **cucumber** is suspicious authority or behavior that survives because the repository recognizes a particular name, path, filename, target, version, environment, legacy alias, fallback, or test expectation rather than because the current architecture requires that semantic distinction.

Identity can legitimately be semantic. The defect is not “there is a special case.” The defect is **special identity acting as authority without a current semantic owner, consumer, or normative contract**.

A second form of the same cucumber appears when **incidental placement becomes authority**: a patch, evidence bundle, generated report, archive, debug output, editor temporary, or OS metadata sidecar is carried into a repository to repair or inspect it, then source discovery, packaging, architecture, or certification starts treating that transport artifact as authored source. The repair mechanism has changed the subject merely by touching it.

## HUNT

Trace real production, build, certification, release, recovery, compatibility, and test paths. Use grep as discovery only; prove reachability before reporting.

Search for:
- allowlists, denylists, exception maps, and privileged named sets;
- `SPECIAL_*`, `EXPLICIT_*`, `*_OVERRIDE*`, `*_EXCEPTION*`, `*_LEGACY*`, `*_COMPAT*`;
- branches on names, paths, filenames, targets, versions, modes, environment names, plan names, task names, or fixture names;
- parser/registry declarations where behavior semantics are already declared, but downstream code keeps command/name/path/version allowlists or skip sets instead of consuming one explicit semantic property;
- compatibility aliases, deprecated entrypoints, old command names, migration shims, and retained legacy identifiers;
- fallback, recovery, rescue, “try old shape,” or “if known target” paths;
- duplicated authority vocabularies that classify the same subject differently;
- tests or fixtures that give one named object privileged behavior;
- assertions based on magic counts, exact lists, or identities produced only by retained exceptions;
- comments containing “special”, “legacy”, “temporary”, “for certification”, “for CI”, “except”, “compatibility”, “deprecated”, or “workaround”;
- generated/derived contracts that still encode an exception absent from normative architecture;
- exception cleanup code that removes one branch while another alias, fallback, or generated form silently restores it;
- hotfix/recovery instructions that download, copy, or stage patch files, ZIPs, evidence bundles, reports, logs, temporary outputs, editor artifacts, or OS metadata inside the repository they modify;
- source-layout or packaging code where mere directory placement decides whether a repair/transport artifact becomes authored source;
- ignore lists added to validators only so repair-created contamination passes admission;
- hidden cleanup in init, certify, build, test, or release paths that erases repair contamination instead of leaving one explicit cleanup owner.

For each candidate, trace one or both forms:

`identity/exception -> decision -> affected behavior -> current consumer`

`repair/transport artifact -> staging location -> source-membership decision -> affected admission/build/package/certification behavior`.

## CHALLENGE

For every candidate ask:

1. What semantic owner requires this?
2. What current consumer uses it?
3. Would the rule remain valid if the object were renamed while preserving its semantics?
4. Is identity being used as authority, or only as a locator for a semantic contract owned elsewhere?
5. Is this behavior described by current normative architecture, compatibility policy, protocol, or product requirements?
6. If deleted, does real product behavior fail, or only a test/snapshot/count that memorializes the exception?
7. Is another native, tool, runtime, platform, or repository owner already authoritative for the same decision?
8. Could one explicit semantic property owned where the object is declared replace a list of privileged identities?
9. Does the repair, recovery, evidence, or debugging mechanism alter canonical source membership merely because of where it stages its own artifacts?
10. If contamination is possible, is cleanup explicit and owned, or is some unrelated init/certify/build path silently compensating for it?

**No current owner + no current consumer = probable cucumber.**

**Repair transport that mutates canonical source membership by incidental placement = probable cucumber even when the transported bytes are disposable.**

That is a lead, not sufficient proof. Continue until the real path is established.

## PROVE

Before reporting a finding:

1. Identify the exact special identity, alias, fallback, exception, or privileged branch.
2. Trace at least one real reachable path through it, or prove that only test/generated residue still keeps it alive.
3. Name the behavior or authority the special case changes.
4. Identify the claimed current semantic owner and consumer. If none exists, show the completed search boundary that supports that conclusion.
5. Apply a rename or equivalent-identity thought experiment: preserve semantic capability/purpose/requirement while changing the incidental identifier. Explain whether behavior would incorrectly change.
6. Show why the exception is absent from, weaker than, or contradictory to current normative architecture.
7. Check whether another owner already decides the fact and the special case duplicates or overrides it.
8. Identify every alternate alias, fallback, generated contract, and test expectation that could restore the hidden authority after the obvious branch is removed.
9. For repair/transport candidates, compare source membership before and after the repair mechanism stages its own artifact. Prove whether the patch/evidence/archive/sidecar becomes an authored member, changes package inputs, or changes qualification outcome.
10. Check the transport boundary itself: prove whether the same repair can be applied from outside the checkout without changing canonical source membership.

Strong proof often looks like:

~~~text
named object / legacy identity
  -> exception branch
  -> privileged behavior
  -> no current semantic owner or consumer
~~~

or:

~~~text
current semantic owner
  -> resolved capability/policy
  -> hidden identity exception overrides it
~~~

or:

~~~text
obsolete compatibility alias
  -> no supported consumer
  -> tests preserve alias
  -> tests are now the only reason the alias exists
~~~

or:

~~~text
repair / evidence artifact
  -> staged inside repository being repaired
  -> incidental location makes it source
  -> admission / packaging / certification changes
  -> repair mechanism mutated its own subject
~~~

## DO NOT REPORT

Do not report identity-sensitive behavior when identity is itself part of a current semantic contract, for example:
- a protocol or public compatibility surface explicitly promises a legacy identifier during a documented support window;
- a security or policy rule intentionally names a concrete principal, resource, jurisdiction, artifact class, or externally governed identifier;
- a migration alias still has a proven current consumer and an explicit removal condition;
- a filename/path/name is the documented public interface rather than an incidental implementation label;
- a test names one object but only proves a general semantic invariant that all equivalent objects satisfy;
- a repair bundle remains outside the canonical source boundary, is applied inward, and never becomes a source/package/admission member;
- a generated artifact is intentionally declared as authored source by a current generator/consumer contract rather than becoming source solely because a repair copied it into the tree.

Do not delete a compatibility path merely because it is old. Prove the supported consumer is gone or the contract has expired.

Do not report ordinary duplicate ownership under this skill when two current semantic owners independently establish the same truth; use `single-source-of-truth-review`.

Do not report a repository wrapper that recreates external/native semantics merely because it contains compatibility logic; use `native-tool-authority-review` when the central defect is shadowing native authority.

Do not report a canonical path plus a genuinely obsolete second implementation merely because the second path has an old name; use `alternate-path-removal-review` when the central defect is architectural duplication rather than identity-based privilege.

Do not report tests that merely couple to private choreography unless the test is actually the only current consumer preserving the hidden exception; otherwise use `test-contract-coupling-review`.

Do not solve repair-artifact contamination by teaching architecture, packaging, or certification to ignore arbitrary files. Preserve fail-closed source admission. Distinguish disposable transport metadata through the canonical source-membership owner and keep cleanup explicit.

## REPAIR

Do not merely update, rename, widen, or move the special case.

Prefer:

~~~text
special identity
    ↓
semantic capability / purpose / requirement / policy
~~~

Move the decision to the semantic owner, transport the semantic result, and make equivalent identities behave equivalently.

When no current owner or consumer exists:

~~~text
historical exception
    ↓
delete authority entirely
~~~

Delete obsolete compatibility aliases, exception sets, fallback/recovery paths, magic-count assertions, generated residue, and tests whose only purpose is to preserve the removed exception.

If a real compatibility or policy requirement remains, make that contract explicit and give it a removal condition or durable owner instead of relying on folklore comments or identity recognition.

When distinct behavior is legitimate and the object already has a canonical declaration/registry owner, prefer making the reason explicit there:

~~~text
semantic declaration
  -> explicit capability / eligibility / policy property
  -> behavior
~~~

rather than maintaining a second downstream list of privileged command names, paths, versions, or targets.

For repair/transport self-contamination, prefer:

~~~text
repair bundle outside canonical source
    -> apply transformation inward
    -> canonical source membership unchanged except for intended edits
~~~

Keep patches, evidence bundles, ZIPs, reports, logs, downloaded artifacts, and their OS/editor sidecars outside the checkout they modify. If contamination already exists, use one explicit source-transport cleanup owner. Do not add silent cleanup to init/certify/build and do not widen ignore rules merely to make the repair pass.

## REGRESSION

Tests should prove the semantic invariant, not memorialize the old exception.

Bad:

~~~text
"APP certification is the only Plan allowed to override resources."
~~~

Good:

~~~text
"Plan templates do not own execution resource authority."
~~~

Bad:

~~~text
"legacy_target remains in the exception allowlist."
~~~

Good:

~~~text
"Targets with the same declared capability receive the same policy regardless of target name."
~~~

A focused regression should normally include:
- the formerly privileged identity;
- an equivalent renamed identity with the same semantics;
- a non-equivalent control whose semantic requirement legitimately differs.

For repair/transport contamination, also prove:
- applying the repair from outside the repository changes only the intended authored files;
- staging the repair artifact inside canonical source is detected rather than silently accepted;
- recognized disposable transport metadata is handled by the canonical source-membership/cleanup owner, not independently reclassified by every consumer;
- a genuine authored extra remains a hard failure.

## PROVE AFTER REPAIR

After repair:
- search again for aliases and exception vocabulary;
- verify no alternate path, fallback, compatibility shim, or generated contract restores the authority;
- verify generated/derived contracts agree with normative architecture;
- run architecture/structural checks;
- run focused semantic regressions;
- attack the repaired area again from another entrypoint, caller, phase, or equivalent renamed identity;
- re-run source membership/package identity after the repair and prove no repair bundle, evidence file, archive, temporary output, or metadata sidecar became canonical source.

The repair is incomplete when the obvious branch is gone but another representation preserves the same hidden authority.

## OVERLAP

Use the narrowest skill:

- `single-source-of-truth-review` — multiple current paths independently own the same semantic truth.
- `semantic-redecision-review` — one authority chain reinterprets a semantic answer repeatedly without creating a privileged historical identity.
- `native-tool-authority-review` — repository code recreates semantics owned by a native/external tool.
- `alternate-path-removal-review` — an obsolete architecture path remains beside the canonical implementation.
- `test-contract-coupling-review` — tests freeze private choreography or implementation shape.
- `baseline-self-authorization-review` — a candidate changes the governing baseline/policy and then validates itself against the weakened authority.

Use this skill when the central defect is either **historical/named identity has become authority without a current semantic reason** or **incidental repair/transport placement has become source/qualification authority without a semantic reason**.

## OUTPUT

Return `# Hidden Authority / Cucumber Attack` with:
- inspected scope and candidate exception vocabulary;
- real reachable identity/exception paths;
- semantic owner and current consumer per candidate;
- rename/equivalent-identity challenge;
- proven hidden-authority/cucumber findings;
- legitimate identity-sensitive contracts to leave alone;
- authority/aliases/fallbacks/tests/generated residue to delete;
- semantic replacement contract and focused regressions;
- repair/transport self-contamination paths and source-membership before/after evidence;
- post-repair re-attack surface.

End with one:
- `CLEAN` — no identity-only or ownerless exception authority was proven in the completed inspection scope;
- `LEAVE ALONE` — suspicious special cases were traced and each has a current semantic owner, consumer, and normative contract;
- `INSUFFICIENT EVIDENCE` — reachability, current consumers, or normative ownership could not be established far enough to distinguish a cucumber from a legitimate exception.
