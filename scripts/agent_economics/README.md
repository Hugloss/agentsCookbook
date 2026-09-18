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

Hotspot evidence also reports the largest definitions (functions/classes with qualified names and line spans), while keeping those dimensions independent rather than creating a composite quality score.

`qualify-local` receipts expose cumulative and per-stage execution economics so P11 dogfood can consume actual local command cost rather than reconstructing it manually.


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
