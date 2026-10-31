# Contributing

Thanks for helping improve Agents Cookbook.

The repository is a reusable Markdown prompt library. Contributions should make the prompts sharper, easier to reuse, or easier to understand without turning the project into a runtime, sandbox, repository indexer, model server, or orchestration framework.

## Before opening a PR

Prefer the smallest change that solves the problem. A new skill is justified when it owns a distinct review or discovery question that existing skills do not already cover cleanly.

Good contributions usually do one of these:

- sharpen an existing invariant, proof requirement, or false-positive boundary;
- add a genuinely missing failure class or discovery question;
- improve public documentation, examples, portability, or installation clarity;
- fix OpenCode/Pi adapter behavior without duplicating prompt methodology;
- add evaluation evidence that helps distinguish one skill from neighboring skills.

Avoid adding generic “code quality”, “maintainability”, “best practices”, or “architecture review” mega-skills.

## Skill contract

A skill should be standalone and useful when loaded directly by a compatible agent runtime.

Prefer this shape when it fits:

```text
INVARIANT

HUNT
- what to inspect

PROVE
- evidence required before reporting

DO NOT REPORT
- false positives and nearby concerns

PREFER
- smallest useful correction direction

OUTPUT
- evidence-backed result
```

A strong skill should:

- own one narrow review or discovery question;
- give specialist review skills one clear failure class;
- follow real production or test paths instead of reporting grep matches;
- require proof before turning suspicion into a finding;
- state the main false positives;
- allow `CLEAN`, `LEAVE ALONE`, or `INSUFFICIENT EVIDENCE` when appropriate;
- prefer deletion, consolidation, clearer ownership, and shorter control/data paths over new layers;
- avoid fixed finding quotas;
- remain independent of Ping-Pong state, sibling reports, a run store, or one model provider.

Descriptions should target 120 characters or less and must remain within the repository’s 160-character validation limit.

### Hard-earned skill-authoring rules

Before merging a new or materially changed skill, apply `skill-contract-review` and check these boundaries. This is an authoring-time guardrail, not an additional mandatory reviewer in Ping-Pong/Ping-Ping or ordinary repository-review flows:

- make the **clean/no-finding path as evidence-bound as the finding path**; bounded or incomplete inspection cannot justify repository-wide absence;
- distinguish `INSUFFICIENT EVIDENCE`, unknown, skipped, truncated, or partial work from clean/success;
- define the minimum semantic scope needed to own the question; allow evidence-backed expansion when directly affected behavior emerges, but do not shrink scope merely to discard a problem;
- define what qualifies as a finding; investigation leads, smells, rankings, or suspicions are not defects without the skill's required proof;
- when success depends on a baseline, policy, threshold, probe contract, or qualification oracle, establish that authority independently of candidate success and do not let the candidate silently weaken it;
- bind source identity, provenance, environment, freshness, or representation only when those dimensions can materially change interpretation—do not cargo-cult evidence machinery into simple bounded skills;
- keep the real semantic owner visible, including upstream ownership; do not encode local workarounds merely to keep a workflow or branch self-contained;
- check positive/control behavior when reviewer discrimination changes; reuse relevant examples or evaluation cases, adding coverage for concrete ambiguity rather than a fixed quota;
- compress repeated rules. Prompt length is not itself a defect, but repeated methodology that does not sharpen discrimination is runtime and maintenance cost.

### Precision, splitting, and quality claims

Treat "platinum" as a quality goal, not a grade produced by loading a skill or passing structural CI. Evaluate the definition, the agent's decisions, and the resulting implementation separately.

- Check selection from the name/description as well as direct invocation: one intended request and a plausible neighboring request should lead to the appropriate owner.
- Require applicable facts before decisions. Verify repository paths and version-sensitive commands/APIs from actual source or primary documentation. Label pseudocode, assumed inputs and application-specific adapters; never substitute plausible names for missing contracts.
- Make output states consistent. A proved defect needs a finding outcome; unresolved neighboring scope must stay visible without erasing that defect or becoming a clean claim.
- Keep safe controls concrete. Existing valid idempotency, supported compatibility, intentional fresh reads and established validation boundaries must not become findings solely because they resemble a hunt pattern.
- Split when each part has an independent trigger, proof obligation and correction owner. Keep tightly coupled end-to-end guarantees together. Use optional references for examples or variants of the same job, and update catalog/router references when a real split occurs.
- For material detection/routing changes, reuse or inspect positive and safe-control cases, plus missing-evidence or competing-skill cases where relevant. A representative fresh-agent exercise is useful prompt-usability evidence; it is not a measured accuracy improvement or production qualification.
- Improve obvious source-proved repeated work directly. Timing infrastructure is not a prerequisite to a safe structural optimization; numerical speedup claims still require suitable observations.

Do not add another mandatory flow reviewer, model run or paired repository PR merely to apply these authoring rules.


## Adding a skill

1. Add `skills/<skill-name>/SKILL.md`. Canonical skill discovery is derived from `skills/*/SKILL.md`; do not maintain a second manual skill registry.
2. Add the skill to `skills/README.md` in the narrowest fitting category.
3. Document overlap boundaries when another skill could plausibly report the same code.
4. Describe validation appropriate to the change and its claims using [evaluation ownership and evidence](#evaluation-ownership-and-evidence). Link relevant existing evidence or an EvalShot change when one is needed; adding a skill does not automatically require a second PR.
5. Do not add a new agent wrapper or mandatory flow step unless the role itself is distinct and the extra workflow cost is intentional.

## Agent prompts

`agents/` contains thin wrappers and coordinator prompts. Keep reusable methodology in `skills/` rather than copying it into an agent file.

Agent changes should be explicit about:

- role and authority;
- allowed tools/permissions;
- which skill owns the methodology;
- expected output contract;
- whether the agent is standalone or part of an optional flow.

The nine-review Ping-Pong/Ping-Ping gate must not grow accidentally when a standalone skill is added.

## Runtime boundary

OpenCode, Pi, or another host owns execution, tools, sandboxing, model/session lifecycle, delegation mechanics, and persistence.

Runtime-specific code belongs only where it bridges the prompt library into a supported host. Do not add a second agent execution engine, sandbox, repository database, scheduler, or autonomous framework.

Benchmark runners, evaluation corpora, and the complete Agent Economics support toolkit belong to [EvalShot](https://github.com/Hugloss/EvalShot). Changes to that implementation, its Python runtime, or its benchmark configuration go there. Keep canonical skills and prompt-facing adapters here; EvalShot consumes an explicitly selected cookbook checkout when evaluating them.

### Model context ownership — do not drift

**The model/provider and agent host own the context window, output limits, and
compaction configuration.** A reusable cookbook skill, agent, flow, protocol,
or preflight must not require a particular model-context size, reserve a fixed
token count, change model settings, or reject a valid agent for using a
different context window.

Keep context guidance qualitative: select the evidence needed for the task,
avoid indiscriminate bulk-loading, preserve critical facts, and let the host
apply supported compaction. If context usage is not observable, do not invent
a capacity. Model-specific tuning belongs in the operator's OpenCode/Pi/provider
configuration; measured context outcomes belong in
[EvalShot](https://github.com/Hugloss/EvalShot/blob/main/docs/model-context-observation.md).

This rule is independent of **output-schema/receipt size bounds**, which may
still be necessary for interoperable artifacts. Do not turn such artifact
contracts into a hidden model token-window requirement.

Before merging an agent/skill/flow/preflight change, confirm that it does not
introduce another model-context owner. See the canonical
[context discipline protocol](protocols/context-discipline.md).

## Evaluation ownership and evidence

EvalShot owns reusable evaluation corpora, runners, and benchmark evidence tooling.
Creating, updating, installing, or using a cookbook skill does not by itself
require an EvalShot checkout, change, paired PR, or model-backed run.

Choose validation for the changed behavior and the claims being made. Reuse
relevant existing evidence rather than creating a new evaluation for every edit.

| Change or claim | Appropriate evidence |
| --- | --- |
| Documentation, examples, or implementation guidance | Source/API review and repository checks; apply materially changed instructions to a representative task where useful. New or materially changed skills still receive `skill-contract-review`. |
| Reviewer detection, routing, or false-positive behavior | Inspect relevant positive/control examples and neighboring cases. Add or update the EvalShot corpus when reusable regression coverage is needed; use model-backed runs before claiming evaluated behavioral quality or improvement. |
| Runtime compatibility, successful implementation, reliability, or performance | Exercise the affected runtime, generated implementation, or service path. Support measured claims with the corresponding observations and comparison evidence. |

Keep durable evaluation corpora and executable benchmark infrastructure in
[EvalShot](https://github.com/Hugloss/EvalShot/tree/main/evals). Change that
repository when the work concerns those assets, and link coordinated PRs when
both repositories actually change. A bounded source review or representative
skill application may be documented directly in the cookbook PR.

Report what the evidence establishes: prompt loading, source review, example
application, corpus validation, model behavior, and executed implementation are
different results. Classification cases do not prove that a construction skill
produces working code; static review does not establish live-service parity.
Keep unavailable or unexecuted checks explicit. Existing runtime promotion and
behavioral qualification requirements still apply when making those claims.

Use [EvalShot's evaluation guide](https://github.com/Hugloss/EvalShot/blob/main/evals/README.md)
for reusable positive/control/confusion cases and model-backed skill evaluation,
and its [benchmark guide](https://github.com/Hugloss/EvalShot/blob/main/benchmarks/README.md)
for campaign configuration, readiness, and execution.

## Validation

Run the repository-owned structural checks before opening a PR:

```bash
scripts/check-canonical-sources.sh
scripts/smoke-opencode-scripts.sh
scripts/smoke-run-artifacts.sh
```

The GitHub workflow validates canonical prompts, adapters, artifact integrity, reviewer authority, and JavaScript/shell syntax on Ubuntu. These checks run without a benchmark checkout or Python environment. EvalShot owns the benchmark and Agent Economics test suites. Real model-backed OpenCode/Pi qualification remains a host-environment check; follow [local runtime qualification](docs/local-runtime-qualification.md) for the applicable evidence.

The distribution step additionally uses the runner's Python 3 standard library
to check and build [Agensi pack candidates](docs/agensi-distribution.md); it needs
no Python environment setup or third-party packages. Pack membership is derived
from the existing catalog sections and checked against `skills/*/SKILL.md`.
When adding a catalog section, assign that section to a pack in
`distribution/agensi-packs.json`. Do not maintain another list of skill names.
Packaging checks prove archive completeness and source identity, not marketplace
approval or host/model behavior.

## Pull requests

Keep PRs focused. Explain:

- the problem being solved;
- why an existing skill or contract is insufficient;
- the exact boundary of the change;
- evidence or examples used to validate it;
- any intentional behavior or compatibility change.

If a change is primarily a preference and no repository/user failure mode can be shown, it probably does not belong in the library.
