# Pi Adapter

The repository source of truth is `agents/` and `skills/`.

Pi uses the same canonical agent files through `pi-open-agents`; `scripts/link-opencode-local.sh` links them into the configured Pi agent directory and installs the same skills into the shared skill directory.

Do not maintain Pi-specific behavioral copies unless a proven runtime incompatibility requires one. Runtime-specific differences belong in adapter/install/preflight logic, not duplicated capability prompts.

`preflight-pi-ping-pong.sh` validates Pi version, `pi-open-agents`, exact eight-review flow permissions, standalone reviewer contracts, links, and project-local shadowing risks.
