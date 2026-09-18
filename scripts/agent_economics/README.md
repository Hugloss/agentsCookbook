# Agent Economics package

Portable, standard-library-only probes that help coding agents decide what evidence to inspect before editing.

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
