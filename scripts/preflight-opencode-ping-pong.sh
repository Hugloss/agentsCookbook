#!/usr/bin/env bash
set -u

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-opencode.sh
. "$script_dir/lib-opencode.sh"

usage() {
  cat <<'USAGE'
Usage: scripts/preflight-opencode-ping-pong.sh [--global-dir DIR] [--shared-skill-dir DIR] [--quick] [target-repo]

Validate canonical sources, installed OpenCode links, deny-by-default reviewer
authority, optional bounded artifact transport, and the exact eight-review gate.
USAGE
}

failures=0; quick=false; global_dir_arg=""; shared_skill_dir_arg=""; target_repo=""
pass() { printf 'CHECK name=%s status=pass %s\n' "$1" "${2:-}"; }
fail() { failures=$((failures + 1)); printf 'CHECK name=%s status=fail %s\n' "$1" "${2:-}"; }
while [ "$#" -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --quick) quick=true ;;
    --global-dir) shift; [ "$#" -gt 0 ] || ac_die "--global-dir requires a directory"; global_dir_arg="$1" ;;
    --shared-skill-dir) shift; [ "$#" -gt 0 ] || ac_die "--shared-skill-dir requires a directory"; shared_skill_dir_arg="$1" ;;
    --*) usage >&2; ac_die "unknown option: $1" ;;
    *) [ -z "$target_repo" ] || ac_die "only one target repo may be supplied"; target_repo="$1" ;;
  esac
  shift
done

repo_root="$(ac_repo_root_from_script "${BASH_SOURCE[0]}")"
agent_src_dir="$(ac_agent_source_dir "$repo_root")"; skill_src_dir="$(ac_skill_source_dir "$repo_root")"
opencode_adapter="$(ac_opencode_artifact_adapter "$repo_root")"
target_repo="$(ac_absolute_path "${target_repo:-$PWD}")"
if [ -n "$global_dir_arg" ]; then global_dir="$(ac_absolute_path "$global_dir_arg")"; elif ! global_dir="$(ac_default_global_dir)"; then ac_die "HOME is not set"; fi
if [ -n "$shared_skill_dir_arg" ]; then shared_skill_dir="$(ac_absolute_path "$shared_skill_dir_arg")"; elif ! shared_skill_dir="$(ac_default_shared_skill_dir)"; then ac_die "HOME is not set"; fi

check_link() {
  local name="$1" dest="$2" expected="$3" resolved
  if [ ! -L "$dest" ]; then fail "$name" "path=$dest expected=$expected"; return; fi
  resolved="$(realpath -- "$dest" 2>/dev/null || true)"
  [ "$resolved" = "$expected" ] && pass "$name" "path=$dest" || fail "$name" "resolved=${resolved:-<unresolved>} expected=$expected"
}
frontmatter_description() { sed -n 's/^description:[[:space:]]*//p' "$1" | head -n 1; }
validate_description() {
  local kind="$1" name="$2" path="$3" max="$4" description length
  description="$(frontmatter_description "$path")"; length=${#description}
  [ -n "$description" ] || { fail "${kind}_description_$name" missing; return; }
  [ "$length" -le "$max" ] || { fail "${kind}_description_$name" "chars=$length max=$max"; return; }
  pass "${kind}_description_$name" "chars=$length target=$AC_DESCRIPTION_TARGET max=$max"
}

[ -d "$agent_src_dir" ] && pass canonical_agents_dir "path=$agent_src_dir" || fail canonical_agents_dir "missing=$agent_src_dir"
[ -d "$skill_src_dir" ] && pass canonical_skills_dir "path=$skill_src_dir" || fail canonical_skills_dir "missing=$skill_src_dir"
[ -f "$opencode_adapter" ] && pass canonical_opencode_artifact_adapter "path=$opencode_adapter" || fail canonical_opencode_artifact_adapter missing

agent_count=0
for agent_file in $AC_AGENT_FILES; do
  path="$agent_src_dir/$agent_file"
  if [ -f "$path" ]; then agent_count=$((agent_count + 1)); validate_description agent "${agent_file%.md}" "$path" "$AC_AGENT_DESCRIPTION_MAX"; check_link "global_agent_${agent_file%.md}" "$global_dir/agents/$agent_file" "$path"; else fail "source_agent_${agent_file%.md}" "missing=$path"; fi
done
[ "$agent_count" -eq 12 ] && pass canonical_agent_count count=12 || fail canonical_agent_count "count=$agent_count expected=12"

skill_count=0
for skill_name in $AC_SKILL_NAMES; do
  path="$skill_src_dir/$skill_name/SKILL.md"
  if [ -f "$path" ]; then skill_count=$((skill_count + 1)); validate_description skill "$skill_name" "$path" "$AC_SKILL_DESCRIPTION_MAX"; check_link "shared_skill_$skill_name" "$shared_skill_dir/$skill_name" "$skill_src_dir/$skill_name"; else fail "source_skill_$skill_name" "missing=$path"; fi
done
[ "$skill_count" -eq 8 ] && pass canonical_skill_count count=8 || fail canonical_skill_count "count=$skill_count expected=8"
check_link opencode_artifact_plugin "$global_dir/plugins/$AC_OPENCODE_ARTIFACT_PLUGIN" "$opencode_adapter"

for primary_file in $AC_PRIMARY_AGENT_FILES; do
  path="$agent_src_dir/$primary_file"; name="${primary_file%.md}"
  if grep -q '^mode: primary$' "$path" && grep -q '^  task:$' "$path" && grep -q '^  review_artifact_read: allow$' "$path" && grep -Fq 'OpenCode: `task({' "$path" && grep -Fq 'Pi + `pi-open-agents`: `subagent({' "$path"; then pass "source_primary_$name" "runtime_adapter=present artifact_read=allow"; else fail "source_primary_$name" primary_contract_mismatch; fi
done

while read -r reviewer skill model; do
  [ -n "$reviewer" ] || continue; path="$agent_src_dir/$reviewer.md"
  if [ -f "$path" ] && grep -q '^mode: subagent$' "$path" && grep -q '^maxDepth: 0$' "$path" && grep -q "^model: $model$" "$path" && grep -Fq '  "*": deny' "$path" && grep -Fq "skills: [$skill]" "$path" && grep -q '^  review_artifact: allow$' "$path" && grep -Fq "Load \`$skill\` first" "$path"; then pass "flow_reviewer_$reviewer" "skill=$skill deny_by_default=true artifact_write=bounded"; else fail "flow_reviewer_$reviewer" reviewer_contract_mismatch; fi
done <<EOF
$AC_FLOW_REVIEWER_SKILL_MAP
EOF
while read -r reviewer skill model; do
  [ -n "$reviewer" ] || continue; path="$agent_src_dir/$reviewer.md"
  if grep -Fq '  "*": deny' "$path" && grep -q '^  review_artifact: allow$' "$path" && grep -Fq 'not part of the mandatory eight-review' "$path"; then pass "standalone_agent_$reviewer" "deny_by_default=true artifact_write=bounded flow_gate=false"; else fail "standalone_agent_$reviewer" standalone_contract_mismatch; fi
done <<EOF
$AC_STANDALONE_AGENT_SKILL_MAP
EOF

plan_source="$agent_src_dir/ping-pong-plan.md"
if grep -Fq 'Attempt every reviewer exactly once' "$plan_source" && grep -Fq '98,304' "$plan_source" && grep -Fq 'review_artifact_read' "$plan_source" && ! grep -Fq 'code-performance-optimization-auditor' "$plan_source"; then pass source_ping_pong_gate "mandatory_reviewers=8 context_98k=true selective_artifact_read=true"; else fail source_ping_pong_gate gate_contract_mismatch; fi

if [ -d "$repo_root/.opencode/agents" ] || [ -d "$repo_root/.agents/skills" ]; then fail canonical_layout legacy_hidden_source_dirs_present; else pass canonical_layout hidden_source_dirs=absent; fi

if [ "$quick" = false ]; then
  if ! command -v opencode >/dev/null 2>&1; then fail command_opencode missing; else
    pass command_opencode "path=$(command -v opencode)"
    artifact_enabled=false; [ -n "${AGENTS_COOKBOOK_RUN_DIR:-}" ] && artifact_enabled=true
    for primary_file in $AC_PRIMARY_AGENT_FILES; do
      name="${primary_file%.md}"; output="$(cd -- "$target_repo" && opencode debug agent "$name" 2>&1)"; status=$?
      if [ "$status" -ne 0 ]; then fail "debug_agent_$name" "status=$status"; continue; fi
      mode=readonly; [ "$name" = ping-ping-build ] && mode=build
      if printf '%s\n' "$output" | node -e '
const fs=require("fs");const mode=process.argv[1],artifact=process.argv[2]==="true";const raw=fs.readFileSync(0,"utf8"),start=raw.indexOf("{");if(start<0)process.exit(2);const a=JSON.parse(raw.slice(start)),t=a.tools||{};const e={task:true,read:true,grep:true,glob:true,skill:mode==="build",edit:mode==="build",write:mode==="build",bash:mode==="build",review_artifact_read:artifact};if(Object.entries(e).some(([k,v])=>t[k]!==v))process.exit(1);
' "$mode" "$artifact_enabled"; then pass "debug_agent_$name" "tools=correct artifact_mode=$artifact_enabled"; else fail "debug_agent_$name" tools_incorrect; fi
    done
    effective_output="$(bash "$repo_root/scripts/check-opencode-effective-reviewers.sh" "$target_repo" 2>&1)"; effective_status=$?; printf '%s\n' "$effective_output"; [ "$effective_status" -eq 0 ] && pass effective_reviewer_contracts reviewers=9 || fail effective_reviewer_contracts "status=$effective_status"
    skill_output="$(cd -- "$target_repo" && opencode debug skill 2>&1)"; skill_status=$?
    if [ "$skill_status" -ne 0 ]; then fail debug_skills "status=$skill_status"; else missing=""; for skill_name in $AC_SKILL_NAMES; do printf '%s\n' "$skill_output" | grep -q "$skill_name" || missing="$missing $skill_name"; done; [ -z "$missing" ] && pass debug_skills all=8 || fail debug_skills "missing=$missing"; fi
  fi
fi

if [ "$failures" -eq 0 ]; then printf 'SUMMARY status=pass runtime=opencode quick=%s agents=12 skills=8 adapters=1 mandatory_flow_reviewers=8\n' "$quick"; exit 0; fi
printf 'SUMMARY status=fail runtime=opencode failures=%s\n' "$failures"; exit 1
