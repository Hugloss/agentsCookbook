# Agent Economics Probes

Agent Economics Probes are optional, portable helpers for deciding where a coding agent should spend its next context, evidence, tool-call, and verification budget.

They are deliberately narrower than an agent framework:

- probes may discover, measure, rank, bound, and explain;
- probes do not edit target repository source code;
- the host runtime still owns execution, permissions, sandboxing, sessions, and persistence;
- repository-specific assumptions should be parameters or unambiguous derivations, not hardcoded policy.

The first reference probe is **`refactor-focus`**. It identifies oversized Python refactoring candidates and separates direct source/test evidence from weaker conventions and heuristics.

## Portable use

The implementation uses only the Python standard library and its own package modules.

From this repository:

```bash
python -m scripts.agent_economics.refactor_focus_cli \
  --source-root src/my_package \
  --tests-root tests \
  --repository-root . \
  --package-name my_package \
  --tests-package-name tests \
  --artifact-path .agent-artifacts/refactor-focus.json
```

If the `agent_economics/` directory is copied into another ChatGPT or coding-agent environment, run it from the directory that contains the package:

```bash
python -m agent_economics.refactor_focus_cli \
  --source-root src/my_package \
  --tests-root verification \
  --repository-root . \
  --package-name my_package \
  --tests-package-name checks
```

`--repository-root`, package names, output path, file/function thresholds, top-N selection, source-transitive depth, test-helper depth, and pytest ownership depth are configurable. `--ownership-hints-path` optionally supplies explicit repository-relative source/test relationships. The source package name can be derived from the source-root basename when that is correct for the target repository.

## Evidence authority

`refactor-focus` does not treat every match as equivalent.

| Authority | Current evidence | May establish corresponding-test authority? |
| --- | --- | --- |
| `confirmed` | exact static import; literal dynamic import; bounded helper chain; active pytest fixture; loaded pytest plugin module-scope dependency; explicit repository ownership declaration | yes |
| `supporting` | mirrored path; same-name convention; bounded transitive owner | no |
| `candidate` | path-feature overlap | no |

When the same test is found by more than one mechanism, stronger evidence wins. For example, an exact import overrides a same-name match for that test file.

Only confirmed evidence can set `has_corresponding_tests`, `test_sync_required_if_split`, confirmed test-size metrics, or actions such as updating/splitting an existing corresponding test. Supporting and candidate evidence instead tell the agent what it should inspect next.

## P2 qualification

Run the built-in stdlib-only adversarial corpus with:

```bash
python -m scripts.agent_economics.refactor_focus_p2_qualification
```

The corpus materializes a temporary repository and exercises:

- exact source imports;
- helper-loader ownership;
- package `__init__.py` identity;
- stronger exact evidence overriding same-name evidence;
- mirrored-path and direct-name conventions without imports;
- bounded transitive ownership;
- heuristic feature matching;
- same-name false-authority pressure;
- unrelated negative cases;
- a literal `importlib.import_module()` relationship;
- non-default source and test package names.

Qualification records `TRUE_RELEVANT`, `FALSE_RELEVANT`, `MISSED_RELEVANT`, `UNKNOWN`, and true-negative counts plus precision, recall, bounded-candidate reduction, evidence reduction, runtime, and exact probe economics.

The gate fails if a non-authoritative signal becomes confirmed authority, if a relationship that the probe claims to support is missed, or if a discovered Python file is read or AST-parsed more than once in a probe run. P2 independently instruments `Path.read_bytes` and `ast.parse`; it does not trust the probe's own counters as proof.

Each probe artifact now includes an `economics` object with exact Python-analysis `files_read`, `bytes_read`, `ast_parses`, `read_failures`, `parse_failures`, `cache_hits`, `unique_files_cached`, `elapsed_ms`, `candidate_reduction`, `evidence_files_selected`, `evidence_lines_selected`, and active depth bounds. Auxiliary ownership-hint reads are reported separately and folded into `total_files_read` / `total_bytes_read`.

## P3 Python/pytest ownership

P3 adds bounded structural ownership recovery without promoting conventions into facts:

- exact static imports and literal `importlib.import_module(...)` / `__import__(...)`;
- test-helper to helper traversal bounded by `--helper-max-depth`;
- ancestor `conftest.py` fixtures, autouse fixtures, fixture dependencies, `usefixtures`, and literal `request.getfixturevalue(...)`;
- repository-local `pytest_plugins` traversal bounded by `--pytest-max-depth`;
- plugin fixtures are authoritative only when active; imports inside unused plugin fixtures do not become plugin-wide ownership;
- optional versioned JSON ownership hints using repository-relative paths; stale, absolute, or escaping declarations fail closed;
- provenance is attached to every match so another agent can inspect why evidence was admitted.

Run the P3 qualification with:

```bash
python -m scripts.agent_economics.refactor_focus_p3_qualification
```

Runtime-built dynamic module names remain unknown rather than guessed. Supporting filename/path conventions and candidate token overlap remain non-authoritative.

## Common probe contract

Every probe artifact now uses the same versioned `agent-economics-probe` v1 envelope:

```text
schema
tool
generated_at
repository
configuration
evidence
derived
interpretation
uncertainty
warnings
candidates
required_next_evidence
deferred_evidence
verification_suggestions
economics
```

The contract deliberately separates **measured facts**, **derived state**, **interpretation**, and **recommendations**. A candidate recommendation such as a refactoring strategy cannot appear in its `facts` object. Confirmed source/test evidence can yield focused verification suggestions; supporting or ambiguous evidence yields explicit uncertainty plus the next evidence the agent should obtain. Candidates omitted by a bounded `top_n` budget are preserved as `deferred_evidence` rather than disappearing silently.

Repository identity is a SHA-256 over the analyzed repository inputs and is independent of the checkout path. Configuration identity is a SHA-256 over semantic probe configuration; changing the artifact destination does not change it, while changing a depth/budget/threshold does. Ownership-hint bytes, when configured, participate through their content identity. Paths in the portable contract are repository-relative.

Run the P4 contract qualification with:

```bash
python -m scripts.agent_economics.probe_contract_qualification
```

P4 qualification also reruns the earlier probe behavior indirectly and checks contract validation, identity invalidation/stability, facts-versus-recommendations separation, deferred-evidence accounting, uncertainty requirements, and verification suggestions.

## Roadmap

See [Agent Economics Probe phases](agent-economics-probe-phases.md) for the hardening sequence and planned `context-focus`, `test-focus`, `change-impact`, `coupling-focus`, `hotspot-focus`, and `tool-budget` probes.


## Repository discovery semantics (P5)

Repository discovery is part of probe evidence, not an invisible filesystem assumption. `refactor-focus` accepts `auto`, `git`, or `filesystem` discovery; tracked/untracked and ignored-file policy; explicit Python-file symlink policy; repeatable repository-relative exclusion globs; optional default exclusions; and a bounded Git command timeout. `auto` prefers Git repository truth and reports when it must fall back to filesystem discovery. The effective discovery policy is included in configuration identity and discovery observations are included in the evidence envelope.


## Context focus (P6)

`context-focus` answers a narrower question than a repo map: **what should the agent inspect next for this task within this explicit budget?** It discovers configurable source/text suffixes through the P5 repository policy, then performs a bounded lexical fallback scan and emits transparent ranking evidence plus explicit uncertainty. The selection budget has independent file, line, byte, and estimated-token ceilings; the repository scan has separate file/byte/per-file ceilings so a large repository cannot silently consume the entire agent budget.

Optional `--repository-intelligence-path` accepts a versioned provider-neutral JSON shortlist. That is the integration seam for Hashmarks or another repository-intelligence producer. External scores are supporting ranking evidence only: they cannot bypass discovery policy, stale paths are ignored with warnings, and the auxiliary JSON itself is excluded from context candidates. The output uses the common Agent Economics Probe contract from P4.
