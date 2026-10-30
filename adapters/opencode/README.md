# OpenCode Adapter

The repository source of truth is `agents/` and `skills/`. OpenCode runtime discovery paths are deployment details.

`scripts/link-opencode-local.sh` installs:

- links to canonical agents in the configured OpenCode agent directory;
- links to canonical skills in the shared skill directory;
- a small native entrypoint in the OpenCode plugin directory, which imports the canonical `review-artifact.js` implementation.

The real entrypoint resolves `@opencode-ai/plugin` from OpenCode's own configuration
dependencies and passes its tool factory to the canonical implementation. A direct
symlink to that implementation resolves bare dependencies at the cookbook checkout
and fails to register tools in native 1.19.5. Relinking migrates the known old
symlink. Installer, preflight and uninstall verify the generated entrypoint's exact
content before treating it as cookbook-owned.

Edit canonical sources rather than installed runtime files, and keep `agents/` as
the source tree.

## Runtime compatibility

This adapter targets **OpenCode 1.x** (`opencode-ai` and `@opencode-ai/plugin`).
Model-free native probes were run against **1.19.5**. Full preflight checks the
selected CLI version and its effective agent/tool/skill contracts; a major-version
match alone does not qualify a host/model profile.

OpenCode 2 uses `@opencode/cli` and `@opencode/plugin`, changes the debug/session
interfaces, and explicitly does not execute V1 plugin implementations. See the
[official V2 migration guide](https://github.com/anomalyco/opencode/blob/v2.2.4/services/www/src/docs/content/migrate-v1.mdx).
The cookbook full-flow preflight and CLI-backed session checks fail with an
actionable message for V2 instead of trying V1 commands or guessing equivalent
permissions. Canonical standalone skills remain usable independently of this
adapter. A V2 port must validate native tool-context identity, permissions, plugin
registration, service environment ownership, and session-result evidence together.

Canonical primaries include Pi's `subagent` permission because the prompts are
shared across hosts. OpenCode V1 delegates through `task`; full preflight rejects
an enabled external `subagent` tool or any other unexpected enabled tool. This
keeps an unrelated plugin from gaining delegation authority through that alias.

## Optional artifact-backed review mode

The installed plugin registers no artifact tools unless `AGENTS_COOKBOOK_RUN_DIR` is set to an **absolute per-run directory** before OpenCode starts.

Example:

```bash
export AGENTS_COOKBOOK_RUN_DIR="$PWD/.runs/$(date +%Y%m%d-%H%M%S)"
opencode
```

When enabled:

- reviewer agents may call only `review_artifact` in addition to their read/skill tools;
- primary agents may call `review_artifact_read` but cannot call `review_artifact`;
- `review_artifact` accepts an artifact ID, compact summary, full Markdown report, and optional subject metadata—never a filesystem path;
- artifacts are confined to `reviews/` and `receipts/` under the configured run root;
- existing artifact IDs cannot be overwritten;
- only the nine known cookbook reviewer artifact IDs are accepted;
- OpenCode tool context must identify one of those reviewer agents before `review_artifact` can write, and the artifact ID must equal that reviewer identity;
- `review_artifact_read` additionally checks tool context and executes only for `ping-pong-plan`, `ping-ping-build`, or `subagent-router`;
- before returning report text, the reader verifies the confined receipt path, schema, runtime, run-directory ID, reviewer/artifact identity, summary bounds, exact character count, and SHA-256 of the report;
- primary agents use the <=1200-character receipt summary by default and selectively read a full named report only when needed.

These execution-time identity checks are defense-in-depth. They remain effective even if a future permission or tool-visibility regression exposes the wrong custom tool.

Leave `AGENTS_COOKBOOK_RUN_DIR` unset for the normal standalone behavior where reviewers return their full skill-defined artifact directly.

`preflight-opencode-ping-pong.sh` validates source/link contracts in `--quick` mode
and effective OpenCode tool permissions in full mode. Quick mode does not inspect
the installed runtime. The canonical source gate additionally checks the artifact
role-binding contract.

`check-opencode-session.sh` requires structured native evidence and completed,
nonempty reviewer results. Failed, pending, empty, malformed, foreign-session or
background-launch records do not qualify. Scoped checks need the SQLite timeline;
an export-only check supports `--scope session` and never substitutes a text scan
for missing evidence. Automatic session selection stays within the current
directory. These checks establish transport and invocation evidence; model-backed
review quality remains part of [local runtime qualification](../../docs/local-runtime-qualification.md).
