# OpenCode Adapter

The repository source of truth is `agents/` and `skills/`. OpenCode runtime discovery paths are deployment details.

`scripts/link-opencode-local.sh` links:

- canonical agents into the configured OpenCode agent directory;
- canonical skills into the shared skill directory;
- `review-artifact.js` into the OpenCode plugin directory.

Do not hand-edit linked runtime copies or reintroduce `.opencode/agents` as a second source tree.

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
- the OpenCode adapter binds a reviewer artifact ID to the current agent identity when that identity is available in tool context;
- primary agents use the <=1200-character receipt summary by default and selectively read a full named report only when needed.

Leave `AGENTS_COOKBOOK_RUN_DIR` unset for the normal standalone behavior where reviewers return their full skill-defined artifact directly.

`preflight-opencode-ping-pong.sh` validates source/link contracts in `--quick` mode and effective OpenCode tool permissions in full mode. In artifact mode it also requires the correct reviewer-write / primary-read tool split.
