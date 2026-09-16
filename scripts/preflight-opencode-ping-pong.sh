#!/usr/bin/env bash
set -u

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-opencode.sh
. "$script_dir/lib-opencode.sh"

usage() {
  cat <<'USAGE'
Usage: scripts/preflight-opencode-ping-pong.sh [--global-dir DIR] [--shared-skill-dir DIR] [--quick] [target-repo]

Validate canonical agents/ and skills/, runtime links, description economics,
standalone capability contracts, and the exact eight-review Ping-Pong gate.
USAGE
}

failures=0
quick=false
global_dir_arg=""
shared_skill_dir_arg=""
target_repo=""
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
agent_src_dir="$(ac_agent_source_dir "$repo_root")"
skill_src_dir="$(ac_skill_source_dir "$repo_root")"
target_repo="$(ac_absolute_path "${target_repo:-$PWD}")"
if [ -n "$global_dir_arg" ]; then global_dir="$(ac_absolute_path "$global_dir_arg")"; elif ! global_dir="$(ac_default_global_dir)"; then ac_die "HOME is not set"; fi
if [ -n "$shared_skill_dir_arg" ]; then shared_skill_dir="$(ac_absolute_path "$shared_skill_dir_arg")"; elif ! shared_skill_dir="$(ac_default_shared_skill_dir)"; then ac_die "HOME is not set"; fi

check_link() {
  local name="$1" dest="$2" expected="$3" resolved
  if [ ! -L "$dest" ]; then fail "$name" "path=$dest expected=$expected"; return; fi
  resolved="$(realpath -- "$dest" 2>/dev/null || true)"
  [ "$resolved" = "$expected" ] && pass "$name" "path=$dest" || fail "$name" "resolved=${resolved:-<unresolved>} expected=$expected"
}

frontmatter_description() {
  sed -n 's/^description:[[:space:]]*//p' "$1" | head -n 1
}

validate_description() {
  local kind="$1" name="$2" path="$3" max="$4" description length
  description="$(frontmatter_description "$path")"
  length=${#description}
  if [ -z "$description" ]; then fail "${kind}_description_$name" "missing"; return; fi
  if [ "$length" -gt "$max" ]; then fail "${kind}_description_$name" "chars=$length max=$max"; return; fi
  pass "${kind}_description_$name" "chars=$length target=$AC_DESCRIPTION_TARGET max=$max"
}

[ -d "$agent_src_dir" ] && pass canonical_agents_dir "path=$agent_src_dir" || fail canonical_agents_dir "missing=$agent_src_dir"
[ -d "$skill_src_dir" ] && pass canonical_skills_dir "path=$skill_src_dir" || fail canonical_skills_dir "missing=$skill_src_dir"

agent_count=0
for agent_file in $AC_AGENT_FILES; do
  path="$agent_src_dir/$agent_file"
  if [ -f "$path" ]; then
    agent_count=$((agent_count + 1))
    validate_description agent "${agent_file%.md}" "$path" "$AC_AGENT_DESCRIPTION_MAX"
    check_link "global_agent_${agent_file%.md}" "$global_dir/agents/$agent_file" "$path"
  else
    fail "source_agent_${agent_file%.md}" "missing=$path"
  fi
done
[ "$agent_count" -eq 12 ] && pass canonical_agent_count "count=12" || fail canonical_agent_count "count=$agent_count expected=12"

skill_count=0
for skill_name in $AC_SKILL_NAMES; do
  path="$skill_src_dir/$skill_name/SKILL.md"
  if [ -f "$path" ]; then
    skill_count=$((skill_count + 1))
    validate_description skill "$skill_name" "$path" "$AC_SKILL_DESCRIPTION_MAX"
    check_link "shared_skill_$skill_name" "$shared_skill_dir/$skill_name" "$skill_src_dir/$skill_name"
  else
    fail "source_skill_$skill_name" "missing=$path"
  fi
done
[ "$skill_count" -eq 8 ] && pass canonical_skill_count "count=8" || fail canonical_skill_count "count=$skill_count expected=8"

# Mandatory full-flow gate remains exactly eight reviewers.
for primary_file in $AC_PRIMARY_AGENT_FILES; do
  path="$agent_src_dir/$primary_file"
  name="${primary_file%.md}"
  if grep -q '^mode: primary$' "$path" && grep -q '^  task:$' "$path" && grep -Fq 'OpenCode: `task({' "$path" && grep -Fq 'Pi + `pi-open-agents`: `subagent({' "$path"; then
    pass "source_primary_$name" "runtime_adapter=present"
  else
    fail "source_primary_$name" "missing_primary_or_runtime_contract"
  fi
done

while read -r reviewer skill model; do
  [ -n "$reviewer" ] || continue
  path="$agent_src_dir/$reviewer.md"
  if [ -f "$path" ] && grep -q '^mode: subagent$' "$path" && grep -q '^maxDepth: 0$' "$path" && grep -q "^model: $model$" "$path" && grep -Fq "skills: [$skill]" "$path" && grep -q '^  task: deny$' "$path" && grep -Fq "Load \`$skill\` first" "$path"; then
    pass "flow_reviewer_$reviewer" "skill=$skill model=$model standalone=true"
  else
    fail "flow_reviewer_$reviewer" "contract_mismatch skill=$skill model=$model"
  fi
done <<EOF
$AC_FLOW_REVIEWER_SKILL_MAP
EOF

while read -r reviewer skill model; do
  [ -n "$reviewer" ] || continue
  path="$agent_src_dir/$reviewer.md"
  if [ -f "$path" ] && grep -q '^mode: subagent$' "$path" && grep -q '^maxDepth: 0$' "$path" && grep -q "^model: $model$" "$path" && grep -Fq "skills: [$skill]" "$path" && grep -Fq 'not part of the mandatory eight-review' "$path"; then
    pass "standalone_agent_$reviewer" "skill=$skill flow_gate=false"
  else
    fail "standalone_agent_$reviewer" "standalone_contract_mismatch"
  fi
done <<EOF
$AC_STANDALONE_AGENT_SKILL_MAP
EOF

plan_source="$agent_src_dir/ping-pong-plan.md"
if grep -q '^  skill: deny$' "$plan_source" && grep -Fq 'Attempt every reviewer exactly once' "$plan_source" && grep -Fq '98,304' "$plan_source" && ! grep -Fq 'code-performance-optimization-auditor' "$plan_source"; then
  pass source_ping_pong_gate "mandatory_reviewers=8 coordinator_skill=false context_98k=true"
else
  fail source_ping_pong_gate "authority_or_gate_contract_mismatch"
fi

# Repository authority must not depend on hidden source directories.
if [ -d "$repo_root/.opencode/agents" ] || [ -d "$repo_root/.agents/skills" ]; then
  fail canonical_layout "legacy_hidden_source_dirs_present"
else
  pass canonical_layout "hidden_source_dirs=absent"
fi

if [ "$quick" = false ]; then
  if ! command -v opencode >/dev/null 2>&1; then
    fail command_opencode missing
  else
    pass command_opencode "path=$(command -v opencode)"
    for primary_file in $AC_PRIMARY_AGENT_FILES; do
      name="${primary_file%.md}"
      output="$(cd -- "$target_repo" && opencode debug agent "$name" 2>&1)"; status=$?
      if [ "$status" -ne 0 ]; then fail "debug_agent_$name" "status=$status"; continue; fi
      mode=readonly; [ "$name" = ping-ping-build ] && mode=build; [ "$name" = subagent-router ] && mode=router
      if printf '%s\n' "$output" | node -e '
const fs=require("fs"); const mode=process.argv[1]; const raw=fs.readFileSync(0,"utf8"); const start=raw.indexOf("{"); if(start<0)process.exit(2); const a=JSON.parse(raw.slice(start)); const t=a.tools||{}; const expected={task:true,read:true,grep:true,glob:true,skill:mode==="build",edit:mode==="build",write:mode==="build",bash:mode==="build"}; const bad=Object.entries(expected).filter(([k,v])=>t[k]!==v); if(bad.length)process.exit(1);
' "$mode"; then pass "debug_agent_$name" "tools=correct"; else fail "debug_agent_$name" "tools_incorrect"; fi
    done

    skill_output="$(cd -- "$target_repo" && opencode debug skill 2>&1)"; skill_status=$?
    if [ "$skill_status" -ne 0 ]; then fail debug_skills "status=$skill_status"; else
      missing=""; for skill_name in $AC_SKILL_NAMES; do printf '%s\n' "$skill_output" | grep -q "$skill_name" || missing="$missing $skill_name"; done
      [ -z "$missing" ] && pass debug_skills "all=8" || fail debug_skills "missing=$missing"
    fi
  fi
fi

if [ "$failures" -eq 0 ]; then printf 'SUMMARY status=pass runtime=opencode quick=%s agents=12 skills=8 mandatory_flow_reviewers=8\n' "$quick"; exit 0; fi
printf 'SUMMARY status=fail runtime=opencode failures=%s\n' "$failures"
exit 1
