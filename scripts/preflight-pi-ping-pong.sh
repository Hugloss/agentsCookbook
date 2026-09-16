#!/usr/bin/env bash
set -u

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-opencode.sh
. "$script_dir/lib-opencode.sh"

usage() {
  cat <<'USAGE'
Usage: scripts/preflight-pi-ping-pong.sh [--pi-agent-dir DIR] [--shared-skill-dir DIR] [target-repo]

Validate Pi, pi-open-agents, canonical source contracts, installed links,
deny-by-default reviewer authority, bounded artifact extension, project
shadowing, and the exact eight-review gate.
USAGE
}

failures=0; pi_agent_dir_arg=""; shared_skill_dir_arg=""; target_repo=""
pass() { printf 'CHECK name=%s status=pass %s\n' "$1" "${2:-}"; }
fail() { failures=$((failures + 1)); printf 'CHECK name=%s status=fail %s\n' "$1" "${2:-}"; }
while [ "$#" -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --pi-agent-dir) shift; [ "$#" -gt 0 ] || ac_die "--pi-agent-dir requires a directory"; pi_agent_dir_arg="$1" ;;
    --shared-skill-dir) shift; [ "$#" -gt 0 ] || ac_die "--shared-skill-dir requires a directory"; shared_skill_dir_arg="$1" ;;
    --*) usage >&2; ac_die "unknown option: $1" ;;
    *) [ -z "$target_repo" ] || ac_die "only one target repo may be supplied"; target_repo="$1" ;;
  esac
  shift
done

repo_root="$(ac_repo_root_from_script "${BASH_SOURCE[0]}")"
agent_src_dir="$(ac_agent_source_dir "$repo_root")"; skill_src_dir="$(ac_skill_source_dir "$repo_root")"; pi_adapter="$(ac_pi_artifact_adapter "$repo_root")"
target_repo="$(ac_absolute_path "${target_repo:-$PWD}")"
if [ -n "$pi_agent_dir_arg" ]; then pi_agent_dir="$(ac_absolute_path "$pi_agent_dir_arg")"; elif ! pi_agent_dir="$(ac_default_pi_agent_dir)"; then ac_die "HOME is not set"; fi
if [ -n "$shared_skill_dir_arg" ]; then shared_skill_dir="$(ac_absolute_path "$shared_skill_dir_arg")"; elif ! shared_skill_dir="$(ac_default_shared_skill_dir)"; then ac_die "HOME is not set"; fi
expected_skill_count="$(printf '%s\n' $AC_SKILL_NAMES | sed '/^$/d' | wc -l)"

canonical_output="$(bash "$repo_root/scripts/check-canonical-sources.sh" 2>&1)"; canonical_status=$?; printf '%s\n' "$canonical_output"
[ "$canonical_status" -eq 0 ] && pass canonical_source_contract status=pass || fail canonical_source_contract "status=$canonical_status"

check_link() {
  local name="$1" dest="$2" expected="$3" resolved
  if [ ! -L "$dest" ]; then fail "$name" "path=$dest expected=$expected"; return; fi
  resolved="$(realpath -- "$dest" 2>/dev/null || true)"; [ "$resolved" = "$expected" ] && pass "$name" "path=$dest" || fail "$name" "resolved=${resolved:-<unresolved>} expected=$expected"
}
version_at_least() {
  local minimum="$1" actual="$2"
  [ -n "$actual" ] && [ "$(printf '%s\n%s\n' "$minimum" "$actual" | sort -V | head -n 1)" = "$minimum" ]
}

if command -v pi >/dev/null 2>&1; then
  pi_version="$(pi --version 2>/dev/null | sed -n '1s/[^0-9]*\([0-9][0-9.]*\).*/\1/p')"
  if version_at_least 0.85.0 "$pi_version"; then pass command_pi "version=$pi_version minimum=0.85.0"; else fail command_pi "version=${pi_version:-unknown} minimum=0.85.0"; fi
else fail command_pi missing; fi

package_json="$pi_agent_dir/npm/node_modules/pi-open-agents/package.json"
if [ -f "$package_json" ]; then
  package_version="$(node -e 'const p=require(process.argv[1]);process.stdout.write(String(p.version||""))' "$package_json" 2>/dev/null || true)"
  if version_at_least 0.1.20 "$package_version"; then pass pi_open_agents_package "version=$package_version minimum=0.1.20"; else fail pi_open_agents_package "version=${package_version:-unknown} minimum=0.1.20"; fi
else fail pi_open_agents_package "missing=$package_json"; fi

settings="$pi_agent_dir/settings.json"
if [ -f "$settings" ] && node -e 'const fs=require("fs"),s=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));const v=[...(Array.isArray(s.extensions)?s.extensions:[]),...(Array.isArray(s.packages)?s.packages:[])];process.exit(v.some(x=>typeof x==="string"&&/^npm:pi-open-agents(?:@|$)/.test(x))?0:1)' "$settings" 2>/dev/null; then pass pi_open_agents_enabled "settings=$settings"; else fail pi_open_agents_enabled "settings=$settings extension=npm:pi-open-agents"; fi

for agent_file in $AC_AGENT_FILES; do check_link "pi_agent_${agent_file%.md}" "$pi_agent_dir/agents/$agent_file" "$agent_src_dir/$agent_file"; done
for skill_name in $AC_SKILL_NAMES; do check_link "shared_skill_$skill_name" "$shared_skill_dir/$skill_name" "$skill_src_dir/$skill_name"; done
check_link pi_artifact_extension "$pi_agent_dir/extensions/$AC_PI_ARTIFACT_EXTENSION" "$pi_adapter"

expected_allowed='allowedAgents: [plan-improver-model2, plan-improver-model3, plan-validation-designer, plan-coverage-reviewer, plan-red-team-gate, plan-implementation-simulator, plan-fact-auditor, plan-contract-checker]'
for primary_file in $AC_PRIMARY_AGENT_FILES; do
  path="$agent_src_dir/$primary_file"
  if grep -Fqx "$expected_allowed" "$path" && grep -q '^maxDepth: 1$' "$path" && grep -Fq '  "*": deny' "$path" && grep -q '^  review_artifact_read: allow$' "$path"; then pass "pi_contract_${primary_file%.md}" "allowed_reviewers=8 artifact_read=allow"; else fail "pi_contract_${primary_file%.md}" primary_contract_mismatch; fi
done

while read -r reviewer skill model; do
  [ -n "$reviewer" ] || continue; path="$agent_src_dir/$reviewer.md"
  if grep -Fqx "skills: [$skill]" "$path" && grep -q '^mode: subagent$' "$path" && grep -q '^maxDepth: 0$' "$path" && grep -Fq '  "*": deny' "$path" && grep -q '^  review_artifact: allow$' "$path" && grep -Fq "Load \`$skill\` first" "$path"; then pass "pi_reviewer_$reviewer" "skill=$skill deny_by_default=true artifact_write=bounded"; else fail "pi_reviewer_$reviewer" reviewer_contract_mismatch; fi
done <<EOF
$AC_FLOW_REVIEWER_SKILL_MAP
EOF
while read -r reviewer skill model; do
  [ -n "$reviewer" ] || continue; path="$agent_src_dir/$reviewer.md"
  if grep -Fqx "skills: [$skill]" "$path" && grep -Fq '  "*": deny' "$path" && grep -q '^  review_artifact: allow$' "$path" && grep -Fq 'not part of the mandatory eight-review' "$path"; then pass "pi_standalone_$reviewer" "skill=$skill artifact_write=bounded flow_gate=false"; else fail "pi_standalone_$reviewer" standalone_contract_mismatch; fi
done <<EOF
$AC_STANDALONE_AGENT_SKILL_MAP
EOF

for agent_file in $AC_AGENT_FILES; do
  canonical="$agent_src_dir/$agent_file"
  for candidate in "$target_repo/.opencode/agents/$agent_file" "$target_repo/.pi/agents/$agent_file" "$target_repo/.agents/$agent_file"; do
    [ -e "$candidate" ] || [ -L "$candidate" ] || continue
    resolved="$(realpath -- "$candidate" 2>/dev/null || true)"; [ "$resolved" = "$canonical" ] && pass "project_override_${agent_file%.md}" "path=$candidate canonical=true" || fail "project_override_${agent_file%.md}" "path=$candidate shadows=$canonical"
  done
done

if [ "$failures" -eq 0 ]; then printf 'SUMMARY status=pass runtime=pi agents=12 skills=%s adapters=1 mandatory_flow_reviewers=8 pi_open_agents=%s\n' "$expected_skill_count" "$package_version"; exit 0; fi
printf 'SUMMARY status=fail runtime=pi failures=%s\n' "$failures"; exit 1
