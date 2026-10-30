# Installation and platform support

The Markdown prompts are platform-independent. The repository-owned helper scripts are not.

## Supported paths

### Prompt-only use

Any runtime that can load Markdown prompts can use the skills directly. Copy or reference the relevant `skills/<name>/SKILL.md` file and adapt host-specific metadata outside the skill when needed.

### OpenCode and Pi helper installer

The provided installer is currently **tested on Ubuntu/Linux and WSL** through repository CI and local development.

It assumes a Unix-like environment with:

- Bash;
- Git;
- standard Unix/GNU filesystem utilities such as `ln`, `mv`, `readlink`, and `realpath`;
- symlink support;
- Node.js for repository validation scripts;
- OpenCode and/or Pi only when you intend to use those runtime integrations.

The helper installer is not currently claimed as native macOS or native Windows support. On those platforms, use the Markdown prompts directly or adapt the install locations for your host.

## Inspect before installing

The installer supports a dry run:

```bash
scripts/link-opencode-local.sh --dry-run
```

Run that first if you already have custom agents, skills, plugins, or Pi extensions.

The installer does not silently overwrite unrelated files. Conflicts fail closed unless `--force` is supplied. With `--force`, conflicting paths are moved to timestamped backup paths before cookbook-owned links are created.

## Install

```bash
git clone https://github.com/Hugloss/agentsCookbook.git
cd agentsCookbook
scripts/link-opencode-local.sh
```

By default the installer links canonical sources into the host locations derived from your environment. Custom destinations are available through:

```text
--global-dir DIR
--pi-agent-dir DIR
--shared-skill-dir DIR
```

Use `scripts/link-opencode-local.sh --help` for the exact interface.

## What gets installed

The helper links:

- canonical agent Markdown files into OpenCode and Pi agent locations;
- canonical skill directories into the shared skill location;
- the narrow OpenCode review-artifact adapter;
- the narrow Pi review-artifact extension.

The canonical files remain in the cloned repository. The runtime locations are links, not behavioral copies.

## Removing the cookbook

Use the repository-provided uninstaller with the same destination options used for installation:

```bash
scripts/unlink-opencode-local.sh
# If custom destinations were used:
scripts/unlink-opencode-local.sh --global-dir DIR --pi-agent-dir DIR --shared-skill-dir DIR
```

The uninstaller removes only recognized cookbook-owned links; it preserves unrelated files and links. Run it before deleting or moving your cookbook checkout so it can still identify the links it owns. Do not recursively delete an OpenCode/Pi configuration directory that may contain unrelated user content.

If you installed with `--force`, the installer may have created timestamped backup paths beside previous conflicts. Those backups are intentionally never deleted automatically; restore or remove them manually after verifying their contents.

## Updating

Because runtime locations link to the clone, updating the checked-out repository changes the prompt content visible to supported hosts.

For reproducible use, pin the clone to a known commit or tag rather than automatically tracking `main`.

Until the project publishes a formal release/backport policy, `main` should be treated as active development rather than a long-term compatibility branch.

## Runtime configuration ownership

Canonical agent files contain role identity, skill bindings, permission boundaries
and prompt/output contracts. They do **not** set a model, temperature, thinking
level, context window, or compaction policy. The installer links those files but
never edits OpenCode/Pi model configuration or synthesizes inference defaults.

Use the host's normal configuration resolution: global, project, per-agent and
explicit command-line settings remain the host's responsibility. In OpenCode,
configure models and per-agent inference options in your selected
`opencode.json`/`opencode.jsonc`; in Pi, use its native model selection and
settings. A missing option means native default behavior, not a cookbook default.
See [OpenCode configuration](https://opencode.ai/docs/config/) and
[agent options](https://opencode.ai/docs/agents/).

**Upgrade from older cookbook revisions:** previous wrappers supplied
`liteLLM/gemma4`, `liteLLM/gpt-oss`, `liteLLM/devstral`, and temperature
settings. They are no longer selected automatically. To preserve a previous
experiment, explicitly configure the desired model/options in the host and
record that configuration with the new campaign. Do not edit historical receipts
or frozen prompt revisions. Installing this revision does not migrate or rewrite
user settings.

Read-only roles, skill bindings, delegation limits, and the planning coordinator's
`systemPrompt: replace` remain unchanged: these define the selected role rather
than tune inference. Cookbook preflight verifies those role contracts, not a
particular model. The install regression exercises both untouched custom settings
(including false/zero values) and absent native configuration.

## Validation

Structural repository checks:

```bash
scripts/check-canonical-sources.sh
scripts/smoke-opencode-scripts.sh
scripts/smoke-run-artifacts.sh
```

Runtime-specific preflight:

```bash
scripts/preflight-opencode-ping-pong.sh
scripts/preflight-pi-ping-pong.sh
```

These preflight scripts verify repository/runtime contracts; they do not make general guarantees about your model server, operating system, or third-party host implementation.

Benchmark execution, the behavioral evaluation corpus, and Agent Economics tooling are maintained separately in [EvalShot](https://github.com/Hugloss/EvalShot). They are not prerequisites for installing or using the cookbook. For model-backed benchmark evaluation of skills, see [EvalShot's evaluation guide](https://github.com/Hugloss/EvalShot/blob/main/evals/README.md). For runtime/profile promotion, follow [local runtime qualification](local-runtime-qualification.md). Ordinary contribution checks follow [evaluation ownership and evidence](../CONTRIBUTING.md#evaluation-ownership-and-evidence).
