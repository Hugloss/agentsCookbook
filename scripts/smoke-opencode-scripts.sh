#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/.." && pwd -P)"

pass() {
  printf 'SMOKE name=%s status=pass %s\n' "$1" "${2:-}"
}

fail() {
  printf 'SMOKE name=%s status=fail %s\n' "$1" "${2:-}" >&2
  exit 1
}

assert_symlink_target() {
  local name="$1"
  local path="$2"
  local expected="$3"
  local resolved

  [ -L "$path" ] || fail "$name" "path=$path expected_symlink=true"
  resolved="$(realpath -- "$path" 2>/dev/null || true)"
  [ "$resolved" = "$expected" ] || fail "$name" "path=$path resolved=${resolved:-<unresolved>} expected=$expected"
  pass "$name" "path=$path"
}

write_target_config() {
  local path="$1"
  local prompt_base="$2"
  node -e '
const fs = require("fs");
const path = process.argv[1];
const promptBase = process.argv[2];
const mapping = [
  ["plan-improver-model2", "plan-improver.md"],
  ["plan-improver-model3", "plan-improver.md"],
  ["plan-validation-designer", "plan-validation-designer.md"],
  ["plan-red-team-gate", "plan-red-team-gate.md"],
  ["plan-implementation-simulator", "plan-implementation-simulator.md"],
  ["plan-fact-auditor", "plan-fact-auditor.md"],
  ["plan-contract-checker", "plan-contract-checker.md"],
];
const agent = {};
for (const [name, promptFile] of mapping) {
  agent[name] = {
    mode: "subagent",
    prompt: `{file:${promptBase}/${promptFile}}`,
    permission: {
      edit: "deny",
      bash: "deny",
      task: "deny",
      read: "allow",
      grep: "allow",
      glob: "allow",
      list: "allow",
    },
  };
}
fs.writeFileSync(path, JSON.stringify({ agent }, null, 2) + "\n");
' "$path" "$prompt_base"
}

temp_root="$(mktemp -d "${TMPDIR:-/tmp}/agents-cookbook-smoke.XXXXXX")"
cleanup() {
  rm -rf "$temp_root"
}
trap cleanup EXIT

global_dir="$temp_root/global opencode"
target_dir="$temp_root/target repo"
mkdir -p "$target_dir"

"$repo_root/scripts/link-opencode-local.sh" --dry-run --global-dir "$global_dir" >/dev/null
pass "link_dry_run"

"$repo_root/scripts/link-opencode-local.sh" --global-dir "$global_dir" >/dev/null
assert_symlink_target "agent_ping_pong_plan_link" "$global_dir/agents/ping-pong-plan.md" "$repo_root/.opencode/agents/ping-pong-plan.md"
assert_symlink_target "agent_ping_ping_build_link" "$global_dir/agents/ping-ping-build.md" "$repo_root/.opencode/agents/ping-ping-build.md"
assert_symlink_target "prompt_plan_improver_link" "$global_dir/prompts/plan-improver.md" "$repo_root/.opencode/prompts/plan-improver.md"

"$repo_root/scripts/link-opencode-local.sh" --global-dir "$global_dir" | grep 'status=already_correct' >/dev/null
pass "link_idempotent"

[ ! -e "$target_dir/.opencode" ] || fail "target_prompts_not_copied" "unexpected_path=$target_dir/.opencode"
[ ! -e "$target_dir/opencode.json" ] || fail "link_did_not_create_target_config" "unexpected_path=$target_dir/opencode.json"
pass "link_does_not_touch_target_repo"

if "$repo_root/scripts/preflight-opencode-ping-pong.sh" --quick --global-dir "$global_dir" --prompt-base "$global_dir/prompts" "$target_dir" >/dev/null 2>&1; then
  fail "preflight_missing_config_fails" "unexpected_pass=true"
fi
pass "preflight_missing_config_fails"

write_target_config "$target_dir/opencode.json" "$global_dir/prompts"
"$repo_root/scripts/preflight-opencode-ping-pong.sh" --quick --global-dir "$global_dir" --prompt-base "$global_dir/prompts" "$target_dir" >/dev/null
pass "preflight_quick_valid_config"

force_global="$temp_root/force global"
mkdir -p "$force_global/agents"
printf 'conflict\n' >"$force_global/agents/ping-pong-plan.md"
if "$repo_root/scripts/link-opencode-local.sh" --global-dir "$force_global" >/dev/null 2>&1; then
  fail "link_conflict_without_force_fails" "unexpected_pass=true"
fi
pass "link_conflict_without_force_fails"
"$repo_root/scripts/link-opencode-local.sh" --force --global-dir "$force_global" >/dev/null
assert_symlink_target "link_force_replaces_conflict" "$force_global/agents/ping-pong-plan.md" "$repo_root/.opencode/agents/ping-pong-plan.md"
find "$force_global/agents" -name 'ping-pong-plan.md.agents-cookbook-backup-*' -print -quit | grep . >/dev/null
pass "link_force_backup_created"

unlink_global="$temp_root/unlink global"
"$repo_root/scripts/link-opencode-local.sh" --global-dir "$unlink_global" >/dev/null
rm -- "$unlink_global/agents/ping-pong-plan.md"
printf 'real file\n' >"$unlink_global/agents/ping-pong-plan.md"
ln -s -- "$temp_root" "$unlink_global/prompts/unrelated.md"
"$repo_root/scripts/unlink-opencode-local.sh" --global-dir "$unlink_global" >/dev/null
[ -f "$unlink_global/agents/ping-pong-plan.md" ] || fail "unlink_preserves_real_file"
[ -L "$unlink_global/prompts/unrelated.md" ] || fail "unlink_preserves_unrelated_symlink"
[ ! -e "$unlink_global/agents/ping-ping-build.md" ] && [ ! -L "$unlink_global/agents/ping-ping-build.md" ] || fail "unlink_removes_cookbook_agent"
pass "unlink_preserves_unrelated_paths"

"$repo_root/scripts/unlink-opencode-local.sh" --global-dir "$unlink_global" >/dev/null
pass "unlink_idempotent"

printf 'SUMMARY status=pass temp_root=%s\n' "$temp_root"
