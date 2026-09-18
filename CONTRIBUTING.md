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

## Adding a skill

1. Add `skills/<skill-name>/SKILL.md`.
2. Add the skill to `skills/README.md` in the narrowest fitting category.
3. Add the skill name to `AC_SKILL_NAMES` in `scripts/lib-opencode.sh` so supported hosts can install it.
4. Document overlap boundaries when another skill could plausibly report the same code.
5. Add or update evaluation evidence when the change affects behavioral discrimination.
6. Do not add a new agent wrapper or mandatory flow step unless the role itself is distinct and the extra workflow cost is intentional.

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

## Validation

Run the repository-owned structural checks before opening a PR:

```bash
scripts/check-canonical-sources.sh
node scripts/run-skill-benchmarks.js --validate-corpus
scripts/smoke-opencode-scripts.sh
scripts/smoke-run-artifacts.sh
```

The GitHub workflow validates the prompt/adapters and the complete Agent Economics P1–P11 regression suite on Ubuntu with Python 3.11. Real model-backed OpenCode/Pi qualification remains a host-environment check.

## Pull requests

Keep PRs focused. Explain:

- the problem being solved;
- why an existing skill or contract is insufficient;
- the exact boundary of the change;
- evidence or examples used to validate it;
- any intentional behavior or compatibility change.

If a change is primarily a preference and no repository/user failure mode can be shown, it probably does not belong in the library.
