# Non-Technical Walkthrough

Agents Cookbook gives a local AI model several independent specialist reviewers instead of asking one context to remember and judge everything.

A full planning run works like this:

1. one coordinator drafts the plan;
2. eight read-only specialists review different risks;
3. the coordinator accepts or rejects their material findings;
4. one final plan is returned.

A user does **not** have to run the full flow. Each specialist is standalone, so you can ask only for coverage review, factual audit, red-team review, performance review, or another specialty.

## Why this helps smaller local models

The system avoids feeding every previous report back into every next reviewer. Each specialist receives the current subject plus a compact evidence packet. Full reports may be stored outside the active model context for the duration of a run and retrieved only when needed.

The supported local profile assumes a maximum context around 98k tokens, but normal work deliberately targets much less so there is room for repository evidence, tools, and the final answer.

## OpenCode and Pi

The same canonical agents and skills are used in both runtimes. Installation scripts expose those sources in the paths each runtime expects. There are not separate behavioral copies that can silently drift.

## Safety and ownership

Planning reviewers cannot edit code. Build reviewers cannot edit code. The build master owns implementation changes, and the planning coordinator owns the final plan. Runtime session evidence is used to verify that required reviewers actually ran.
