# Agent Economics package

Portable, standard-library-only probes and a constrained capability bridge that help coding agents decide what evidence to inspect and run repository-declared local verification before editing again.

**Runtime:** Python 3.11+ (the command-manifest reader uses stdlib `tomllib`).

Run the refactor probe from an Agents Cookbook checkout:

```bash
python -m scripts.agent_economics.refactor_focus_cli --source-root src/pkg --tests-root tests --repository-root . --package-name pkg
```

Run its adversarial qualification corpora:

```bash
python -m scripts.agent_economics.refactor_focus_p2_qualification
python -m scripts.agent_economics.refactor_focus_p3_qualification
python -m scripts.agent_economics.probe_contract_qualification
```

The directory can also be copied by itself into another environment. From the copied package's parent directory, use `python -m agent_economics.refactor_focus_cli ...`.

### Start in an unfamiliar repository

After materialization, the first command should normally be:

```bash
PYTHONPATH="$PWD/.agent-economics/scripts" python -m agent_economics doctor --repository-root .
```

\`doctor\` is read-only. It reports Git/Python/Ruff availability, detects likely Python source/test/package roots, and marks probe readiness. Detected roots are suggestions only; ambiguous repository structure remains explicit instead of becoming hidden configuration.

To see those observations projected into one reviewable campaign shape without writing anything:

\`\`\`bash
python -m agent_economics doctor --repository-root . --suggest-profile
\`\`\`

The result is always \`REVIEW_REQUIRED\`. It separates package/test roots from quality-analysis roots, preserves unresolved ambiguity and missing tool supply, and is not repository authority. Agent Economics does not automatically write or adopt the suggestion.

The package root is also a real CLI front door:

```bash
python -m agent_economics --help
python -m agent_economics help quality-debt
```

The command catalog is canonical for top-level help and capability reporting, preventing those public surfaces from drifting apart.

### First-class import and exact bootstrap

Agent Economics is a standalone Python package rooted at `scripts/agent_economics`. Consumers do not need repository-specific Python wrappers. Put the parent directory `scripts` on `PYTHONPATH`, then use either the package CLI or normal imports:

```bash
PYTHONPATH=/path/to/agentsCookbook/scripts python -m agent_economics test-focus ...
```

```python
from agent_economics.test_focus import GateSpec, test_focus_audit
from agent_economics.quality_debt import quality_debt_audit
```

For CI or another repository, materialize an exact agentsCookbook commit with the fail-closed bootstrap:

```bash
sh /path/to/bootstrap-agent-economics.sh \
  --revision <FULL_COMMIT_SHA> \
  --destination .agent-economics
export PYTHONPATH="$PWD/.agent-economics/scripts"
python -m agent_economics test-focus ...
```

The bootstrap never follows a branch tip or silently replaces an existing destination. It fetches the requested commit into a detached checkout, verifies the resolved commit, verifies the package exists, removes a partial destination on failure, and prints `AGENT_ECONOMICS_REVISION`, `AGENT_ECONOMICS_ROOT`, and `AGENT_ECONOMICS_PYTHONPATH` for receipts. `AGENT_ECONOMICS_ROOT` and `AGENT_ECONOMICS_REPOSITORY` can provide default destination/repository values.

A consumer-specific adapter is only needed when the repository must prove parity with an existing repository-owned authority or translate a repository-specific evidence schema. It is not required to run or import Agent Economics.

See `docs/agent-economics-probes.md` in the repository for the evidence-authority contract and portability rules.

The JSON artifact uses the versioned `agent-economics-probe` v1 contract. Facts, derived state, interpretation, recommendations, uncertainty, required/deferred evidence, verification suggestions, and economics are separate sections. Repository and semantic configuration identities are deterministic and portable across checkout locations. Exact per-run Python analysis economics include files/bytes read, AST parses, cache reuse, elapsed time, candidate reduction, and selected evidence lines, plus separately accounted auxiliary ownership-hint reads when configured.


### P5 discovery portability

`refactor-focus` defaults to `--discovery-mode auto`, which uses Git tracked plus non-ignored untracked Python files when the supplied repository root is a Git worktree root. Use `--untracked-policy exclude` for tracked-only analysis, `--ignored-policy include` only when ignored untracked files are intentionally evidence, `--symlink-policy exclude|reject|within-repo`, and repeat `--exclude-path` for repository-specific exclusions. `--no-default-excludes` disables the portable defaults. Explicit `filesystem` mode never pretends to apply `.gitignore`; that limitation is emitted in the probe warnings.


### P6 context-focus

Run `python -m scripts.agent_economics context-focus --task "..." --repository-root .`. The command is stdlib-only and accepts repository-relative roots, configurable suffixes, P5 discovery policy, independent scan/context budgets, and optional provider-neutral repository-intelligence JSON. Relative output and intelligence paths are anchored to the repository root. Existing refactor-focus invocation remains backward compatible: `python -m scripts.agent_economics ...` still routes arguments without a subcommand to refactor-focus.


### P7 test-focus

Run `python -m scripts.agent_economics test-focus --source-root src/pkg --changed-path src/pkg/foo.py --gate 'package=pytest -q'`. Changed paths, source/test roots, package names, ownership hints, discovery policy, reverse-impact depth/source limits, per-stage test limits, changed-input identity byte bounds, and broader gates are all parameters. `test-focus` only suggests verification order; it does not execute tests or waive broader repository validation.


### P8 change-impact

Run `python -m scripts.agent_economics change-impact --source-root src/pkg --changed-path src/pkg/foo.py`. Source/package roots, changed paths, reverse-depth/source bounds, P5 discovery policy, exclusions, symlink policy, and Git timeout are parameters. Unsupported-only changes deliberately avoid a repository-wide Python scan.


### P8 coupling-focus

Run `python -m scripts.agent_economics coupling-focus --target-path src/pkg/foo.py`. Git history length and output bytes are hard-bounded; mega-commit size, shared-commit threshold, candidate suffixes, exclusions, sample count, top-N, first-parent/all-parent mode, and timeout are parameters. Historical co-change is never dependency authority.


### P9 hotspot-focus

Run `python -m scripts.agent_economics hotspot-focus --source-root src/pkg --tests-root tests --package-name pkg`. Visible dimensions include source size, branch points, largest function, static fan-in/fan-out, bounded Git churn, anonymized author concentration, and confirmed test ownership. Ranking is configurable lexicographic investigation priority only; unavailable history/test evidence remains unknown rather than zero.


### P10 capability bridge

Use `python -m scripts.agent_economics capabilities --repository-root . --manifest agent-economics.toml` to inspect what the local environment can actually execute. Repository commands are declared as argv arrays in a version-1 TOML manifest and run with `run-command`; arbitrary shell strings are not the command authority. The runner hard-bounds time/stdout/stderr, keeps cwd inside the repository, records stable command/failure identities, and compares bounded SHA-256 identities of tracked workspace bytes before and after commands. Unexpected tracked mutation fails policy. `qualify-local` supports staged local verification with exclusive loop state, cumulative budgets, and no-progress/oscillation stops. Local qualification never claims CI or certification authority.

### P11 outcome benchmark

Use `python -m scripts.agent_economics benchmark-outcomes --input outcomes.jsonl` with paired `baseline` and `bridge` JSONL records. The comparator measures correctness plus CI activations, evidence/context consumption, tool calls, commands, iterations, verification attempts, failed edits, no-progress stops, bridge overhead, and local-vs-CI agreement. Benchmark results are evidence only and never automatically promote a workflow.


### Trust and isolation

A command manifest is executable-repository configuration. Passing `--manifest` and selecting a command is explicit authorization to execute that argv array. Commands are never parsed as shell strings, cwd is confined to the repository, time/output are bounded, and tracked-byte mutation is observed. The child still inherits whatever filesystem, environment, credentials, and network authority the host gives it. Agent Economics is not a sandbox and never reports network/sandbox isolation unless the host actually provides it.

`qualify-local` distinguishes focused, affected, component, and repository stages. Focused/affected passes remain incomplete; only an executed repository-stage pass can yield `LOCAL_QUALIFIED`, and every local result reports `ci_status=NOT_RUN`.


### quality-debt

`quality-debt` measures configured analyzer debt without making policy decisions. The first adapter consumes Ruff JSON diagnostics through the shared bounded-process primitive; it does not reimplement Ruff's complexity semantics.

```bash
python -m scripts.agent_economics quality-debt \
  --repository-root . \
  --root src --root scripts \
  --exclude scripts/retained \
  --limit C901=10 --limit PLR0912=12 \
  --max-file-lines 1200 --file-line-root src \
  --artifact .agent-artifacts/quality-debt.json
```

Repeat `--exclude` for repository-relative path prefixes that are outside the admitted analyzer evidence. Exclusions apply consistently to analyzer invocation, analyzed-source identity, findings, and file-length evidence. `--file-line-root` independently scopes the line ceiling when only production roots own that policy; without it, the ceiling applies to every `--root`.

A baseline comparison is valid only when analyzer/version, roots, exclusions, limits, and file-line policy have the same comparable identity. Otherwise the result is `INCOMPARABLE_BASELINE`. Per-file increases remain visible even when repository-wide debt falls. Baselines are measurement evidence, not acceptance or certification authority.

The artifact also exposes `evidence.detailed_findings` as deterministic machine-readable rows with `path`, `line`, `rule`, `observed`, `limit`, and `excess`. `derived.summary.files` remains the per-file aggregation, so a low-context consumer can rank current hotspots without reparsing analyzer messages or opening candidate files first. These measurements prioritize investigation; they do not authorize edits or change repository policy. Each debt candidate therefore publishes `required_next_evidence.kind=test_focus` for its exact target instead of pretending that a high debt value is sufficient edit evidence. Run `test-focus` with that target as the changed path and the repository's source/test roots to recover confirmed/supporting test ownership and affected verification before selecting an edit.

Hotspot evidence also reports the largest definitions (functions/classes with qualified names and line spans), while keeping those dimensions independent rather than creating a composite quality score.

`qualify-local` receipts expose cumulative and per-stage execution economics so P11 dogfood can consume actual local command cost rather than reconstructing it manually.


### behavior-preservation

Use `behavior_preservation_readiness(...)` before a structural split when the goal is to preserve existing behavior. It binds the exact source identity, declared behavior/risk boundaries, confirmed test references, a PASS execution receipt for those exact source/test identities, provider freshness, and repository-owned broader gates. Every boundary must also name the frozen test evidence identities that prove that boundary; missing bindings or references to tests outside the selected/executed test set fail closed as `EVIDENCE_REQUIRED`.

The result is evidence readiness only: `READY_FOR_BEHAVIOR_PRESERVING_EDIT` never authorizes an edit and never claims that a future refactor is safe. Indirect-only protection yields `TEST_STRENGTHENING_REQUIRED`; stale, failed, mismatched, unexecuted, or incomplete evidence yields `EVIDENCE_REQUIRED`. Coverage percentages may be recorded but cannot independently promote readiness.

After the external edit, rerun the bound focused tests and repository gates, then build `behavior_preservation_receipt(...)`. BP2 binds the exact BP1 evidence identity and pre-edit source identity to a canonical post-edit source-set identity. Callers must provide every changed/new production source as a `post_edit_source_references` row with its evidence identity, and must separately provide repository-owned `post_edit_change_set_evidence` that attests the complete changed/new production source set. BP2 requires the declared source references to match that independent change-set evidence exactly; a self-consistent but incomplete source identity/execution receipt cannot prove completeness by itself. BP2 also requires the frozen test path/evidence identities to remain unchanged, requires a PASS execution receipt for those exact frozen tests against that exact source set, and requires PASS receipts for the exact repository gates declared by BP1. Changed tests, source-set completeness mismatches, missing/failed executions, or incomplete gate receipts fail closed as `POST_EDIT_EVIDENCE_REQUIRED`.

A successful BP2 receipt reports `BEHAVIOR_PRESERVATION_VERIFIED`, but still does not authorize merge, prove architectural improvement, own repository policy, or treat reduced debt/complexity as proof of preserved behavior. A repository may run additional affected/component verification according to its own policy. Remeasure current debt separately; the next target must come from fresh repository evidence rather than a frozen hotspot list.

Probe artifacts that do not publish their own top-level `evidence_identity` can be bound canonically with `agent_economics.probe_contract.sha256_identity(payload)`. Consumers should not invent repository-local JSON serialization or hashing rules.


### dogfood-corpus

`dogfood-corpus` emits the immutable adversarial task specification used for empirical baseline-vs-bridge runs. It contains the 12 planned failure/authority/bounds cases and a protocol that requires local repair iterations, no CI during the repair loop, outcome freeze before opening the oracle, and one independent CI qualification only after local evidence is frozen.

```bash
python -m scripts.agent_economics dogfood-corpus \
  --artifact .agent-artifacts/dogfood-corpus.json
```

The corpus generator does not execute or repair tasks. Its identity makes it possible to bind P11 outcome records to an exact experimental task definition rather than a mutable task name.


### Stress qualification

The permanent Agent Economics qualification includes a bounded stress layer after the deterministic phase regressions. It repeatedly exercises semantic identity stability, independent stdout/stderr hard limits, non-UTF8 output, a 128-iteration loop-state boundary, and repeated process-tree timeout termination.

The GitHub Agent Economics job has a 20-minute outer timeout. Individual commands retain much smaller local bounds; the outer timeout is safety headroom for the complete suite, not permission for a single probe or repair command to run unbounded.
