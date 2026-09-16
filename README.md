# Agents Cookbook

**Small, reusable prompts for agents that need to understand, review, and improve real codebases.**

Agents Cookbook is a Markdown prompt library for coding agents and repository reviewers. The prompts are deliberately narrow, evidence-driven, and composable: use one skill directly, wrap it in an agent role, or combine several into a larger review flow.

The library works with **OpenCode, Pi, or another compatible agent runtime**. The cookbook owns the prompts. Your runtime owns execution, tools, sandboxing, models, sessions, and persistence.

> The goal is not to make the agent sound more confident. The goal is to make it inspect the repository, find the right thing to investigate, prove what is actually wrong, and prefer the smallest correction that removes the problem.

## 30-second setup

Clone the repository and link the canonical prompts into the supported local runtimes:

```bash
git clone https://github.com/Hugloss/agentsCookbook.git
cd agentsCookbook
scripts/link-opencode-local.sh
```

That installs the same canonical agent and skill sources for OpenCode and Pi. You can also ignore the adapters completely and copy or load any `SKILL.md` directly in another agent system.

Check the local installation with:

```bash
scripts/check-canonical-sources.sh
scripts/preflight-opencode-ping-pong.sh
scripts/preflight-pi-ping-pong.sh
```

## Start here

You do **not** need to run a giant review flow. Pick the smallest prompt that answers the question you actually have.

| You want the agent to... | Start with |
| --- | --- |
| figure out what is worth investigating in a repo | [`repository-improvement-scout`](skills/repository-improvement-scout/SKILL.md) |
| decide whether suspicious code is a real finding | [`codebase-finding-derivation`](skills/codebase-finding-derivation/SKILL.md) |
| check whether a repo-specific claim is actually true | [`fact-grounding-auditor`](skills/fact-grounding-auditor/SKILL.md) |
| find stale async work that can overwrite newer state | [`stale-work-race-review`](skills/stale-work-race-review/SKILL.md) |
| find duplicated semantic decisions | [`semantic-redecision-review`](skills/semantic-redecision-review/SKILL.md) |
| find obsolete alternate implementation paths | [`alternate-path-removal-review`](skills/alternate-path-removal-review/SKILL.md) |
| find slow work caused by repeated repository/runtime effort | [`code-performance-optimization-audit`](skills/code-performance-optimization-audit/SKILL.md) |
| review whether tests exercise real behavior | [`coverage-design-review`](skills/coverage-design-review/SKILL.md) |
| plan a change through eight independent review passes | [`ping-pong-plan`](agents/ping-pong-plan.md) |
| implement, validate, review, fix, and polish a change | [`ping-ping-build`](agents/ping-ping-build.md) |

The complete catalog of **35 skills** and their overlap boundaries is in [`skills/README.md`](skills/README.md).

## Why this library exists

Coding agents are fast, but the failure modes are familiar.

### The agent does not know what to look for

A repository can contain hundreds of plausible smells. File size, TODOs, duplicate-looking code, old names, and broad searches produce noise very quickly.

`repository-improvement-scout` exists to turn repository signals into **bounded investigation leads**: what looked suspicious, why it may matter, where to inspect next, what would prove or dismiss it, and which specialist should take over.

### The agent turns suspicion into certainty

Finding a strange branch or repeated check is not the same as proving a defect.

`codebase-finding-derivation` forces the agent to establish a reachable path, the expected invariant or contract, the exact violation, the material consequence, the evidence, and the disconfirmation check before calling something a finding.

If the evidence is incomplete, the correct result is **insufficient evidence**, not a confident guess.

### Generic code review produces generic advice

“Improve maintainability” and “reduce complexity” are too vague to be useful.

The specialist skills each own a narrow question: stale work, retry idempotency, semantic redecision, state authority, hidden effects, duplicate observation, test contamination, dependency surface, and so on. Each skill says what to hunt, what must be proved, what not to report, and what kind of correction to prefer.

### Agent frameworks can become the product

This repository intentionally does not own your execution environment.

Agents Cookbook is a **prompt library**, not a model server, sandbox, repository indexer, workflow engine, durable state system, or orchestration framework. OpenCode, Pi, or another host provides those capabilities.

## The repository-improvement chain

One of the main patterns in this library is separating discovery from proof:

```text
repository signal
    ↓
repository-improvement-scout
    ↓
evidence-backed investigation lead
    ↓
codebase-finding-derivation
    or a narrow specialist
    ↓
proven finding
    ↓
smallest corrective change
```

This matters because the skill that gets the idea **“we should inspect this”** should not also be allowed to silently promote that idea into **“this is broken.”**

The stages have different jobs:

- **Scout:** decide what deserves investigation.
- **Derive:** decide whether the evidence justifies a finding.
- **Specialist:** prove the exact failure class and its boundary.
- **Fix:** prefer deletion, consolidation, stronger ownership, or a shorter control/data path over another abstraction.

## Skill design

The skills are intentionally small and opinionated.

A skill should own one narrow review or discovery question and have a hard invariant. Specialist review skills own one failure class.

Most skills follow the same shape:

```text
INVARIANT

HUNT
- exact patterns worth inspecting

PROVE
- evidence required before reporting

DO NOT REPORT
- false positives and nearby concerns

PREFER
- smallest useful correction direction

OUTPUT
- evidence-backed result
```

Common rules across the library:

- trace real production or test paths instead of reporting grep matches;
- prove the consequence before calling something a defect;
- protect coherent boundaries that do not need refactoring;
- prefer deletion and consolidation over new managers, registries, wrappers, or compatibility layers;
- accept `LEAVE ALONE`, `CLEAN`, or `INSUFFICIENT EVIDENCE` as legitimate outcomes;
- avoid fixed finding quotas;
- keep prompts small enough to work well with local models and bounded context.

## Skill map

The current library groups prompts by the kind of question they answer:

- **Discovery and evidence** — repository scouting, finding derivation, fact grounding, plan gaps, validation, red-team review.
- **Concurrency** — stale work and UI lifecycle races.
- **Execution integrity** — atomicity, retries/idempotency, resource lifetime, failure contracts.
- **Semantic authority** — repeated decisions, durable commit authority, resolved facts, state authority, invalid states.
- **Structural simplicity** — repeated observation, no-value call chains, obsolete paths, hidden effects, oversized dependency surfaces.
- **Test-derived architecture** — amplified work, repeated setup, isolation boundaries, orchestration complexity, deterministic causality, state contamination, contract coupling.
- **Performance** — algorithmic scaling, repeated work, I/O, memory, batching, contention, and cache economics.

Browse every skill and the important overlap rules in the [`skill catalog`](skills/README.md).

## Skills, agents, and flows

There are three reusable layers:

```text
skill  -> methodology
agent  -> thin role / permission / output wrapper
flow   -> optional composition recipe
```

### Skills

`skills/` is the library core. A skill should make sense when loaded directly without Ping-Pong state, sibling reviewer output, a run store, or a specific model provider.

### Agent prompts

`agents/` contains thin runtime-ready wrappers around skills plus a few coordinator prompts. They add role boundaries, permissions, default model aliases, or output contracts; they should not duplicate the methodology in the skill.

The repository currently has **12 agent prompts**.

### Flows

`flows/` contains optional compositions. They sequence existing prompts but do not own unique reviewer intelligence.

The provided `ping-pong-plan` and `ping-ping-build` flows use exactly eight independent reviewers. Adding a new standalone skill does **not** silently enlarge that gate.

## OpenCode and Pi

OpenCode and Pi are supported consumers of the same canonical Markdown sources.

```bash
scripts/link-opencode-local.sh
```

Runtime adapters handle the small integration differences required by those hosts. They are not separate behavioral copies of the prompts.

For runtime qualification and the local 98,304-token context profile, see [`docs/local-runtime-qualification.md`](docs/local-runtime-qualification.md) and [`protocols/context-budget.md`](protocols/context-budget.md).

## Evaluation

A prompt loading successfully proves almost nothing about its quality.

`evals/` focuses on **discrimination**: can the skill find its own failure class while rejecting safe cases and neighboring failure classes?

The cookbook supplies the prompt and evaluation contract. The host runtime owns actual model execution, sandboxing, tool access, and repository materialization.

See [`evals/README.md`](evals/README.md) and [`evals/sharp-skill-discrimination.md`](evals/sharp-skill-discrimination.md).

## Repository layout

```text
skills/       reusable prompt methodology — the library core
agents/       thin role and coordinator prompts
flows/        optional composition recipes
protocols/    portable evidence/context/output conventions
adapters/     OpenCode/Pi integration
scripts/      install and validation helpers
evals/        prompt-quality and discrimination cases
docs/         architecture and usage documentation
```

There is one canonical Markdown source for each skill and agent. Supported runtime installation links those sources rather than maintaining runtime-specific copies.

## Design boundary

Agents Cookbook owns:

- reusable prompt methodology;
- review/discovery invariants;
- role and authority contracts;
- optional composition recipes;
- portable evidence and output conventions.

The host owns:

- model execution and context management;
- tool execution and permissions;
- filesystem/process/network isolation;
- delegation and session lifecycle;
- persistence and runtime state.

That boundary is intentional. The useful thing in this repository should remain the **prompts**.

## Documentation

- [Skill catalog](skills/README.md)
- [Architecture](docs/architecture.md)
- [Ping-Pong planning example](docs/ping-pong-plan-flow.md)
- [Local runtime qualification](docs/local-runtime-qualification.md)
- [Context budget](protocols/context-budget.md)
- [Run artifacts](protocols/run-artifacts.md)
- [Evaluation guidance](evals/README.md)
- [Sharp skill discrimination](evals/sharp-skill-discrimination.md)
- [Non-technical walkthrough](docs/non-technical-walkthrough.md)
