---
name: source-transport-contamination-review
description: Finds repair, evidence, or temporary artifacts that become source, package, or qualification inputs through incidental staging.
license: MIT
---

# Source Transport Contamination Review

Standalone, read-only review of the boundary between a repository's declared source and artifacts carried by repair, inspection or transport. Review the membership contract; do not stage files into the live subject or clean up user files to prove a point.

## INVARIANT

> **Carrying a repair, evidence or temporary artifact must not silently make it authored source, a package input, or qualification authority unless the current membership contract intentionally admits that role.**

The defect is an unintended role change. An in-tree scratch directory can be safe when the canonical owner excludes it. A tracked generated file can be legitimate when the build/consumer contract explicitly includes it. Location alone proves neither case.

## HUNT

Trace `artifact producer -> staging location -> membership owner -> consumer` across:
- hotfix patches, archives, reports, logs, evidence bundles, editor temporaries and OS metadata sidecars;
- repair or recovery instructions that copy artifacts into the checkout they inspect or transform;
- recursive source discovery, packaging, build-context creation or qualification that admits everything under a path;
- source identities or admission decisions changed by incidental staging;
- validators widened to ignore contamination while another consumer still packages or trusts it;
- hidden cleanup in init/build/test/certify paths compensating for another operation's staging.

Treat names and directory placement as leads. Identify the consumer that actually admits the bytes or uses the changed membership.

## PROVE

For a finding, establish:

1. **Governing membership.** Identify the current source/package/qualification boundary and its owner from repository policy, manifests, build rules and supported consumers. Do not invent a rule that all generated or untracked files are forbidden.
2. **Artifact role.** Show who produces or carries the artifact, why it is transport/diagnostic material, and which intended source edits the operation is authorized to make.
3. **Reachable transfer.** Trace the real staging path and discovery/admission logic. Follow aliases, extraction directories and secondary consumers that matter to the same operation.
4. **Before/after witness.** Compare membership and relevant output/qualification semantics before and after staging the same incidental artifact, holding intended authored edits constant. A decisive code trace is valid; label it static. If executing a probe, use an authorized disposable fixture/worktree and retain the observation evidence.
5. **Material consequence.** Prove unintended inclusion, source identity drift, changed package contents, incorrect admission, or hidden cleanup that makes the operation's authority depend on incidental artifacts. Mere file presence outside consumed scope is not enough.
6. **Control.** Show what happens when the same repair is applied from an excluded staging boundary, and when a genuinely declared authored/generated input changes. The correction must preserve intentional source changes and required diagnostics.
7. **Owner and repair.** Name the canonical membership or transport owner, smallest correction, and other consumers that must use the same classification.

If the membership rule or staging path cannot be established, record the missing evidence. Do not infer contamination from an unexplained extra file, or safety from a successful build alone.

## DO NOT REPORT

Do not report:
- intentionally tracked generated artifacts or checked-in fixtures required by the current consumer contract;
- declared diagnostic/evidence inputs that qualification intentionally uses;
- in-tree scratch/output directories excluded consistently by the applicable canonical membership policy;
- temporary files in an isolated fixture or build directory that never enter the source/package/qualification boundary;
- an artifact whose only effect is ordinary disk usage, without a membership or authority consequence;
- a legitimate admission rule rejecting an unexpected authored input.

A source policy may intentionally reject all untracked additions. Respect that contract rather than teaching the validator to accept every repair artifact. Conversely, do not impose fail-closed authored-input admission on a project whose documented membership rule deliberately allows auxiliary files.

## PREFER

Keep transport artifacts outside the boundary that interprets them as source, or use an existing explicitly excluded staging area. Apply intended edits inward through the established operation.

Where multiple consumers disagree, repair the existing canonical membership rule and have them consume it. Do not add per-validator ignore lists, hidden cleanup hooks or a new source registry. Keep cleanup owned by the operation that created the artifact; preserve user files and declared evidence.

If contamination already exists, specify exactly which operation-owned files are disposable and which must be retained or migrated. A generic delete-untracked command is not a justified cleanup plan.

## VERIFY THE CORRECTION

Specify a focused witness and near-neighbor controls:
- staging incidental transport material cannot silently change declared source/package/qualification membership;
- applying the repair from the allowed staging boundary changes only the intended authored inputs;
- legitimate authored or generated inputs still affect membership and output as required;
- an actual forbidden input remains rejected where the governing contract requires rejection;
- related extraction/sidecar paths and downstream consumers obey the same boundary.

For an implemented repair, compare actual resulting membership/package contents and qualification inputs. Do not equate a passing validator with every consumer being corrected. Report proposed, static and executed verification separately.

## OVERLAP

- `hidden-authority-cucumber-attack` owns historical or named identity granting unsupported semantic privilege.
- `semantic-noninterference-review` owns conclusions affected by out-of-scope evidence generally; this skill owns the concrete artifact-staging-to-source-membership cause.
- `baseline-self-authorization-review` owns a candidate weakening its governing oracle; accidental membership contamination does not require an oracle edit.
- `path-scope-confinement-review` owns paths escaping an authority root; contamination may occur entirely inside the correct root.
- `single-source-of-truth-review` owns independently accepted competing membership authorities when that is the primary cause.

Name the earliest proven causal owner and attach secondary effects to one finding.

## OUTPUT

Return `# Source Transport Contamination Review` with:
- declared source/package/qualification scope, membership owner and unknown boundaries;
- artifact producer/role, staging path and actual consumers;
- before/after membership witness and intentional-input control;
- proved consequence, minimal correction and cleanup ownership;
- verification performed and checks still proposed.

End with exactly one:
- `FINDING` — a reachable staging path demonstrably admits or acts on incidental artifacts contrary to the declared membership contract;
- `CLEAN` — the declared staging, admission and consumer paths were traced with no material unresolved membership question;
- `LEAVE ALONE` — the suspected artifact is intentionally admitted or demonstrably excluded from the relevant boundary;
- `INSUFFICIENT EVIDENCE` — no violation is established and missing membership, staging or consumer evidence prevents a bounded conclusion.
