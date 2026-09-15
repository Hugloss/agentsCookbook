#!/usr/bin/env bash
set -u

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-opencode.sh
. "$script_dir/lib-opencode.sh"

usage() {
  cat <<'USAGE'
Usage: scripts/preflight-opencode-ping-pong.sh [--global-dir DIR] [--shared-skill-dir DIR] [--quick] [target-repo]

Read-only OpenCode checks for all eleven agents, seven shared skills, permissions,
reviewer mappings, and the runtime delegation contract. No target opencode.json
reviewer block is required.
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
    --global-dir) shift; [ "$#" -gt 0 ] || ac_die "--global-dir requires a directory argument"; global_dir_arg="$1" ;;
    --shared-skill-dir) shift; [ "$#" -gt 0 ] || ac_die "--shared-skill-dir requires a directory argument"; shared_skill_dir_arg="$1" ;;
    --*) usage >&2; ac_die "unknown option: $1" ;;
    *) [ -z "$target_repo" ] || ac_die "only one target repo may be supplied"; target_repo="$1" ;;
  esac
  shift
done

repo_root="$(ac_repo_root_from_script "${BASH_SOURCE[0]}")"
target_repo="${target_repo:-$PWD}"
target_repo="$(ac_absolute_path "$target_repo")"
if [ -n "$global_dir_arg" ]; then global_dir="$(ac_absolute_path "$global_dir_arg")"; elif ! global_dir="$(ac_default_global_dir)"; then ac_die "HOME is not set and --global-dir was not provided"; fi
if [ -n "$shared_skill_dir_arg" ]; then shared_skill_dir="$(ac_absolute_path "$shared_skill_dir_arg")"; elif ! shared_skill_dir="$(ac_default_shared_skill_dir)"; then ac_die "HOME is not set and --shared-skill-dir was not provided"; fi

check_link() {
  local name="$1" dest="$2" expected="$3" resolved
  if [ ! -L "$dest" ]; then fail "$name" "path=$dest expected=$expected"; return; fi
  resolved="$(realpath -- "$dest" 2>/dev/null || true)"
  if [ "$resolved" = "$expected" ]; then pass "$name" "path=$dest"; else fail "$name" "path=$dest resolved=${resolved:-<unresolved>} expected=$expected"; fi
}

for agent_file in $AC_AGENT_FILES; do check_link "global_agent_${agent_file%.md}" "$global_dir/agents/$agent_file" "$repo_root/.opencode/agents/$agent_file"; done
for skill_name in $AC_SKILL_NAMES; do check_link "shared_skill_$skill_name" "$shared_skill_dir/$skill_name" "$repo_root/.agents/skills/$skill_name"; done

for primary_file in $AC_PRIMARY_AGENT_FILES; do
  path="$repo_root/.opencode/agents/$primary_file"
  name="${primary_file%.md}"
  if grep -q '^mode: primary$' "$path" \
    && grep -q '^  task:$' "$path" \
    && { grep -q 'OpenCode: `task({' "$path" || grep -q 'OpenCode exposes `task`' "$path"; } \
    && { grep -q 'Pi with `pi-open-agents`: `subagent({' "$path" || grep -q 'Pi with `pi-open-agents` exposes `subagent`' "$path"; }; then
    pass "source_primary_$name" "runtime_adapter=present"
  else
    fail "source_primary_$name" "missing_primary_mode_task_permission_or_runtime_adapter"
  fi
done

while read -r reviewer skill model; do
  [ -n "$reviewer" ] || continue
  path="$repo_root/.opencode/agents/$reviewer.md"
  if [ -f "$path" ] && grep -q '^mode: subagent$' "$path" && grep -q '^maxDepth: 0$' "$path" && grep -q "^model: $model$" "$path" && grep -Fq "skills: [$skill]" "$path" && grep -q '^  task: deny$' "$path" && grep -Fq "Your first action must load \`$skill\`" "$path"; then
    pass "source_reviewer_$reviewer" "skill=$skill model=$model"
  else
    fail "source_reviewer_$reviewer" "expected_skill=$skill expected_model=$model"
  fi
done <<EOF
$AC_REVIEWER_SKILL_MAP
EOF

plan_source="$repo_root/.opencode/agents/ping-pong-plan.md"
if grep -q '^  skill: deny$' "$plan_source" \
  && grep -Fq 'Analysis was performed by model 1 directly` is never a valid status or reason' "$plan_source" \
  && grep -Fq 'PLAN GAP COMPLETION' "$plan_source" \
  && grep -Fq 'ALTERNATIVE ROUTE CHALLENGE' "$plan_source" \
  && ! grep -Fq 'delegated_task_body' "$plan_source"; then
  pass source_ping_pong_hardening "early_delegation=true distinct_improvers=true coordinator_skill=false"
else
  fail source_ping_pong_hardening "missing_prompt_hardening_contract"
fi

if [ "$quick" = false ]; then
  if ! command -v opencode >/dev/null 2>&1; then
    fail command_opencode missing
  else
    pass command_opencode "path=$(command -v opencode)"
    for primary_file in $AC_PRIMARY_AGENT_FILES; do
      name="${primary_file%.md}"
      output="$(cd -- "$target_repo" && opencode debug agent "$name" 2>&1)"
      status=$?
      if [ "$status" -ne 0 ]; then fail "debug_agent_$name" "status=$status"; continue; fi
      mode=readonly
      [ "$name" = ping-ping-build ] && mode=build
      [ "$name" = subagent-router ] && mode=router
      if printf '%s\n' "$output" | node -e '
const fs=require("fs"); const mode=process.argv[1]; const raw=fs.readFileSync(0,"utf8");
const start=raw.indexOf("{"); if(start<0) process.exit(2); const a=JSON.parse(raw.slice(start)); const t=a.tools||{};
const expected={task:true,read:true,grep:true,glob:true,skill:mode==="build",edit:mode==="build",write:mode==="build",bash:mode==="build"};
const bad=Object.entries(expected).filter(([k,v])=>t[k]!==v); if(bad.length){console.error(bad.map(([k,v])=>`${k}=${t[k]} expected=${v}`).join(" "));process.exit(1)}
' "$mode"; then pass "debug_agent_$name" "tools=correct"; else fail "debug_agent_$name" "tools_incorrect"; fi
    done

    while read -r reviewer skill model; do
      [ -n "$reviewer" ] || continue
      output="$(cd -- "$target_repo" && opencode debug agent "$reviewer" 2>&1)"
      status=$?
      if [ "$status" -ne 0 ]; then fail "debug_reviewer_$reviewer" "status=$status"; continue; fi
      if printf '%s\n' "$output" | node -e '
const fs=require("fs"); const skill=process.argv[1]; const raw=fs.readFileSync(0,"utf8"); const start=raw.indexOf("{"); if(start<0)process.exit(2);
const a=JSON.parse(raw.slice(start)),t=a.tools||{},p=String(a.prompt||"");
if(t.task!==false||t.edit!==false||t.write!==false||t.bash!==false||t.read!==true||t.skill!==true||!p.includes(`first action must load \`${skill}\``))process.exit(1);
' "$skill"; then pass "debug_reviewer_$reviewer" "skill=$skill tools=readonly"; else fail "debug_reviewer_$reviewer" "effective_contract_incorrect"; fi
    done <<EOF
$AC_REVIEWER_SKILL_MAP
EOF

    skill_output="$(cd -- "$target_repo" && opencode debug skill 2>&1)"
    skill_status=$?
    if [ "$skill_status" -ne 0 ]; then fail debug_skills "status=$skill_status"; else
      missing=""
      for skill_name in $AC_SKILL_NAMES; do printf '%s\n' "$skill_output" | grep -q "$skill_name" || missing="$missing $skill_name"; done
      if [ -z "$missing" ]; then pass debug_skills "all=7"; else fail debug_skills "missing=$missing"; fi
    fi
  fi
fi

if [ "$failures" -eq 0 ]; then printf 'SUMMARY status=pass runtime=opencode quick=%s agents=11 skills=7\n' "$quick"; exit 0; fi
printf 'SUMMARY status=fail runtime=opencode failures=%s\n' "$failures"
exit 1
