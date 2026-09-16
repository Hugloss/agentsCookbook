#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-opencode.sh
. "$script_dir/lib-opencode.sh"
repo_root="$(ac_repo_root_from_script "${BASH_SOURCE[0]}")"
agent_src_dir="$(ac_agent_source_dir "$repo_root")"; skill_src_dir="$(ac_skill_source_dir "$repo_root")"
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
actual_skills="$(find "$skill_src_dir" -mindepth 2 -maxdepth 2 -type f -name SKILL.md -printf '%h\n' | xargs -r -n1 basename | sort)"
expected_skills="$(printf '%s\n' $AC_SKILL_NAMES | sed '/^$/d' | sort)"
[ "$actual_skills" = "$expected_skills" ] && pass skill_registry_exact count=8 || fail skill_registry_exact mismatch

for agent_file in $AC_AGENT_FILES; do check_description agent "${agent_file%.md}" "$agent_src_dir/$agent_file" "$AC_AGENT_DESCRIPTION_MAX"; done
for skill_name in $AC_SKILL_NAMES; do check_description skill "$skill_name" "$skill_src_dir/$skill_name/SKILL.md" "$AC_SKILL_DESCRIPTION_MAX"; done

flow_count="$(printf '%s\n' $AC_FLOW_REVIEWER_AGENT_FILES | sed '/^$/d' | wc -l)"
[ "$flow_count" -eq 8 ] && pass flow_reviewer_count count=8 || fail flow_reviewer_count "count=$flow_count"
if printf '%s\n' $AC_FLOW_REVIEWER_AGENT_FILES | grep -qx 'code-performance-optimization-auditor.md'; then fail standalone_flow_leak performance_auditor_in_mandatory_gate; else pass standalone_flow_leak absent; fi

for skill_name in $AC_SKILL_NAMES; do
  file="$skill_src_dir/$skill_name/SKILL.md"
  if grep -Eqi 'use only for the .*reviewer role|must be invoked by ping-pong|requires? .*run store' "$file"; then fail "standalone_skill_$skill_name" flow_specific_dependency; else pass "standalone_skill_$skill_name" independent=true; fi
done

# All reviewer actors are deny-by-default. The only write-shaped capability
# they receive is the bounded review_artifact tool; generic project write/edit
# remains denied by the wildcard. Primary agents may only read named artifacts.
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

if [ -d "$repo_root/.agents/skills" ] || [ -d "$repo_root/.opencode/agents" ]; then fail hidden_source_layout present; else pass hidden_source_layout absent; fi

if [ "$failures" -eq 0 ]; then printf 'SUMMARY status=pass agents=12 skills=8 adapters=2 mandatory_flow_reviewers=8\n'; exit 0; fi
printf 'SUMMARY status=fail failures=%s\n' "$failures"; exit 1
