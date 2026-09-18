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

Only `confirmed` evidence may set corresponding-test authority or prescribe confirmed-test actions. P1 intentionally deferred exact read/AST invocation accounting to Phase 2.

## Phase 2 — Probe economics and parse-once analysis

Status: **complete** on the Agent Economics Probes branch.

Read and AST-parse each discovered Python file at most once per probe run, then reuse one analysis cache for line counts, import extraction, dynamic-loader inspection, and function-size analysis. Publish exact economics in every probe artifact: files read, bytes read, AST parses, read/parse failures, cache hits, unique cached files, elapsed time, candidate reduction, selected evidence files/lines, and the explicit transitive-depth bound.

Qualification independently instruments `Path.read_bytes` and `ast.parse` so repeated reads/parses fail the gate even if the probe's own counters are wrong. The P2 corpus requires one read and one AST parse per discovered Python file, exact byte accounting, zero read/parse failures on the valid corpus, and exact bounded evidence-line accounting.

## Phase 3 — Python/pytest ownership closure

Status: **complete** on the Agent Economics Probes branch.

Extend test evidence without pretending heuristics are facts. P3 adds parameterized, bounded support for test-helper chains, ancestor `conftest.py` fixtures, autouse fixtures, fixture dependencies, literal `request.getfixturevalue`, repository-local `pytest_plugins`, active plugin fixtures, literal dynamic imports, and versioned repository ownership hints. Every admitted relationship carries provenance. Runtime-computed module names remain unknown. Unused fixtures, depth-overflow helper/plugin chains, and naming/path heuristics cannot become confirmed ownership. Ownership-hint paths must be repository-relative, discovered files; stale, absolute, or escaping declarations fail closed. Auxiliary hint-file reads are reported separately in probe economics and included in total read/byte accounting.

P3 qualification requires all expected structural relationships to be confirmed, zero false authority across bounded/unused negative cases, P2 parse-once qualification to remain green, and all invalid ownership-hint cases to fail closed.

## Phase 4 — Common Agent Economics Probe contract

Status: **complete** on the Agent Economics Probes branch.

All probe artifacts use the versioned `agent-economics-probe` v1 envelope. The common sections are schema/tool identity, portable repository identity, semantic configuration identity, evidence, derived facts, interpretation, uncertainty, warnings, bounded candidates, required next evidence, deferred evidence, verification suggestions, and economics. Candidate facts, derived state, interpretation, and recommendations are separate objects so an agent cannot accidentally treat a recommendation as measured repository truth.

Repository identity is a checkout-location-independent SHA-256 over analyzed repository inputs. Configuration identity is a canonical SHA-256 over semantic probe configuration and excludes the artifact destination. Optional ownership-hint content identity is included in configuration identity. P4 qualification proves schema validity, identity stability and invalidation, repository-relative paths, deferred-evidence accounting, facts/recommendation separation, uncertainty-to-next-evidence linkage, and verification suggestions for confirmed ownership. P1–P3 qualification must remain green under the v1 envelope.

## Phase 5 — Repository discovery semantics

Status: **complete** on the Agent Economics Probes branch.

P5 replaces recursive path-fragment scanning with a parameterized repository discovery authority. `auto` prefers the Git worktree when available; explicit `git` and `filesystem` modes are also supported. Git discovery has separate tracked/untracked and ignored-file policy, lists the repository once for all requested roots, and records the backend and bounded command count in the artifact. Exclusions are normalized repository-relative segment globs, so patterns cannot silently cross directory boundaries and `docs/_build/**` now behaves as written. Python file symlinks have explicit `exclude`, `reject`, or `within-repo` policy; escaping symlinks and discovery roots outside the repository fail closed. Auto mode uses a deterministic filesystem fallback when Git is unavailable and publishes that loss of Git authority as a warning.

P5 qualification covers Git tracked/untracked/ignored semantics, one-listing economics, normalized and anchored exclusions, the historical `docs/_build` case, symlink policy, out-of-repository and nested-root failures, explicit Git failure outside a worktree, filesystem fallback, and discovery-policy/repository-identity invalidation in the common P4 contract. P1–P4 qualification must remain green.

## Phase 6 — `context-focus`

Status: **complete** on the Agent Economics Probes branch.

Given a task/query, P6 returns a bounded ranked evidence set without editing repository files. The stdlib-only fallback is language-neutral across configurable code/text suffixes and reuses P5 Git/filesystem discovery. Ranking components remain visible: path-token overlap, basename overlap, content-token evidence, bounded occurrence evidence, and optional provider-neutral repository-intelligence support. Selection is independently bounded by files, lines, bytes, and an explicitly labeled token estimate; repository scanning is separately bounded by files, bytes, per-file bytes, and evidence anchors.

Provider-neutral intelligence JSON can carry stronger repository facts from systems such as Hashmarks without creating a runtime dependency or granting execution authority. Stale intelligence paths are warnings; auxiliary intelligence and output artifacts cannot become context candidates themselves. Scan truncation, filesystem fallback, no-match results, read/stat failures, and oversized files remain explicit uncertainty/warnings rather than silently widening the scan. P6 also generalizes P5 discovery to configurable suffix sets while preserving the Python-specific wrapper used by refactor-focus.

P6 qualification requires multi-language ranking, strict context and scan budgets, external-intelligence vocabulary-mismatch rescue, stale-hint handling, checkout-independent repository path-set identity, task/config invalidation, auxiliary-input self-exclusion, bounded intelligence input, common P4 contract validity, and continued P1–P5 qualification.

## Phase 7 — `test-focus`

Status: **complete** on the Agent Economics Probes branch.

Given changed repository paths, P7 builds a bounded staged verification ladder without executing tests. Stage 1 contains changed tests plus tests with confirmed direct ownership of changed Python source. Stage 2 contains confirmed tests of bounded reverse source dependents. Stage 3 contains explicit repository/component gates supplied by the caller. Mirrored paths and same-name conventions remain supporting evidence only and can never become direct-test authority. Non-Python, deleted, undiscovered, or otherwise unmapped changes publish uncertainty and required next evidence instead of fabricated test ownership.

Focused verification suggestions never assert that broader verification is unnecessary. If no broader gates are supplied, the contract records that missing escalation boundary explicitly. Test selection and reverse-impact traversal have independent bounds; omitted tests/sources are preserved as deferred evidence. P7 reuses the P1–P5 ownership, pytest, hints, discovery, parse-once, and common-contract infrastructure rather than maintaining a second authority model.

P7 qualification requires direct-vs-affected separation, naming-only false-authority prevention, changed-test handling, non-Python and deleted-path uncertainty, bounded omission accounting, broader-gate escalation, repository identity stability/invalidation, fail-closed escaping paths, common P4 contract validity, and continued P1–P6 qualification.

## Phase 8 — `change-impact` and `coupling-focus`

Status: **complete** on the Agent Economics Probes branch.

P8 adds two deliberately separate probes. `change-impact` computes bounded reverse reachability over the current Python import graph for changed paths under a parameterized source root. Direct and transitive source dependents retain their explicit depth and module chain. Deleted/renamed Python paths may seed impact lexically while publishing that the current source bytes are unavailable; unsupported-only changes short-circuit without scanning/parsing the Python tree. Source-depth and source-count bounds preserve omitted dependents as deferred evidence.

`coupling-focus` mines bounded Git history for repeated co-change correlation. It exposes raw shared/target/candidate commit counts separately from derived target coverage, candidate coverage, and Jaccard. First-parent history is the default and is parameterized; mega-commits are suppressed by an explicit file-count ceiling; total history output has a hard byte bound; candidate suffixes, exclusions, history length, shared-commit threshold, top-N, commit samples, and Git timeout are all parameters. Co-change always carries `dependency_authority=false` and requires structural/domain inspection before use.

P8 qualification requires reverse-impact depth/budget correctness, deleted-module recovery, zero Python scans for unsupported-only changes, repository identity stability/invalidation, history correlation counts, mega-commit suppression, bounded-history uncertainty, hard history-byte failure, suffix/exclusion policy, fail-closed paths/Git absence, common P4 contract validity, and continued P1–P7 qualification.

## Phase 9 — `hotspot-focus`

Status: **complete** on the Agent Economics Probes branch.

P9 ranks source files for investigation using separately visible facts: source lines, AST branch points, largest function, static fan-in/fan-out, bounded first-parent Git churn, anonymized author concentration, and confirmed test ownership. It never emits an opaque composite risk score. Ranking is an explicit configurable lexicographic dimension order and is labeled investigation priority only.

History has hard commit, byte, and timeout bounds. In `auto` mode unavailable Git history degrades to explicit unknown values rather than zero churn; `required` fails closed; `disabled` supports a static-only run. Missing test-tree evidence likewise remains unknown rather than becoming a false zero-coverage claim. P9 reuses the P1–P8 discovery, parse-once, import, ownership, and common-contract authorities.

P9 qualification requires visible independent dimensions, no opaque score, deterministic lexicographic ranking, static fan-in, bounded churn, anonymized author concentration, confirmed test evidence, static-only unknown-not-zero semantics, hard history-byte failure, common P4 contract validity, and continued P1–P8 qualification.

## Phase 10 — `tool-budget`

Measure agent-environment overhead: available tool/schema footprint, duplicated capabilities, injected repository context, instruction/skill footprint, and likely unused context. Use this to identify avoidable context/tool-call cost before repository work begins.

## Phase 11 — Agent outcome benchmark

Compare representative repository tasks with and without probes. Measure files opened, lines/bytes/tokens read, tool calls, verification attempts, elapsed execution cost where available, and final correctness. Promotion requires demonstrated economics improvement without loss of correctness.
