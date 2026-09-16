#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-opencode.sh
. "$script_dir/lib-opencode.sh"

target_repo="${1:-$PWD}"
target_repo="$(ac_absolute_path "$target_repo")"
failures=0
artifact_enabled=false
[ -n "${AGENTS_COOKBOOK_RUN_DIR:-}" ] && artifact_enabled=true
pass() { printf 'CHECK name=%s status=pass %s\n' "$1" "${2:-}"; }
fail() { failures=$((failures + 1)); printf 'CHECK name=%s status=fail %s\n' "$1" "${2:-}"; }

command -v opencode >/dev/null 2>&1 || { fail command_opencode missing; exit 1; }

check_reviewer() {
  local reviewer="$1" skill="$2" output status
  output="$(cd -- "$target_repo" && opencode debug agent "$reviewer" 2>&1)" || status=$?
  status=${status:-0}
  if [ "$status" -ne 0 ]; then fail "debug_reviewer_$reviewer" "status=$status"; return; fi
  if printf '%s\n' "$output" | node -e '
const fs=require("fs");const skill=process.argv[1],artifact=process.argv[2]==="true";const raw=fs.readFileSync(0,"utf8"),start=raw.indexOf("{");if(start<0)process.exit(2);const a=JSON.parse(raw.slice(start)),t=a.tools||{},p=String(a.prompt||"");const expected={task:false,edit:false,write:false,bash:false,read:true,skill:true,review_artifact:artifact,review_artifact_read:false};if(Object.entries(expected).some(([k,v])=>t[k]!==v))process.exit(1);const loads=p.includes(`Load \`${skill}\` first`)||p.includes(`load \`${skill}\``);if(!loads)process.exit(1);
' "$skill" "$artifact_enabled"; then
    pass "debug_reviewer_$reviewer" "skill=$skill readonly=true artifact_mode=$artifact_enabled"
  else
    fail "debug_reviewer_$reviewer" "effective_contract_incorrect skill=$skill artifact_mode=$artifact_enabled"
  fi
}

while read -r reviewer skill model; do
  [ -n "$reviewer" ] || continue
  check_reviewer "$reviewer" "$skill"
done <<EOF
$AC_FLOW_REVIEWER_SKILL_MAP
$AC_STANDALONE_AGENT_SKILL_MAP
EOF

if [ "$failures" -eq 0 ]; then printf 'SUMMARY status=pass effective_reviewers=9 mandatory_flow_reviewers=8 artifact_mode=%s\n' "$artifact_enabled"; exit 0; fi
printf 'SUMMARY status=fail failures=%s\n' "$failures"; exit 1
