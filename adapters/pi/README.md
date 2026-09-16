# Pi Adapter

The repository source of truth is `agents/` and `skills/`.

Pi uses the same canonical agent files through `pi-open-agents`. `scripts/link-opencode-local.sh` links agents into the configured Pi agent directory, skills into the shared skill directory, and `review-artifact.js` into the Pi extensions directory.

Do not maintain Pi-specific behavioral copies unless a proven runtime incompatibility requires one. Runtime differences belong in adapters/install/preflight logic.

## Optional artifact-backed review mode

The installed extension registers no artifact tools unless `AGENTS_COOKBOOK_RUN_DIR` is set to an **absolute per-run directory** before Pi starts.

Example:

```bash
export AGENTS_COOKBOOK_RUN_DIR="$PWD/.runs/$(date +%Y%m%d-%H%M%S)"
pi
```

When enabled:

- reviewer permission allow-lists include `review_artifact` but not `review_artifact_read`;
- primary agents include `review_artifact_read` but not `review_artifact`;
- the extension accepts no arbitrary filesystem path from the model;
- reports are confined to `reviews/` and deterministic receipts to `receipts/` under the configured run root;
- artifact IDs cannot overwrite existing reports;
- reviewers return a <=1200-character material-finding summary/receipt while the full Markdown remains in the run store;
- primary agents read a full named report only when its compact summary is insufficient.

Leave `AGENTS_COOKBOOK_RUN_DIR` unset for normal standalone behavior where reviewers return full review artifacts directly.

`preflight-pi-ping-pong.sh` validates Pi version, `pi-open-agents`, exact eight-review flow permissions, deny-by-default reviewer contracts, the artifact extension link, and project-local shadowing risks. Live artifact-tool execution remains a runtime qualification step because it depends on the installed Pi environment.
