# Agent Economics Probes — Hardening and Expansion Phases

## Goal

Make the AgentCookbook probe family portable across ChatGPT coding environments and repositories. Probes should cheaply identify where an agent should spend evidence, context, tool-call, and verification budget. They may discover, measure, rank, bound, and explain; they must not edit production code.

## Portability rule

Repository-specific facts must be supplied as parameters or derived from supplied paths when derivation is unambiguous. Do not hardcode application package names, repository roots, test subdirectories, logging frameworks, or project-specific commands into generic probes.

## Phase 0 — P0 correctness and portability closure

Status: **complete** on the Agent Economics Probes branch.

1. Separate confirmed test evidence from heuristic candidate matches.
   - Heuristic `feature_fallback` matches may suggest what to inspect next.
   - They must not set `has_corresponding_tests`, `test_sync_required_if_split`, confirmed test size, or test-splitting recommendations.
   - Ambiguous-only matches must require correspondence verification before a source/test action is recommended.
2. Correct Python package identity for `__init__.py`.
   - `pkg/__init__.py` maps to `pkg`, not `pkg.__init__`.
   - Relative-import resolution must preserve package semantics for `__init__.py`.
3. Replace guessed reporting anchors with repository-relative reporting.
   - Accept `repository_root` explicitly.
   - If omitted, derive a common ancestor from source/test roots.
   - Use one reporting anchor for source and test paths.
4. Remove application-specific assumptions.
   - No hardcoded `app` package in import analysis.
   - No hardcoded `tests/unit` lookup.
   - No dependency on an application's logging utilities.
   - CLI accepts source root, tests root, repository root, package names, thresholds, output path, top-N, and transitive depth.
5. Add P0 adversarial qualification cases.
   - custom non-`app` package;
   - `__init__.py` imported as its package;
   - weak feature-only test match cannot prescribe a split;
   - source/test report paths use the same repository-relative anchor;
   - same-name tests may live outside `tests/unit`.

Exit criteria: every P0 adversarial case passes and the scripts compile with only Python stdlib plus their own probe modules.

## Phase 1 — Qualification corpus and evidence authority

Status: **complete** on the Agent Economics Probes branch.

Build a repository fixture corpus with known positive, negative, ambiguous, and unsupported relationships. Track `TRUE_RELEVANT`, `FALSE_RELEVANT`, `MISSED_RELEVANT`, `UNKNOWN`, and explicit true negatives. Measure precision, recall, candidate reduction, evidence reduction, runtime, a lower bound on files parsed, and a lower bound on bytes read. Fail qualification when false authority is introduced even if unit tests pass.

P1 also establishes three evidence-authority classes:

- `confirmed`: direct import or explicit helper/loader relationship;
- `supporting`: mirrored/name convention or bounded transitive ownership;
- `candidate`: heuristic path-feature overlap.

Only `confirmed` evidence may set corresponding-test authority or prescribe confirmed-test actions. Exact read/AST invocation accounting remains Phase 2 work.

## Phase 2 — Probe economics and parse-once analysis

Parse/read each Python file once per probe run and reuse cached syntax/import/line metadata. Record scan cost in the artifact: files read, bytes read, AST parses, elapsed time, candidate reduction, and evidence lines selected. Bound expensive transitive analysis explicitly.

## Phase 3 — Python/pytest ownership closure

Extend test evidence without pretending heuristics are facts. Add parameterized support for `conftest.py` ancestry, fixtures, `pytest_plugins`, helper-to-helper test imports, common dynamic imports, and declared repository-specific ownership hints. Every evidence source gets an authority class and provenance.

## Phase 4 — Common Agent Economics Probe contract

Define a versioned output contract shared by all probes. Include schema/tool version, repository/config identity, evidence, derived facts, interpretation, uncertainty, warnings, candidates, required next evidence, deferred evidence, verification suggestions, and economics. Keep facts and recommendations separately represented.

## Phase 5 — Repository discovery semantics

Add configurable discovery policy. Prefer repository truth when available: Git tracked/untracked policy and ignore semantics. Handle symlinks and out-of-repository paths explicitly. Replace path-fragment exclusions with normalized relative-path rules. Keep a pure-filesystem fallback for environments without Git.

## Phase 6 — `context-focus`

Given a task/query and an evidence budget, return the smallest ranked set of files/symbols the agent should inspect first. Bound by files, lines, bytes, or tokens. Use Hashmarks repository intelligence when available, with a lightweight standalone fallback.

## Phase 7 — `test-focus`

Given proposed/changed files or symbols, produce a staged verification ladder: direct owning tests, affected dependents, package/component gates, then broader validation when evidence requires it. The probe suggests order and evidence; it does not declare broader verification unnecessary.

## Phase 8 — `change-impact` and `coupling-focus`

Add static impact and historical co-change probes. Keep structural dependency evidence separate from Git-history correlation. Report unexpected coupling and uncertainty rather than treating co-change as dependency authority.

## Phase 9 — `hotspot-focus`

Combine separately visible dimensions such as complexity, churn, fan-in/fan-out, ownership weakness, and verification weakness. Do not hide them behind one opaque score. Ranking is for investigation priority, not autonomous refactoring authority.

## Phase 10 — `tool-budget`

Measure agent-environment overhead: available tool/schema footprint, duplicated capabilities, injected repository context, instruction/skill footprint, and likely unused context. Use this to identify avoidable context/tool-call cost before repository work begins.

## Phase 11 — Agent outcome benchmark

Compare representative repository tasks with and without probes. Measure files opened, lines/bytes/tokens read, tool calls, verification attempts, elapsed execution cost where available, and final correctness. Promotion requires demonstrated economics improvement without loss of correctness.
