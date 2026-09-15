#!/usr/bin/env bash
set -u

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-opencode.sh
. "$script_dir/lib-opencode.sh"

usage() {
  cat <<'USAGE'
Usage: scripts/preflight-pi-ping-pong.sh [--pi-agent-dir DIR] [--shared-skill-dir DIR] [target-repo]

Read-only checks for Pi 0.85.0+, pi-open-agents 0.1.20, all eleven agent
links, all seven shared skills, and project files that could shadow them.
USAGE
}

failures=0
pi_agent_dir_arg=""
shared_skill_dir_arg=""
target_repo=""
pass() { printf 'CHECK name=%s status=pass %s\n' "$1" "${2:-}"; }
fail() { failures=$((failures + 1)); printf 'CHECK name=%s status=fail %s\n' "$1" "${2:-}"; }

while [ "$#" -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --pi-agent-dir) shift; [ "$#" -gt 0 ] || ac_die "--pi-agent-dir requires a directory argument"; pi_agent_dir_arg="$1" ;;
    --shared-skill-dir) shift; [ "$#" -gt 0 ] || ac_die "--shared-skill-dir requires a directory argument"; shared_skill_dir_arg="$1" ;;
    --*) usage >&2; ac_die "unknown option: $1" ;;
    *) [ -z "$target_repo" ] || ac_die "only one target repo may be supplied"; target_repo="$1" ;;
  esac
  shift
done

repo_root="$(ac_repo_root_from_script "${BASH_SOURCE[0]}")"
target_repo="$(ac_absolute_path "${target_repo:-$PWD}")"
if [ -n "$pi_agent_dir_arg" ]; then pi_agent_dir="$(ac_absolute_path "$pi_agent_dir_arg")"; elif ! pi_agent_dir="$(ac_default_pi_agent_dir)"; then ac_die "HOME is not set and --pi-agent-dir was not provided"; fi
if [ -n "$shared_skill_dir_arg" ]; then shared_skill_dir="$(ac_absolute_path "$shared_skill_dir_arg")"; elif ! shared_skill_dir="$(ac_default_shared_skill_dir)"; then ac_die "HOME is not set and --shared-skill-dir was not provided"; fi

check_link() {
  local name="$1" dest="$2" expected="$3" resolved
  if [ ! -L "$dest" ]; then fail "$name" "path=$dest expected=$expected"; return; fi
  resolved="$(realpath -- "$dest" 2>/dev/null || true)"
  if [ "$resolved" = "$expected" ]; then pass "$name" "path=$dest"; else fail "$name" "path=$dest resolved=${resolved:-<unresolved>} expected=$expected"; fi
}

if command -v pi >/dev/null 2>&1; then
  pi_version="$(pi --version 2>/dev/null | sed -n '1s/[^0-9]*\([0-9][0-9.]*\).*/\1/p')"
  if [ -n "$pi_version" ] && [ "$(printf '%s\n%s\n' 0.85.0 "$pi_version" | sort -V | head -n 1)" = 0.85.0 ]; then pass command_pi "version=$pi_version"; else fail command_pi "version=${pi_version:-unknown} minimum=0.85.0"; fi
else
  fail command_pi missing
fi

package_json="$pi_agent_dir/npm/node_modules/pi-open-agents/package.json"
if [ -f "$package_json" ]; then
  package_version="$(node -e 'const p=require(process.argv[1]);process.stdout.write(String(p.version||""))' "$package_json" 2>/dev/null || true)"
  if [ "$package_version" = 0.1.20 ]; then pass pi_open_agents_package "version=$package_version"; else fail pi_open_agents_package "version=${package_version:-unknown} expected=0.1.20"; fi
else
  fail pi_open_agents_package "missing=$package_json"
fi

settings="$pi_agent_dir/settings.json"
if [ -f "$settings" ] && node -e '
const fs=require("fs"); const s=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));
const values=[...(Array.isArray(s.extensions)?s.extensions:[]),...(Array.isArray(s.packages)?s.packages:[])];
process.exit(values.some(v=>typeof v==="string" && /^npm:pi-open-agents(?:@|$)/.test(v))?0:1);
' "$settings" 2>/dev/null; then pass pi_open_agents_enabled "settings=$settings"; else fail pi_open_agents_enabled "settings=$settings extension=npm:pi-open-agents"; fi

for agent_file in $AC_AGENT_FILES; do check_link "pi_agent_${agent_file%.md}" "$pi_agent_dir/agents/$agent_file" "$repo_root/.opencode/agents/$agent_file"; done
for skill_name in $AC_SKILL_NAMES; do check_link "shared_skill_$skill_name" "$shared_skill_dir/$skill_name" "$repo_root/.agents/skills/$skill_name"; done

expected_allowed='allowedAgents: [plan-improver-model2, plan-improver-model3, plan-validation-designer, plan-coverage-reviewer, plan-red-team-gate, plan-implementation-simulator, plan-fact-auditor, plan-contract-checker]'
for primary_file in $AC_PRIMARY_AGENT_FILES; do
  path="$repo_root/.opencode/agents/$primary_file"
  if grep -Fqx "$expected_allowed" "$path" && grep -q '^maxDepth: 1$' "$path"; then pass "pi_contract_${primary_file%.md}" "allowed_reviewers=8"; else fail "pi_contract_${primary_file%.md}" "allowedAgents_must_be_exact_inline_array"; fi
done
while read -r reviewer skill model; do
  [ -n "$reviewer" ] || continue
  path="$repo_root/.opencode/agents/$reviewer.md"
  if grep -Fqx "skills: [$skill]" "$path" && grep -q '^mode: subagent$' "$path" && grep -q '^maxDepth: 0$' "$path" && grep -Fq "Your first action must load \`$skill\`" "$path"; then pass "pi_reviewer_$reviewer" "skill=$skill max_depth=0"; else fail "pi_reviewer_$reviewer" "expected_skill=$skill maxDepth=0 first_action=skill_load"; fi
done <<EOF
$AC_REVIEWER_SKILL_MAP
EOF

plan_source="$repo_root/.opencode/agents/ping-pong-plan.md"
if grep -Fq 'Analysis was performed by model 1 directly` is never a valid status or reason' "$plan_source" \
  && grep -Fq 'PLAN GAP COMPLETION' "$plan_source" \
  && grep -Fq 'ALTERNATIVE ROUTE CHALLENGE' "$plan_source" \
  && ! grep -Fq 'delegated_task_body' "$plan_source"; then
  pass pi_prompt_hardening "early_delegation=true distinct_improvers=true"
else
  fail pi_prompt_hardening "missing_prompt_hardening_contract"
fi

# Project-local agent files have precedence in Pi. Allow this cookbook's own
# canonical files, but fail any other same-name definition that could shadow a link.
for agent_file in $AC_AGENT_FILES; do
  canonical="$repo_root/.opencode/agents/$agent_file"
  for candidate in "$target_repo/.opencode/agents/$agent_file" "$target_repo/.pi/agents/$agent_file" "$target_repo/.agents/$agent_file"; do
    [ -e "$candidate" ] || [ -L "$candidate" ] || continue
    resolved="$(realpath -- "$candidate" 2>/dev/null || true)"
    if [ "$resolved" = "$canonical" ]; then pass "project_override_${agent_file%.md}" "path=$candidate canonical=true"; else fail "project_override_${agent_file%.md}" "path=$candidate shadows=$canonical"; fi
  done
done

if [ "$failures" -eq 0 ]; then printf 'SUMMARY status=pass runtime=pi agents=11 skills=7 plugin=pi-open-agents@0.1.20\n'; exit 0; fi
printf 'SUMMARY status=fail runtime=pi failures=%s\n' "$failures"
exit 1
