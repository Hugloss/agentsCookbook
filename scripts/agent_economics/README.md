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
```

The directory can also be copied by itself into another environment. From the copied package's parent directory, use `python -m agent_economics.refactor_focus_cli ...`.

See `docs/agent-economics-probes.md` in the repository for the evidence-authority contract and portability rules.

The JSON artifact includes exact per-run Python analysis economics (files/bytes read, AST parses, cache reuse, elapsed time, candidate reduction, and selected evidence lines), plus separately accounted auxiliary ownership-hint reads when configured. The built-in qualification independently verifies parse-once behavior and pytest/helper evidence authority.
