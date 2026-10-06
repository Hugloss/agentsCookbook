#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-opencode.sh
. "$script_dir/lib-opencode.sh"
repo_root="$(ac_repo_root_from_script "${BASH_SOURCE[0]}")"
agent_src_dir="$(ac_agent_source_dir "$repo_root")"; skill_src_dir="$(ac_skill_source_dir "$repo_root")"
AC_SKILL_NAMES="$(ac_skill_names "$repo_root")"
opencode_adapter="$(ac_opencode_artifact_adapter "$repo_root")"; pi_adapter="$(ac_pi_artifact_adapter "$repo_root")"
failures=0
pass() { printf 'CHECK name=%s status=pass %s\n' "$1" "${2:-}"; }
fail() { failures=$((failures + 1)); printf 'CHECK name=%s status=fail %s\n' "$1" "${2:-}"; }

description_of() { sed -n 's/^description:[[:space:]]*//p' "$1" | head -n 1; }
check_description() {
  local kind="$1" name="$2" file="$3" max="$4" value length
  value="$(description_of "$file")"; length=${#value}
  [ -n "$value" ] || { fail "${kind}_description_$name" missing; return; }
  [ "$length" -le "$max" ] || { fail "${kind}_description_$name" "chars=$length max=$max"; return; }
  pass "${kind}_description_$name" "chars=$length target=$AC_DESCRIPTION_TARGET max=$max"
}

[ -d "$agent_src_dir" ] || fail canonical_agents_dir "missing=$agent_src_dir"
[ -d "$skill_src_dir" ] || fail canonical_skills_dir "missing=$skill_src_dir"

actual_agents="$(find "$agent_src_dir" -maxdepth 1 -type f -name '*.md' -printf '%f\n' | sort)"
expected_agents="$(printf '%s\n' $AC_AGENT_FILES | sed '/^$/d' | sort)"
[ "$actual_agents" = "$expected_agents" ] && pass agent_registry_exact count=12 || fail agent_registry_exact mismatch
expected_skills="$(printf '%s\n' $AC_SKILL_NAMES | sed '/^$/d' | sort)"
expected_skill_count="$(printf '%s\n' $AC_SKILL_NAMES | sed '/^$/d' | wc -l)"

catalog_file="$skill_src_dir/README.md"
if [ -f "$catalog_file" ]; then
  catalog_skills="$(awk '/^## Overlap boundaries/{exit} /^- `[^`]+` —/{line=$0; sub(/^- `/,"",line); sub(/`.*/,"",line); print line}' "$catalog_file" | sort)"
  [ "$catalog_skills" = "$expected_skills" ] && pass skill_catalog_exact "count=$expected_skill_count" || fail skill_catalog_exact mismatch
else
  fail skill_catalog_exact missing
fi

stale_skill_name='plan-improvement''-scout'
if git -C "$repo_root" grep -q "$stale_skill_name" -- .; then fail removed_skill_reference "name=$stale_skill_name"; else pass removed_skill_reference absent=true; fi

for agent_file in $AC_AGENT_FILES; do check_description agent "${agent_file%.md}" "$agent_src_dir/$agent_file" "$AC_AGENT_DESCRIPTION_MAX"; done
for skill_name in $AC_SKILL_NAMES; do check_description skill "$skill_name" "$skill_src_dir/$skill_name/SKILL.md" "$AC_SKILL_DESCRIPTION_MAX"; done

flow_count="$(printf '%s\n' $AC_FLOW_REVIEWER_AGENT_FILES | sed '/^$/d' | wc -l)"
[ "$flow_count" -eq 9 ] && pass flow_reviewer_count count=9 || fail flow_reviewer_count "count=$flow_count"
catalog_reviewers="$(node -e 'const fs=require("fs");const list=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));if(!Array.isArray(list)||list.length!==9||new Set(list).size!==9||list.some(x=>typeof x!=="string"||!/^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$/.test(x)))process.exit(1);process.stdout.write(list.slice().sort().join("\n"))' "$repo_root/reviewers.json" 2>/dev/null)" || catalog_reviewers=""
flow_reviewers="$(printf '%s\n' $AC_FLOW_REVIEWER_AGENT_FILES | sed '/^$/d;s/\.md$//' | sort)"
[ -n "$catalog_reviewers" ] && [ "$catalog_reviewers" = "$flow_reviewers" ] && pass reviewer_catalog_exact count=9 || fail reviewer_catalog_exact mismatch

for skill_name in $AC_SKILL_NAMES; do
  file="$skill_src_dir/$skill_name/SKILL.md"
  if grep -Eqi 'use only for the .*reviewer role|must be invoked by ping-pong|requires? .*run store' "$file"; then fail "standalone_skill_$skill_name" flow_specific_dependency; else pass "standalone_skill_$skill_name" independent=true; fi
done

for reviewer_file in $AC_FLOW_REVIEWER_AGENT_FILES; do
  file="$agent_src_dir/$reviewer_file"; reviewer_name="${reviewer_file%.md}"
  reviewer_skill="$(sed -n 's/^skills: \[\([^]]*\)\]$/\1/p' "$file" | head -n 1)"
  if [ -n "$reviewer_skill" ] && [ -f "$skill_src_dir/$reviewer_skill/SKILL.md" ] && grep -q '^## BUILD REVIEW MODE$' "$skill_src_dir/$reviewer_skill/SKILL.md"; then
    pass "build_review_contract_$reviewer_name" "skill=$reviewer_skill"
  else
    fail "build_review_contract_$reviewer_name" "skill=${reviewer_skill:-missing}"
  fi
done

build_master="$agent_src_dir/ping-ping-build.md"
if grep -q '^  skill:' "$build_master"; then fail build_master_skill_authority direct_skill_permission_present; else pass build_master_skill_authority reviewer_owned=true; fi
if grep -q '^## Final polish$' "$build_master" && grep -Fq '`## Final Polish`' "$build_master"; then pass build_final_polish_contract bounded=true; else fail build_final_polish_contract missing; fi

for reviewer_file in $AC_FLOW_REVIEWER_AGENT_FILES $AC_STANDALONE_AGENT_FILES; do
  file="$agent_src_dir/$reviewer_file"; name="${reviewer_file%.md}"
  if grep -Fq '  "*": deny' "$file" && grep -q '^  review_artifact: allow$' "$file" && ! grep -q '^  review_artifact_read: allow$' "$file"; then pass "reviewer_artifact_authority_$name" deny_by_default=true; else fail "reviewer_artifact_authority_$name" authority_mismatch; fi
done
for primary_file in $AC_PRIMARY_AGENT_FILES; do
  file="$agent_src_dir/$primary_file"; name="${primary_file%.md}"
  if grep -Fq '  "*": deny' "$file" && grep -q '^  review_artifact_read: allow$' "$file" && ! grep -q '^  review_artifact: allow$' "$file"; then pass "primary_artifact_authority_$name" selective_read=true; else fail "primary_artifact_authority_$name" authority_mismatch; fi
done

for pair in "opencode:$opencode_adapter" "pi:$pi_adapter"; do
  runtime="${pair%%:*}"; file="${pair#*:}"
  if [ ! -f "$file" ]; then fail "artifact_adapter_$runtime" missing; continue; fi
  if grep -Fq 'AGENTS_COOKBOOK_RUN_DIR' "$file" && grep -Fq 'flag: "wx"' "$file" && grep -Fq 'review_artifact_read' "$file" && ! grep -Eq 'path:[[:space:]]*(Type\.|tool\.schema)' "$file"; then pass "artifact_adapter_$runtime" bounded_root=true no_arbitrary_path=true no_overwrite=true; else fail "artifact_adapter_$runtime" safety_contract_mismatch; fi
done

# Exercise the OpenCode plugin with a foreign working directory and a hostile
# project-local reviewer list. The adapter must use only its cookbook catalog.
opencode_boundary_output="$(node "$repo_root/scripts/check-opencode-reviewer-boundary.js" 2>&1)"; opencode_boundary_status=$?
printf '%s\n' "$opencode_boundary_output"
[ "$opencode_boundary_status" -eq 0 ] || fail opencode_reviewer_runtime_boundary "status=$opencode_boundary_status"

# This Pi family exposes TypeBox through the `typebox` peer used by
# pi-open-agents. Pin the import contract so syntax-only checks cannot hide a
# dependency that the runtime will not resolve.
if grep -Fq 'import { Type } from "typebox"' "$pi_adapter" && ! grep -Fq '@sinclair/typebox' "$pi_adapter"; then
  pass pi_adapter_typebox_dependency import=typebox
else
  fail pi_adapter_typebox_dependency expected='import { Type } from "typebox"'
fi

# pi-open-agents cannot derive a finite child --tools whitelist from a
# wildcard permission block. Canonical reviewers intentionally keep wildcard
# deny-by-default for OpenCode, so the Pi adapter owns an explicit child-process
# boundary. Prove that contract independently of the runtime package.
pi_boundary_output="$(node "$repo_root/scripts/check-pi-reviewer-boundary.js" 2>&1)"; pi_boundary_status=$?
printf '%s\n' "$pi_boundary_output"
[ "$pi_boundary_status" -eq 0 ] || fail pi_reviewer_runtime_boundary "status=$pi_boundary_status"

if [ -d "$repo_root/.agents/skills" ] || [ -d "$repo_root/.opencode/agents" ]; then fail hidden_source_layout present; else pass hidden_source_layout absent; fi

if [ "$failures" -eq 0 ]; then printf 'SUMMARY status=pass agents=12 skills=%s adapters=2 mandatory_flow_reviewers=9\n' "$expected_skill_count"; exit 0; fi
printf 'SUMMARY status=fail failures=%s\n' "$failures"; exit 1
