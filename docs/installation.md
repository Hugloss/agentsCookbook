# Installation and platform support

The Markdown prompts are platform-independent. The repository-owned helper scripts are not.

## Supported paths

### Prompt-only use

Load the relevant `skills/<name>/SKILL.md` and its referenced resources. When
copying or importing a skill, preserve the complete `skills/<name>/` directory,
including any `references/`, `assets/`, scripts, and optional UI metadata. A copy
of `SKILL.md` alone can omit instructions required by that skill.

In a native installation, resolve relative references from the installed skill
folder. Through a remote connector such as Agensi, retrieve the referenced text
through that connector; archive paths do not imply a local checkout. The host
must provide the source access and tools the task needs. See the
[delivery routes](agensi-distribution.md#choose-the-delivery-route) for Agensi
and ChatGPT environments with native personal-skill support.

### OpenCode and Pi helper installer

The provided installer is currently **tested on Ubuntu/Linux and WSL** through repository CI and local development.

It assumes a Unix-like environment with:

- Bash;
- Git;
- standard Unix/GNU filesystem utilities such as `ln`, `mv`, `readlink`, and `realpath`;
- symlink support;
- Node.js for installation/removal ownership checks and repository validation scripts;
- OpenCode and/or Pi only when you intend to use those runtime integrations.

Scoped OpenCode session checks use the `sqlite3` CLI to inspect the native
timeline; export-only checks support explicit whole-session scope. The local
OpenCode regression suite also uses Python 3's standard-library SQLite driver
for disposable database fixtures.

The helper installer is not currently claimed as native macOS or native Windows support. On those platforms, use the Markdown prompts directly or adapt the install locations for your host.

## Runtime versions

Release names alone do not establish compatibility. These are the concrete
boundaries inspected on 2026-10-30:

| Component | Evidence and integration status |
| --- | --- |
| OpenCode 1.19.5 (`opencode-ai`) | Official binary and SDK used for full preflight with artifacts off/on, all 12 agent tool sets/85 skills, and native artifact write/read plus denial controls. The adapter targets the 1.x API. A complete model-backed review flow was not run. |
| OpenCode 2.2.4 (`@opencode/cli`) | Latest 2.x source checked; 2.2.3 binary probed. The plugin API and CLI differ. Full cookbook preflight rejects 2.x until a native port and qualification exist. Portable skill Markdown remains usable. |
| Pi 1.4.0 (`@earendil-works/pi-coding-agent`) | Real extension loader and native permission/delegation helpers exercised in an isolated installation. Requires Node.js >=22.19.0. This evidence does not include a model-backed child session. |
| `pi-open-agents` 0.1.26 | Concrete integration baseline after the lifecycle and delegation fixes. Pin it explicitly for this flow; run preflight against the actual installation. |
| `pi-open-agents` 0.1.27 | Native inherited tool ceiling and rule composition block this cookbook's deny-by-default reviewer flow. Preflight rejects it. Later versions require fresh compatibility evidence. |

The installer links cookbook files; it does not install, downgrade, or update
your runtimes or third-party packages. For a Pi installation selected by the
operator, the native package command is:

```bash
pi install npm:pi-open-agents@0.1.26
```

Pi package declarations belong in native `settings.json` under `packages`, for
example `"packages": ["npm:pi-open-agents@0.1.26"]`. The `extensions` setting is
for local resources; placing an npm declaration there does not prove the package
will load. Keep model/provider and unrelated settings in their existing host
configuration.

The exact source revisions, reproduced failures, fixes, and evidence limits are
recorded in the [runtime compatibility review](runtime-compatibility-review-2026-10-30.md).
The [local runtime qualification guide](local-runtime-qualification.md) separates
installation/preflight from successful session evidence. Native Pi parent
`tools[].status: "done"` records do not encode a tool's successful outcome;
full session qualification needs actual child result evidence when those logs
cannot prove it.

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

The helper installs:

- canonical agent Markdown files into OpenCode and Pi agent locations;
- canonical skill directories into the shared skill location;
- a small real OpenCode plugin entry that imports the host's SDK and delegates to the canonical review-artifact adapter;
- the narrow Pi review-artifact extension.

The canonical files remain in the cloned repository. Agents, skills and the Pi
adapter are linked. The four-line OpenCode entry contains only import/registration
wiring; behavior remains in the canonical adapter. A symlink for that entry
would resolve the SDK from the checkout instead of OpenCode's dependency
directory. Installation migrates the known former plugin symlink and verifies
the exact generated bytes. A user-modified entry is a conflict; `--force` backs
it up before replacement.

The installer does not install the host itself or Pi's `pi-open-agents` package.
For the optional Pi agent roles and full review flows, install and enable
`pi-open-agents` through Pi's normal package workflow before running the Pi
preflight. See [Pi adapter responsibilities](../adapters/pi/README.md) and
[local runtime prerequisites](local-runtime-qualification.md#host-compatibility-and-context-selection).
The preflight checks the applicable runtime/package requirements. Loading a
standalone skill does not require the full-flow integration.

## Removing the cookbook

Use the repository-provided uninstaller with the same destination options used for installation:

```bash
scripts/unlink-opencode-local.sh
# If custom destinations were used:
scripts/unlink-opencode-local.sh --global-dir DIR --pi-agent-dir DIR --shared-skill-dir DIR
```

The uninstaller removes the exact unmodified generated OpenCode entry and
recognized cookbook-owned links, including retired names whose source has been
deleted. Link ownership requires a target in this checkout's same-named
canonical or known legacy source. It preserves modified native entries, unrelated files, links
from other checkouts, and custom aliases. Run it before deleting or moving your
cookbook checkout so it can still identify the links it owns. Do not recursively
delete an OpenCode/Pi configuration directory that may contain unrelated user content.

If you installed with `--force`, the installer may have created timestamped backup paths beside previous conflicts. Those backups are intentionally never deleted automatically; restore or remove them manually after verifying their contents.

## Updating

Because runtime locations link to the clone, updating the checked-out repository changes the prompt content visible to supported hosts.

After changing the checkout revision, rerun `scripts/link-opencode-local.sh` with
the same destination options. This installs new names and removes retired links
owned by that checkout, after verifying the current links. Use `--dry-run` to
inspect reconciliation. Reload or restart the selected host so it discovers the
updated definitions.

For reproducible use, pin the clone to a known commit or tag rather than automatically tracking `main`.

These steps maintain the native OpenCode/Pi installation. Agensi listings and native personal-skill copies follow their own update workflows; changing the checkout does not update those copies.

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
node --test scripts/test-*.js
node scripts/check-pi-reviewer-boundary.js
```

For the optional Ping-Pong/Ping-Ping full review flows, run the preflight for
the host you intend to use:

| Selected host | Preflight |
| --- | --- |
| OpenCode | `scripts/preflight-opencode-ping-pong.sh` |
| Pi with `pi-open-agents` enabled | `scripts/preflight-pi-ping-pong.sh` |

These full-flow checks are not prerequisites for loading an individual skill.

These preflight scripts verify repository/runtime contracts; they do not make general guarantees about your model server, operating system, or third-party host implementation.

Benchmark execution, the behavioral evaluation corpus, and Agent Economics tooling are maintained separately in [EvalShot](https://github.com/Hugloss/EvalShot). They are not prerequisites for installing or using the cookbook. For model-backed benchmark evaluation of skills, see [EvalShot's evaluation guide](https://github.com/Hugloss/EvalShot/blob/main/evals/README.md). For runtime/profile promotion, follow [local runtime qualification](local-runtime-qualification.md). Ordinary contribution checks follow [evaluation ownership and evidence](../CONTRIBUTING.md#evaluation-ownership-and-evidence).
