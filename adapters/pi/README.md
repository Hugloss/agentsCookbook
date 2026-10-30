# Pi Adapter

The repository source of truth is `agents/` and `skills/`.

Pi uses the same canonical agent files through `pi-open-agents`. `scripts/link-opencode-local.sh` links agents into the configured Pi agent directory, skills into the shared skill directory, and this adapter directory into the Pi extensions directory. Pi discovers `index.js`; the adapter and its `reviewer-tool-boundary.js` helper remain together so relative imports resolve.

Do not maintain Pi-specific behavioral copies unless a proven runtime incompatibility requires one. Runtime differences belong in adapters/install/preflight logic.

## Checked host profile

The model-free compatibility check on 2026-10-30 used **`@earendil-works/pi-coding-agent` 1.4.0 + `pi-open-agents` 0.1.26**. It loaded the real extension through Pi's published loader, executed native permission/delegation helpers with child process execution replaced by a capture function, read a real skill with Pi's native `read` tool, and wrote/read an artifact. It made no model requests and did not launch a child Pi. A model-backed local flow is still required before claiming deployment qualification.

`pi-open-agents` 0.1.27 is incompatible with this composition: its native delegation ceiling discards all explicitly allowed tools when the parent has a wildcard deny, and its inherited deny rule blocks child allowances. The parent also does not own the reviewer-only artifact sink, so granting that sink through an inherited parent ceiling needs native support. The cookbook does not bypass either native restriction. Preflight accepts only the checked pair and reports other versions for compatibility review; this does not restrict using the standalone skill prompts.

The npm host identity is `@earendil-works/pi-coding-agent`; its 1.4.0 package requires Node >=22.19.0. The legacy `@mariozechner/pi-coding-agent` package is a different release line. Configure the extension using Pi's native package declaration, for example:

```json
{
  "packages": ["npm:pi-open-agents@0.1.26"]
}
```

Pi also accepts package objects such as `{ "source": "npm:pi-open-agents@0.1.26" }`. `extensions: ["npm:pi-open-agents@0.1.26"]` is not an npm package declaration in this host. Preflight follows project package precedence, recognizes the unfiltered object form and an exact `index.ts` filter, and reports disabled/other filtered declarations as unverified instead of claiming they are loaded. Pi remains the authority for project trust and resource resolution.

Primary agents explicitly grant Pi's `subagent` tool. OpenCode's `task` permission does not grant that native Pi name. The existing `allowedAgents` list restricts the called agent to the exact nine reviewers, and native `maxDepth` prevents reviewer delegation; the native compatibility probe exercises those restrictions.

Sources: [Pi 1.4.0 loader](https://github.com/earendil-works/pi/blob/v1.4.0/packages/coding-agent/src/core/extensions/loader.ts), [Pi package configuration](https://github.com/earendil-works/pi/blob/v1.4.0/packages/coding-agent/docs/packages.md), [pi-open-agents 0.1.26 delegation](https://github.com/andrea-tomassi/pi-open-agents/blob/e86a547af7c37f7c991a952159d2e65f4f495fd9/src/subagent/tool.ts), and [0.1.27 inheritance](https://github.com/andrea-tomassi/pi-open-agents/blob/725a1ff17ed449cdfc86ceb9f2f37637a2a5a8ff/src/subagent/tool.ts).

## Reviewer child authority boundary

Canonical reviewer agents use OpenCode-compatible wildcard deny-by-default permissions:

```yaml
permission:
  "*": deny
  read: allow
  grep: allow
  find: allow
  ls: allow
  review_artifact: allow
```

The checked `pi-open-agents` 0.1.26 cannot derive a finite child-process `--tools` whitelist from any permission block containing `*`, including `"*": deny`. Without an adapter boundary, that runtime limitation can leave all child tools visible even though the canonical policy is deny-by-default.

The Pi adapter closes that runtime-specific gap using the authoritative child identity in `PI_OPEN_AGENTS_NAME` + `PI_OPEN_AGENTS_DEPTH`:

- only the nine cookbook reviewer identities are affected;
- normal reviewer children get exactly `read`, `grep`, `find`, and `ls` as active tools;
- artifact-backed reviewer children additionally get `review_artifact`;
- `bash`, `powershell`, `edit`, `write`, delegation, and `review_artifact_read` are excluded;
- a `tool_call` hook independently blocks any out-of-policy tool call as defense-in-depth;
- the active tool set is applied on `session_start`, after Pi binds runtime actions, including reload/resume; the extension factory only registers tools and hooks;
- primary Pi sessions are not classified as reviewer children and keep their own canonical authority.

This is adapter enforcement, not a second behavioral agent definition. `agents/*.md` remains the single source of reviewer intent and methodology.

## Optional artifact-backed review mode

Artifact tools are registered only when `AGENTS_COOKBOOK_RUN_DIR` is set to an **absolute per-run directory** before Pi starts. The reviewer child tool boundary above is active regardless of artifact mode.

Example:

```bash
export AGENTS_COOKBOOK_RUN_DIR="$PWD/.runs/$(date +%Y%m%d-%H%M%S)"
pi
```

When enabled:

- delegated reviewer children register only the bounded `review_artifact` sink and never `review_artifact_read`;
- the top-level Pi process registers only `review_artifact_read`; it never registers the reviewer write sink;
- only the nine known cookbook reviewer artifact IDs are accepted;
- the extension accepts no arbitrary filesystem path from the model;
- reports are confined to `reviews/` and deterministic receipts to `receipts/` under the configured run root;
- artifact IDs are bound to the active reviewer child identity and cannot overwrite existing reports;
- reviewers return a <=1200-character material-finding summary/receipt while the full Markdown remains in the run store;
- primary agents read a full named report only when its compact summary is insufficient.

Before returning a stored report, the reader validates its matching receipt: Pi runtime, schema, run and reviewer identity, fixed artifact path, exact SHA-256 and character count, and a nonempty bounded summary. Both the report and receipt must remain inside their configured directories. Missing, modified, mismatched, or escaped artifacts fail the read.

A reviewer remains standalone in Pi even when invoked directly rather than as a child. Direct/top-level standalone invocation returns the full review normally. For a one-reviewer Pi run that also needs live low-context persistence, invoke the reviewer through `subagent-router` so it runs behind the delegated reviewer boundary.

Leave `AGENTS_COOKBOOK_RUN_DIR` unset for normal standalone behavior where reviewers return full review artifacts directly; the finite reviewer child tool boundary still applies to delegated reviewers.

`preflight-pi-ping-pong.sh` checks the host pair, native npm declaration, canonical contracts, adapter links, exact nine-review flow allowlists, and agent discovery collisions. Discovery includes `.pi/agents`, all four `.opencode/{agent,agents,mode,modes}` directories, `.agents/agents`, nested filename identities, and explicit frontmatter names. Global Pi aliases are checked; lower-priority global OpenCode definitions cannot replace canonical global Pi agents.

`scripts/check-pi-reviewer-boundary.js` executes unchanged adapter code with a lifecycle-faithful host test double and a TypeBox schema-construction stub. It checks role separation, factory-time action rejection, session-start reapplication, tool blocking, and receipt integrity. To check actual installed packages without a model call, run:

```bash
node scripts/check-pi-native-compatibility.js \
  --pi-package /absolute/path/to/node_modules/@earendil-works/pi-coding-agent \
  --open-agents-package /absolute/path/to/pi-open-agents
```

The probe requires supplied package directories and their dependencies; it never installs them or changes native user settings. A successful static preflight or native probe does not claim that a model-backed review flow ran. Follow [local runtime qualification](../../docs/local-runtime-qualification.md) for that evidence.
