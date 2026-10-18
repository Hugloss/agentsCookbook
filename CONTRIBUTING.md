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
- use positive/control benchmark cases to protect behavioral discrimination, adding more cases only for real ambiguity rather than a fixed quota;
- compress repeated rules. Prompt length is not itself a defect, but repeated methodology that does not sharpen discrimination is runtime and maintenance cost.


## Adding a skill

1. Add `skills/<skill-name>/SKILL.md`. Canonical skill discovery is derived from `skills/*/SKILL.md`; do not maintain a second manual skill registry.
2. Add the skill to `skills/README.md` in the narrowest fitting category.
3. Document overlap boundaries when another skill could plausibly report the same code.
4. Add or update evaluation evidence in [EvalShot](https://github.com/Hugloss/EvalShot/tree/main/evals) when the change affects behavioral discrimination. Link the associated evaluation change or evidence from the skill PR.
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

## Evaluation ownership

Use [EvalShot's evaluation guide](https://github.com/Hugloss/EvalShot/blob/main/evals/README.md) for positive/control/confusion cases and model-backed skill evaluation. Use its [benchmark guide](https://github.com/Hugloss/EvalShot/blob/main/benchmarks/README.md) for campaign configuration, readiness, and execution. A prompt loading successfully, a corpus validating, and a model passing the behavioral cases establish different claims; report the evidence actually collected.

## Validation

Run the repository-owned structural checks before opening a PR:

```bash
scripts/check-canonical-sources.sh
scripts/smoke-opencode-scripts.sh
scripts/smoke-run-artifacts.sh
```

The GitHub workflow validates canonical prompts, adapters, artifact integrity, reviewer authority, and JavaScript/shell syntax on Ubuntu. These checks run without a benchmark checkout or Python environment. EvalShot owns the benchmark and Agent Economics test suites. Real model-backed OpenCode/Pi qualification remains a host-environment check; follow [local runtime qualification](docs/local-runtime-qualification.md) for the applicable evidence.

## Pull requests

Keep PRs focused. Explain:

- the problem being solved;
- why an existing skill or contract is insufficient;
- the exact boundary of the change;
- evidence or examples used to validate it;
- any intentional behavior or compatibility change.

If a change is primarily a preference and no repository/user failure mode can be shown, it probably does not belong in the library.
