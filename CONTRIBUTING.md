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
4. Add or update evaluation evidence when the change affects behavioral discrimination.
5. Do not add a new agent wrapper or mandatory flow step unless the role itself is distinct and the extra workflow cost is intentional.

## Agent prompts

`agents/` contains thin wrappers and coordinator prompts. Keep reusable methodology in `skills/` rather than copying it into an agent file.

Agent changes should be explicit about:

- role and authority;
- allowed tools/permissions;
- which skill owns the methodology;
- expected output contract;
- whether the agent is standalone or part of an optional flow.

The eight-review Ping-Pong/Ping-Ping gate must not grow accidentally when a standalone skill is added.

## Runtime boundary

OpenCode, Pi, or another host owns execution, tools, sandboxing, model/session lifecycle, delegation mechanics, and persistence.

Runtime-specific code belongs only where it bridges the prompt library into a supported host. Do not add a second agent execution engine, sandbox, repository database, scheduler, or autonomous framework.

The optional `scripts/agent_economics/` package may execute **explicitly named argv-array verification commands** from its versioned manifest. That narrow capability exists to compensate for missing host tools; it must remain bounded, non-autonomous, source-edit-free, and honest about host isolation. General shell execution, dependency installation, source repair, and replacement CI/certification authority remain out of scope.

## Python runtime

Repository-owned Python commands run through uv. Python 3.11 is pinned in `.python-version`.

Use:

```bash
uv run --no-project python -m <module>
```

Do not add repository entrypoints, CI steps, or documentation that call `python` or `python3` directly. The current Python utilities are stdlib-only, so do not add a `pyproject.toml` or dependency wrapper merely to launch them.

## Benchmark readiness

Benchmark execution has no implicit agent population. `BENCHMARK_AGENT` must explicitly select one or more native agents in `.env` before Make preflight, execution, reporting, or specialized scoring. Direct `preflight` and `run` CLI calls likewise require `--agent`. `benchmark-check` checks each distinct agent/subject pair in the suite once, including bare conditions, without expanding tasks or seeds; direct `check --agent` can narrow that diagnostic. Never restore an all-agents execution default for preflight or execution; adding a new suite agent must not silently expose another model/provider to a trial.

`make benchmark-check` is a runtime-connectivity check, not trial admission. It may resolve/fingerprint native hosts and subjects, validate the explicit Hashmarks checkout, and check each unique MCP exposure once in a disposable workspace. It must not load task authority, materialize repositories, apply mutations, run oracles, inspect receipts, derive trial identities, invoke a model, or retry automatically.

Use `make benchmark-check-all` when exhaustive frozen-definition preflight is explicitly wanted. `make benchmark` must not invoke either check implicitly.

## Validation

Run the repository-owned structural checks before opening a PR:

```bash
scripts/check-canonical-sources.sh
node scripts/run-skill-benchmarks.js --validate-corpus
scripts/smoke-opencode-scripts.sh
scripts/smoke-run-artifacts.sh
```

The GitHub workflow validates the prompt/adapters and the complete Agent Economics deterministic, adversarial, dogfood-corpus, and bounded stress qualification suite on Ubuntu with uv-managed Python 3.11. The Agent Economics job has a 20-minute outer safety window; individual subprocesses keep their own smaller hard bounds. Real model-backed OpenCode/Pi qualification and empirical baseline-vs-bridge dogfood remain host-environment checks.

## Pull requests

Keep PRs focused. Explain:

- the problem being solved;
- why an existing skill or contract is insufficient;
- the exact boundary of the change;
- evidence or examples used to validate it;
- any intentional behavior or compatibility change.

If a change is primarily a preference and no repository/user failure mode can be shown, it probably does not belong in the library.
