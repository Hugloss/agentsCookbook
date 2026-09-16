#!/usr/bin/env bash
set -u

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-opencode.sh
. "$script_dir/lib-opencode.sh"

usage() {
  cat <<'USAGE'
Usage: scripts/preflight-pi-ping-pong.sh [--pi-agent-dir DIR] [--shared-skill-dir DIR] [target-repo]

Validate Pi, pi-open-agents, canonical agents/ and skills/, runtime links,
standalone capability contracts, and the exact eight-review flow gate.
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
    --pi-agent-dir) shift; [ "$#" -gt 0 ] || ac_die "--pi-agent-dir requires a directory"; pi_agent_dir_arg="$1" ;;
    --shared-skill-dir) shift; [ "$#" -gt 0 ] || ac_die "--shared-skill-dir requires a directory"; shared_skill_dir_arg="$1" ;;
    --*) usage >&2; ac_die "unknown option: $1" ;;
    *) [ -z "$target_repo" ] || ac_die "only one target repo may be supplied"; target_repo="$1" ;;
  esac
  shift
done

repo_root="$(ac_repo_root_from_script "${BASH_SOURCE[0]}")"
agent_src_dir="$(ac_agent_source_dir "$repo_root")"
skill_src_dir="$(ac_skill_source_dir "$repo_root")"
target_repo="$(ac_absolute_path "${target_repo:-$PWD}")"
if [ -n "$pi_agent_dir_arg" ]; then pi_agent_dir="$(ac_absolute_path "$pi_agent_dir_arg")"; elif ! pi_agent_dir="$(ac_default_pi_agent_dir)"; then ac_die "HOME is not set"; fi
if [ -n "$shared_skill_dir_arg" ]; then shared_skill_dir="$(ac_absolute_path "$shared_skill_dir_arg")"; elif ! shared_skill_dir="$(ac_default_shared_skill_dir)"; then ac_die "HOME is not set"; fi

check_link() {
  local name="$1" dest="$2" expected="$3" resolved
  if [ ! -L "$dest" ]; then fail "$name" "path=$dest expected=$expected"; return; fi
  resolved="$(realpath -- "$dest" 2>/dev/null || true)"
  [ "$resolved" = "$expected" ] && pass "$name" "path=$dest" || fail "$name" "resolved=${resolved:-<unresolved>} expected=$expected"
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
  [ "$package_version" = 0.1.20 ] && pass pi_open_agents_package "version=$package_version" || fail pi_open_agents_package "version=${package_version:-unknown} expected=0.1.20"
else
  fail pi_open_agents_package "missing=$package_json"
fi

settings="$pi_agent_dir/settings.json"
if [ -f "$settings" ] && node -e '
const fs=require("fs"); const s=JSON.parse(fs.readFileSync(process.argv[1],"utf8")); const values=[...(Array.isArray(s.extensions)?s.extensions:[]),...(Array.isArray(s.packages)?s.packages:[])]; process.exit(values.some(v=>typeof v==="string" && /^npm:pi-open-agents(?:@|$)/.test(v))?0:1);
' "$settings" 2>/dev/null; then pass pi_open_agents_enabled "settings=$settings"; else fail pi_open_agents_enabled "settings=$settings extension=npm:pi-open-agents"; fi

for agent_file in $AC_AGENT_FILES; do check_link "pi_agent_${agent_file%.md}" "$pi_agent_dir/agents/$agent_file" "$agent_src_dir/$agent_file"; done
for skill_name in $AC_SKILL_NAMES; do check_link "shared_skill_$skill_name" "$shared_skill_dir/$skill_name" "$skill_src_dir/$skill_name"; done

expected_allowed='allowedAgents: [plan-improver-model2, plan-improver-model3, plan-validation-designer, plan-coverage-reviewer, plan-red-team-gate, plan-implementation-simulator, plan-fact-auditor, plan-contract-checker]'
for primary_file in $AC_PRIMARY_AGENT_FILES; do
  path="$agent_src_dir/$primary_file"
  if grep -Fqx "$expected_allowed" "$path" && grep -q '^maxDepth: 1$' "$path"; then pass "pi_contract_${primary_file%.md}" "allowed_reviewers=8"; else fail "pi_contract_${primary_file%.md}" "allowedAgents_must_be_exact_eight"; fi
done

while read -r reviewer skill model; do
  [ -n "$reviewer" ] || continue
  path="$agent_src_dir/$reviewer.md"
  if grep -Fqx "skills: [$skill]" "$path" && grep -q '^mode: subagent$' "$path" && grep -q '^maxDepth: 0$' "$path" && grep -Fq "Load \`$skill\` first" "$path" && grep -Fq 'standalone reviewer' "$path"; then
    pass "pi_reviewer_$reviewer" "skill=$skill standalone=true"
  else
    fail "pi_reviewer_$reviewer" "contract_mismatch skill=$skill"
  fi
done <<EOF
$AC_FLOW_REVIEWER_SKILL_MAP
EOF

while read -r reviewer skill model; do
  [ -n "$reviewer" ] || continue
  path="$agent_src_dir/$reviewer.md"
  if grep -Fqx "skills: [$skill]" "$path" && grep -q '^maxDepth: 0$' "$path" && grep -Fq 'not part of the mandatory eight-review' "$path"; then
    pass "pi_standalone_$reviewer" "skill=$skill flow_gate=false"
  else
    fail "pi_standalone_$reviewer" "standalone_contract_mismatch"
  fi
done <<EOF
$AC_STANDALONE_AGENT_SKILL_MAP
EOF

plan_source="$agent_src_dir/ping-pong-plan.md"
if grep -Fq 'Attempt every reviewer exactly once' "$plan_source" && grep -Fq '98,304' "$plan_source" && ! grep -Fq 'code-performance-optimization-auditor' "$plan_source"; then
  pass pi_prompt_gate "mandatory_reviewers=8 context_98k=true"
else
  fail pi_prompt_gate "flow_gate_contract_mismatch"
fi

# Project-local agent files can shadow installed Pi definitions. Allow canonical
# self-links only; fail other same-name definitions.
for agent_file in $AC_AGENT_FILES; do
  canonical="$agent_src_dir/$agent_file"
  for candidate in "$target_repo/.opencode/agents/$agent_file" "$target_repo/.pi/agents/$agent_file" "$target_repo/.agents/$agent_file"; do
    [ -e "$candidate" ] || [ -L "$candidate" ] || continue
    resolved="$(realpath -- "$candidate" 2>/dev/null || true)"
    if [ "$resolved" = "$canonical" ]; then pass "project_override_${agent_file%.md}" "path=$candidate canonical=true"; else fail "project_override_${agent_file%.md}" "path=$candidate shadows=$canonical"; fi
  done
done

if [ -d "$repo_root/.opencode/agents" ] || [ -d "$repo_root/.agents/skills" ]; then
  fail canonical_layout "legacy_hidden_source_dirs_present"
else
  pass canonical_layout "hidden_source_dirs=absent"
fi

if [ "$failures" -eq 0 ]; then printf 'SUMMARY status=pass runtime=pi agents=12 skills=8 mandatory_flow_reviewers=8 plugin=pi-open-agents@0.1.20\n'; exit 0; fi
printf 'SUMMARY status=fail runtime=pi failures=%s\n' "$failures"
exit 1
