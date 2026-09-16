# Pi Adapter

The repository source of truth is `agents/` and `skills/`.

Pi uses the same canonical agent files through `pi-open-agents`. `scripts/link-opencode-local.sh` links agents into the configured Pi agent directory, skills into the shared skill directory, and this adapter directory into the Pi extensions directory. Pi discovers `index.js`; the adapter and its `reviewer-tool-boundary.js` helper remain together so relative imports resolve.

Do not maintain Pi-specific behavioral copies unless a proven runtime incompatibility requires one. Runtime differences belong in adapters/install/preflight logic.

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

Current `pi-open-agents` cannot derive a finite child-process `--tools` whitelist from any permission block containing `*`, including `"*": deny`. Without an adapter boundary, that runtime limitation can leave all child tools visible even though the canonical policy is deny-by-default.

The Pi adapter closes that runtime-specific gap using the authoritative child identity in `PI_OPEN_AGENTS_NAME` + `PI_OPEN_AGENTS_DEPTH`:

- only the nine cookbook reviewer identities are affected (eight flow reviewers plus the standalone performance auditor);
- normal reviewer children get exactly `read`, `grep`, `find`, and `ls` as active tools;
- artifact-backed reviewer children additionally get `review_artifact`;
- `bash`, `powershell`, `edit`, `write`, delegation, and `review_artifact_read` are excluded;
- a `tool_call` hook independently blocks any out-of-policy tool call as defense-in-depth;
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

A reviewer remains standalone in Pi even when invoked directly rather than as a child. Direct/top-level standalone invocation returns the full review normally. For a one-reviewer Pi run that also needs live low-context persistence, invoke the reviewer through `subagent-router` so it runs behind the delegated reviewer boundary.

Leave `AGENTS_COOKBOOK_RUN_DIR` unset for normal standalone behavior where reviewers return full review artifacts directly; the finite reviewer child tool boundary still applies to delegated reviewers.

`preflight-pi-ping-pong.sh` validates Pi version, compatible `pi-open-agents`, canonical contracts, adapter links, exact eight-review flow allowlists, and project-local shadowing. `scripts/check-pi-reviewer-boundary.js` separately gates the finite reviewer identity/tool set, role-separated artifact tools, known artifact IDs, session-start reapplication, and the execution blocker. Real model-backed execution remains a local runtime qualification step.
