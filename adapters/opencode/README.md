# OpenCode Adapter

The repository source of truth is `agents/` and `skills/`.

OpenCode's runtime discovery layout is an adapter concern. `scripts/link-opencode-local.sh` links canonical agents into the configured OpenCode agent directory and canonical skills into the shared skill directory used by both runtimes.

Do not hand-edit generated/linked runtime copies and do not reintroduce `.opencode/agents` as a second source tree.

`preflight-opencode-ping-pong.sh` validates the effective OpenCode tool/permission contract when OpenCode is available and performs source/link checks in `--quick` mode.
