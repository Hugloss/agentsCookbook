#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-opencode.sh
. "$script_dir/lib-opencode.sh"

target_repo="${1:-$PWD}"
target_repo="$(ac_absolute_path "$target_repo")"
failures=0
pass() { printf 'CHECK name=%s status=pass %s\n' "$1" "${2:-}"; }
fail() { failures=$((failures + 1)); printf 'CHECK name=%s status=fail %s\n' "$1" "${2:-}"; }

command -v opencode >/dev/null 2>&1 || { fail command_opencode missing; exit 1; }

check_reviewer() {
  local reviewer="$1" skill="$2" output status
  output="$(cd -- "$target_repo" && opencode debug agent "$reviewer" 2>&1)" || status=$?
  status=${status:-0}
  if [ "$status" -ne 0 ]; then fail "debug_reviewer_$reviewer" "status=$status"; return; fi
  if printf '%s\n' "$output" | node -e '
const fs=require("fs");
const skill=process.argv[1];
const raw=fs.readFileSync(0,"utf8");
const start=raw.indexOf("{"); if(start<0) process.exit(2);
const a=JSON.parse(raw.slice(start)); const t=a.tools||{}; const p=String(a.prompt||"");
const readOnly=t.task===false && t.edit===false && t.write===false && t.bash===false && t.read===true && t.skill===true;
const loads=p.includes(`Load \`${skill}\` first`) || p.includes(`load \`${skill}\``);
if(!readOnly || !loads) process.exit(1);
' "$skill"; then
    pass "debug_reviewer_$reviewer" "skill=$skill tools=readonly"
  else
    fail "debug_reviewer_$reviewer" "effective_contract_incorrect skill=$skill"
  fi
}

while read -r reviewer skill model; do
  [ -n "$reviewer" ] || continue
  check_reviewer "$reviewer" "$skill"
done <<EOF
$AC_FLOW_REVIEWER_SKILL_MAP
$AC_STANDALONE_AGENT_SKILL_MAP
EOF

if [ "$failures" -eq 0 ]; then printf 'SUMMARY status=pass effective_reviewers=9 mandatory_flow_reviewers=8\n'; exit 0; fi
printf 'SUMMARY status=fail failures=%s\n' "$failures"
exit 1
