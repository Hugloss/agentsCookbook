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

`--repository-root`, package names, output path, file/function thresholds, top-N selection, and transitive depth are configurable. The source package name can be derived from the source-root basename when that is correct for the target repository.

## Evidence authority

`refactor-focus` does not treat every match as equivalent.

| Authority | Current evidence | May establish corresponding-test authority? |
| --- | --- | --- |
| `confirmed` | exact static import; explicit helper/loader source relationship | yes |
| `supporting` | mirrored path; same-name convention; bounded transitive owner | no |
| `candidate` | path-feature overlap | no |

When the same test is found by more than one mechanism, stronger evidence wins. For example, an exact import overrides a same-name match for that test file.

Only confirmed evidence can set `has_corresponding_tests`, `test_sync_required_if_split`, confirmed test-size metrics, or actions such as updating/splitting an existing corresponding test. Supporting and candidate evidence instead tell the agent what it should inspect next.

## P1 qualification

Run the built-in stdlib-only adversarial corpus with:

```bash
python -m scripts.agent_economics.refactor_focus_qualification
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
- an intentionally unsupported `importlib.import_module()` relationship;
- non-default source and test package names.

Qualification records `TRUE_RELEVANT`, `FALSE_RELEVANT`, `MISSED_RELEVANT`, `UNKNOWN`, and true-negative counts plus precision, recall, bounded-candidate reduction, evidence reduction, runtime, and lower-bound scan economics.

The gate fails if a non-authoritative signal becomes confirmed authority or if a relationship that the probe claims to support is missed.

Exact read and AST-parse invocation accounting is intentionally deferred to Phase 2, which will make the analysis parse-once and publish exact economics instead of lower bounds.

## Roadmap

See [Agent Economics Probe phases](agent-economics-probe-phases.md) for the hardening sequence and planned `context-focus`, `test-focus`, `change-impact`, `coupling-focus`, `hotspot-focus`, and `tool-budget` probes.
