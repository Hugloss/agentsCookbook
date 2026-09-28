---
name: single-source-of-truth-review
description: Finds one semantic truth whose authoritative owner changes by path, caller, phase, or duplicate producer.
license: MIT
---

# Single Source of Truth Review

Standalone, read-only review of split semantic ownership across repository paths.

## INVARIANT

> **For one semantic truth in one declared scope and generation, exactly one authority should establish what is true. Other paths may transport, validate, project, cache, or fail closed on that authority, but the owner must not change because a different caller, entrypoint, Goon, lifecycle phase, helper, or execution route happened to reach the same behavior.**

"Truth" here is semantic, not necessarily a single file or variable. It can be:
- an execution-authority/tool set;
- a resolved configuration or policy result;
- a prerequisite or generated artifact;
- an identity or provenance result;
- a lifecycle/admission/readiness result;
- a canonical manifest, package input, or materialized repository fact;
- any other value whose consumers treat it as authoritative for the same scope.

Many representations are allowed. Many consumers are allowed. **Multiple independent owners for the same truth are not.**

## HUNT

Trace real production, build, certification, test, packaging, recovery, and runtime paths. Hunt for cases where the same semantic truth can be established by different owners depending on context:

- the same tests or runtime behavior receive different execution-authority contracts depending on which outer Goon, target, task, or entrypoint launches them;
- one caller derives authority from a global fixture while another caller declares a local authority for the same behavior;
- Make/bootstrap, normalization, build hooks, packaging, CI, or runtime independently create, default, normalize, inject, or repair the same prerequisite;
- two helpers each mint a canonical identity, manifest, readiness result, resolved config, status, or policy answer that downstream code can accept as truth;
- one path consumes an upstream resolved result while another reconstructs the same truth from raw inputs;
- one lifecycle phase silently becomes a fallback owner when the intended owner is absent;
- a local fix adds one missing tool, field, directory, default, or adapter but leaves a second authority path intact, so the next missing element is merely exposed later;
- tests encode one source of truth while production/certification uses another.

The signal is not repeated syntax. The signal is **authority bifurcation**: two reachable paths can independently decide or establish the same semantic truth.

## PROVE

Before reporting a finding:

1. Name the exact semantic truth and its scope/generation.
2. Trace at least two real reachable paths that consume that truth.
3. For every relevant touch point classify it as **owner**, **transport**, **validation**, **projection**, **cache**, **consumer**, or **compensation/fallback**.
4. Prove that at least two paths can independently establish, select, recreate, or override what downstream behavior accepts as authoritative truth.
5. Show whether owner selection changes with caller, outer workflow, entrypoint, phase, environment, or missing prerequisite.
6. Identify the smallest coherent owner that can establish the truth once for all affected paths.
7. Show a material consequence such as:
   - the same behavior has different prerequisites or semantics by launch path;
   - fixing one missing item only reveals the next because the wrong owner remains;
   - two accepted authorities can drift;
   - a path fails when a compensating owner is absent;
   - tests prove one authority model while certification/runtime executes another;
   - operators or agents must know which path's truth "wins".
8. State which alternate owners, reconstructors, fallbacks, or compensators can disappear after consolidation.

A strong proof often looks like:

```text
same semantic consumer
  <- path A <- authority owner A
  <- path B <- authority owner B
```

or:

```text
one required fact
  <- bootstrap synthesizes it
  <- normalizer synthesizes it
  <- build hook synthesizes it
  <- packaging synthesizes it
```

## DO NOT REPORT

Do not report merely because:
- the same authoritative fact has several read-only projections or serialized forms;
- consumers validate an owner-produced fact at trust boundaries;
- caches bind to and revalidate one authoritative result rather than deciding it again;
- distinct lifecycle phases own genuinely different facts;
- tests create test-only inputs that are not accepted as production authority;
- separate scopes or generations intentionally have separate owners and the boundary is explicit;
- a downstream layer derives display-only or evidence-only data from one transported authority.

Do not collapse legitimate producer/consumer boundaries merely to reduce files.

### Neighboring skills

Use the narrowest specialist when the failure is more specific:

- `semantic-redecision-review` — one authority chain repeatedly interprets the same semantic question, but the downstream redecision is not itself an alternate accepted source of truth.
- `state-authority-review` — competing state representations are the specific truth conflict.
- `entrypoint-authority-review` — multiple launch surfaces independently own defaults/configuration for one operator action.
- `native-tool-authority-review` — repository code duplicates semantics that belong to an external/native tool.
- `resolved-fact-regression-review` — a resolved fact is discarded and a consumer falls back to raw inputs.
- `durable-commit-path-review` — the split truth is specifically multiple durable commit authorities.

Use this skill when the broader architectural defect is **the identity of the semantic owner itself changes across real paths**, or several independent producers are all accepted as the source of truth.

## PREFER

Prefer a single authority path:

```text
raw/source inputs
  -> one semantic owner
  -> resolved authority
  -> transport / validation / projection
  -> all consumers
```

For delegated execution, prefer:

```text
resolve once
-> transport once
-> execute once
-> report once
```

Do not patch the nearest failing consumer if the failure proves that ownership is split. Move ownership to the correct semantic boundary, transport the resolved authority, and delete alternate reconstruction/compensation paths.

When a fact only becomes valid at a later lifecycle phase, keep earlier phases from fabricating placeholders for it.

## OUTPUT

Return `# Single Source of Truth Review` with:
- semantic truth under review;
- declared scope/generation;
- real paths traced;
- authority map showing owner/transport/validation/projection/cache/consumer/compensation roles;
- proven split-source findings;
- context that changes owner selection;
- canonical owner and target authority path;
- alternate owners/fallbacks/compensators that can be removed;
- focused regression needed to prove all affected paths consume the same owner;
- inspected scope and any untraced paths.

End with one:
- `CLEAN` — one authority owner was preserved across the completed inspection scope;
- `LEAVE ALONE` — apparently duplicated paths were traced and own genuinely different truths/scopes;
- `INSUFFICIENT EVIDENCE` — the real paths or authority acceptance could not be traced far enough to prove whether multiple owners exist.
