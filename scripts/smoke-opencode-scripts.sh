#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/.." && pwd -P)"
# shellcheck source=scripts/lib-opencode.sh
. "$script_dir/lib-opencode.sh"

pass() { printf 'SMOKE name=%s status=pass %s\n' "$1" "${2:-}"; }
fail() { printf 'SMOKE name=%s status=fail %s\n' "$1" "${2:-}" >&2; exit 1; }

assert_link() {
  local name="$1" path="$2" expected="$3" resolved
  [ -L "$path" ] || fail "$name" "missing=$path"
  resolved="$(realpath -- "$path" 2>/dev/null || true)"
  [ "$resolved" = "$expected" ] || fail "$name" "resolved=${resolved:-<unresolved>} expected=$expected"
  pass "$name"
}

temp_root="$(mktemp -d "${TMPDIR:-/tmp}/agents-cookbook-smoke.XXXXXX")"
cleanup() { rm -rf "$temp_root"; }
trap cleanup EXIT

global_dir="$temp_root/global opencode"
pi_dir="$temp_root/pi agent"
skills_dir="$temp_root/shared skills"
target_dir="$temp_root/target repo"
mkdir -p "$target_dir" "$global_dir/agents" "$skills_dir" "$temp_root/bin"

# Simulate links created by the retired repository layout. Migration must
# replace only cookbook-owned links and must not require --force.
ln -s "$repo_root/.opencode/agents/ping-pong-plan.md" "$global_dir/agents/ping-pong-plan.md"
ln -s "$repo_root/.agents/skills/plan-improvement-scout" "$skills_dir/plan-improvement-scout"

"$repo_root/scripts/link-opencode-local.sh" --dry-run --global-dir "$global_dir" --pi-agent-dir "$pi_dir" --shared-skill-dir "$skills_dir" >/dev/null
pass link_dry_run
"$repo_root/scripts/link-opencode-local.sh" --global-dir "$global_dir" --pi-agent-dir "$pi_dir" --shared-skill-dir "$skills_dir" >/dev/null

assert_link opencode_primary "$global_dir/agents/ping-pong-plan.md" "$repo_root/agents/ping-pong-plan.md"
assert_link opencode_reviewer "$global_dir/agents/plan-coverage-reviewer.md" "$repo_root/agents/plan-coverage-reviewer.md"
assert_link opencode_standalone "$global_dir/agents/code-performance-optimization-auditor.md" "$repo_root/agents/code-performance-optimization-auditor.md"
assert_link pi_primary "$pi_dir/agents/ping-ping-build.md" "$repo_root/agents/ping-ping-build.md"
assert_link pi_reviewer "$pi_dir/agents/plan-contract-checker.md" "$repo_root/agents/plan-contract-checker.md"
assert_link shared_skill "$skills_dir/plan-improvement-scout" "$repo_root/skills/plan-improvement-scout"
assert_link performance_skill "$skills_dir/code-performance-optimization-audit" "$repo_root/skills/code-performance-optimization-audit"

"$repo_root/scripts/preflight-opencode-ping-pong.sh" --quick --global-dir "$global_dir" --shared-skill-dir "$skills_dir" "$target_dir" >/dev/null
pass opencode_quick_preflight

# Deterministic Pi/plugin fixture.
mkdir -p "$pi_dir/npm/node_modules/pi-open-agents"
printf '{"version":"0.1.20"}\n' >"$pi_dir/npm/node_modules/pi-open-agents/package.json"
printf '{"extensions":["npm:pi-open-agents@0.1.20"]}\n' >"$pi_dir/settings.json"
printf '#!/usr/bin/env bash\nprintf "pi 0.85.0\\n"\n' >"$temp_root/bin/pi"
chmod +x "$temp_root/bin/pi"
PATH="$temp_root/bin:$PATH" "$repo_root/scripts/preflight-pi-ping-pong.sh" --pi-agent-dir "$pi_dir" --shared-skill-dir "$skills_dir" "$target_dir" >/dev/null
pass pi_preflight

"$repo_root/scripts/link-opencode-local.sh" --global-dir "$global_dir" --pi-agent-dir "$pi_dir" --shared-skill-dir "$skills_dir" | grep 'status=already_correct' >/dev/null
pass link_idempotent

# Unrelated user paths remain protected.
force_dir="$temp_root/force"
mkdir -p "$force_dir/agents"
printf 'conflict\n' >"$force_dir/agents/ping-pong-plan.md"
if "$repo_root/scripts/link-opencode-local.sh" --global-dir "$force_dir" --pi-agent-dir "$temp_root/force-pi" --shared-skill-dir "$temp_root/force-skills" >/dev/null 2>&1; then fail conflict_without_force; fi
pass conflict_without_force
"$repo_root/scripts/link-opencode-local.sh" --force --global-dir "$force_dir" --pi-agent-dir "$temp_root/force-pi" --shared-skill-dir "$temp_root/force-skills" >/dev/null
find "$force_dir/agents" -name 'ping-pong-plan.md.agents-cookbook-backup-*' -print -quit | grep . >/dev/null
pass force_backup

# Registry invariants: 12 installable agents, 8 skills, exactly 8 flow reviewers.
[ "$(printf '%s\n' $AC_AGENT_FILES | sed '/^$/d' | wc -l)" -eq 12 ] || fail agent_registry_count
[ "$(printf '%s\n' $AC_SKILL_NAMES | sed '/^$/d' | wc -l)" -eq 8 ] || fail skill_registry_count
[ "$(printf '%s\n' $AC_FLOW_REVIEWER_AGENT_FILES | sed '/^$/d' | wc -l)" -eq 8 ] || fail flow_reviewer_count
! printf '%s\n' $AC_FLOW_REVIEWER_AGENT_FILES | grep -qx 'code-performance-optimization-auditor.md' || fail standalone_leaked_into_flow_gate
pass registry_boundaries

# Script syntax remains valid even when OpenCode itself is unavailable.
for script in "$repo_root"/scripts/*.sh; do bash -n "$script"; done
node --check "$repo_root/scripts/check-pi-session.js"
node --check "$repo_root/scripts/run-opencode-benchmarks.js"
pass script_syntax

# Unlink removes only owned links.
rm -- "$global_dir/agents/ping-pong-plan.md"
printf 'user file\n' >"$global_dir/agents/ping-pong-plan.md"
ln -s "$temp_root" "$global_dir/agents/unrelated.md"
"$repo_root/scripts/unlink-opencode-local.sh" --global-dir "$global_dir" --pi-agent-dir "$pi_dir" --shared-skill-dir "$skills_dir" >/dev/null
[ -f "$global_dir/agents/ping-pong-plan.md" ] || fail unlink_preserves_real_file
[ -L "$global_dir/agents/unrelated.md" ] || fail unlink_preserves_unrelated_link
[ ! -e "$pi_dir/agents/plan-contract-checker.md" ] && [ ! -L "$pi_dir/agents/plan-contract-checker.md" ] || fail unlink_removes_pi_agent
[ ! -e "$skills_dir/plan-improvement-scout" ] && [ ! -L "$skills_dir/plan-improvement-scout" ] || fail unlink_removes_shared_skill
pass unlink_safe

printf 'SUMMARY status=pass agents=12 skills=8 mandatory_flow_reviewers=8\n'
