# Agent Economics package

Portable, standard-library-only probes that help coding agents decide what evidence to inspect before editing.

Run the refactor probe from an Agents Cookbook checkout:

```bash
python -m scripts.agent_economics.refactor_focus_cli --source-root src/pkg --tests-root tests --repository-root . --package-name pkg
```

Run its adversarial qualification corpus:

```bash
python -m scripts.agent_economics.refactor_focus_qualification
```

The directory can also be copied by itself into another environment. From the copied package's parent directory, use `python -m agent_economics.refactor_focus_cli ...`.

See `docs/agent-economics-probes.md` in the repository for the evidence-authority contract and portability rules.
