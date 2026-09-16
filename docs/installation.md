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

There is currently no automatic uninstaller.

To remove an installation, delete only the cookbook-created symlinks whose resolved target points into your cloned `agentsCookbook` repository. Do not recursively delete an OpenCode/Pi configuration directory that may contain unrelated user content.

If you installed with `--force`, the installer may have created timestamped backup paths beside previous conflicts. Those backups are intentionally never deleted automatically; restore or remove them manually after verifying their contents.

## Updating

Because runtime locations link to the clone, updating the checked-out repository changes the prompt content visible to supported hosts.

For reproducible use, pin the clone to a known commit or tag rather than automatically tracking `main`.

Until the project publishes a formal release/backport policy, `main` should be treated as active development rather than a long-term compatibility branch.

## Model aliases in agent wrappers

The `skills/` library does not require a particular model provider.

Some files under `agents/` include repository-owner deployment aliases such as `liteLLM/gemma4`, `liteLLM/gpt-oss`, or `liteLLM/devstral`. These are example/default wrapper configuration, not requirements of the underlying methodology. Adapt or override them for your runtime.

## Validation

Structural repository checks:

```bash
scripts/check-canonical-sources.sh
node scripts/run-skill-benchmarks.js --validate-corpus
scripts/smoke-opencode-scripts.sh
scripts/smoke-run-artifacts.sh
```

Runtime-specific preflight:

```bash
scripts/preflight-opencode-ping-pong.sh
scripts/preflight-pi-ping-pong.sh
```

These preflight scripts verify repository/runtime contracts; they do not make general guarantees about your model server, operating system, or third-party host implementation.
