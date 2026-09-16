#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/.." && pwd -P)"
# shellcheck source=scripts/lib-opencode.sh
. "$script_dir/lib-opencode.sh"

pass() { printf 'SMOKE name=%s status=pass %s\n' "$1" "${2:-}"; }
fail() { printf 'SMOKE name=%s status=fail %s\n' "$1" "${2:-}" >&2; exit 1; }
assert_link() {
  local name="$1" candidate="$2" expected="$3" resolved
  [ -L "$candidate" ] || fail "$name" "missing=$candidate"
  resolved="$(realpath -- "$candidate" 2>/dev/null || true)"
  [ "$resolved" = "$expected" ] || fail "$name" "resolved=${resolved:-<unresolved>} expected=$expected"
  pass "$name"
}

temp_root="$(mktemp -d "${TMPDIR:-/tmp}/agents-cookbook-smoke.XXXXXX")"
cleanup() { rm -rf "$temp_root"; }
trap cleanup EXIT

global_dir="$temp_root/global opencode"; pi_dir="$temp_root/pi agent"; skills_dir="$temp_root/shared skills"; target_dir="$temp_root/target repo"
mkdir -p "$target_dir" "$global_dir/agents" "$skills_dir" "$temp_root/bin"

ln -s "$repo_root/.opencode/agents/ping-pong-plan.md" "$global_dir/agents/ping-pong-plan.md"
ln -s "$repo_root/.agents/skills/plan-improvement-scout" "$skills_dir/plan-improvement-scout"
"$repo_root/scripts/link-opencode-local.sh" --dry-run --global-dir "$global_dir" --pi-agent-dir "$pi_dir" --shared-skill-dir "$skills_dir" >/dev/null
pass link_dry_run
"$repo_root/scripts/link-opencode-local.sh" --global-dir "$global_dir" --pi-agent-dir "$pi_dir" --shared-skill-dir "$skills_dir" >/dev/null

assert_link opencode_primary "$global_dir/agents/ping-pong-plan.md" "$repo_root/agents/ping-pong-plan.md"
assert_link opencode_reviewer "$global_dir/agents/plan-coverage-reviewer.md" "$repo_root/agents/plan-coverage-reviewer.md"
assert_link opencode_standalone "$global_dir/agents/code-performance-optimization-auditor.md" "$repo_root/agents/code-performance-optimization-auditor.md"
assert_link pi_primary "$pi_dir/agents/ping-ping-build.md" "$repo_root/agents/ping-ping-build.md"
assert_link pi_reviewer "$pi_dir/agents/plan-contract-checker.md" "$repo_root/agents/plan-contract-checker.md"
assert_link shared_skill "$skills_dir/plan-improvement-scout" "$repo_root/skills/plan-improvement-scout"
assert_link performance_skill "$skills_dir/code-performance-optimization-audit" "$repo_root/skills/code-performance-optimization-audit"
assert_link opencode_artifact_plugin "$global_dir/plugins/$AC_OPENCODE_ARTIFACT_PLUGIN" "$repo_root/adapters/opencode/review-artifact.js"
assert_link pi_artifact_extension "$pi_dir/extensions/$AC_PI_ARTIFACT_EXTENSION" "$repo_root/adapters/pi/review-artifact.js"

"$repo_root/scripts/preflight-opencode-ping-pong.sh" --quick --global-dir "$global_dir" --shared-skill-dir "$skills_dir" "$target_dir" >/dev/null
pass opencode_quick_preflight

mkdir -p "$pi_dir/npm/node_modules/pi-open-agents"
printf '{"version":"0.1.20"}\n' >"$pi_dir/npm/node_modules/pi-open-agents/package.json"
printf '{"extensions":["npm:pi-open-agents@0.1.20"]}\n' >"$pi_dir/settings.json"
printf '#!/usr/bin/env bash\nprintf "pi 0.85.0\\n"\n' >"$temp_root/bin/pi"; chmod +x "$temp_root/bin/pi"
PATH="$temp_root/bin:$PATH" "$repo_root/scripts/preflight-pi-ping-pong.sh" --pi-agent-dir "$pi_dir" --shared-skill-dir "$skills_dir" "$target_dir" >/dev/null
pass pi_preflight

"$repo_root/scripts/link-opencode-local.sh" --global-dir "$global_dir" --pi-agent-dir "$pi_dir" --shared-skill-dir "$skills_dir" | grep 'status=already_correct' >/dev/null
pass link_idempotent

force_dir="$temp_root/force"; mkdir -p "$force_dir/agents"; printf 'conflict\n' >"$force_dir/agents/ping-pong-plan.md"
if "$repo_root/scripts/link-opencode-local.sh" --global-dir "$force_dir" --pi-agent-dir "$temp_root/force-pi" --shared-skill-dir "$temp_root/force-skills" >/dev/null 2>&1; then fail conflict_without_force; fi
pass conflict_without_force
"$repo_root/scripts/link-opencode-local.sh" --force --global-dir "$force_dir" --pi-agent-dir "$temp_root/force-pi" --shared-skill-dir "$temp_root/force-skills" >/dev/null
find "$force_dir/agents" -name 'ping-pong-plan.md.agents-cookbook-backup-*' -print -quit | grep . >/dev/null
pass force_backup

[ "$(printf '%s\n' $AC_AGENT_FILES | sed '/^$/d' | wc -l)" -eq 12 ] || fail agent_registry_count
[ "$(printf '%s\n' $AC_SKILL_NAMES | sed '/^$/d' | wc -l)" -eq 8 ] || fail skill_registry_count
[ "$(printf '%s\n' $AC_FLOW_REVIEWER_AGENT_FILES | sed '/^$/d' | wc -l)" -eq 8 ] || fail flow_reviewer_count
! printf '%s\n' $AC_FLOW_REVIEWER_AGENT_FILES | grep -qx 'code-performance-optimization-auditor.md' || fail standalone_leaked_into_flow_gate
pass registry_boundaries

# Adapter sources must remain opt-in, bounded, non-overwriting, and path-free at
# their model-facing schema boundary.
for adapter in "$repo_root/adapters/opencode/review-artifact.js" "$repo_root/adapters/pi/review-artifact.js"; do
  grep -Fq 'AGENTS_COOKBOOK_RUN_DIR' "$adapter" || fail artifact_adapter_env "file=$adapter"
  grep -Fq 'flag: "wx"' "$adapter" || fail artifact_adapter_no_overwrite "file=$adapter"
  ! grep -Eq 'path:[[:space:]]*(Type\.|tool\.schema)' "$adapter" || fail artifact_adapter_arbitrary_path "file=$adapter"
done
pass artifact_adapter_static_safety

# Post-run fallback exporter remains available when native artifact mode was not
# enabled for the original run.
pi_trace="$temp_root/pi-trace.jsonl"; opencode_trace="$temp_root/opencode-export.json"; pi_artifacts="$temp_root/pi-artifacts"; opencode_artifacts="$temp_root/opencode-artifacts"
node - "$pi_trace" "$opencode_trace" <<'NODE'
const fs=require('fs');const [piPath,ocPath]=process.argv.slice(2);
const pi=[{type:'session',version:3,id:'session-artifacts',cwd:'/repo'},{type:'message',id:'a1',parentId:'u1',message:{role:'assistant',content:[{type:'toolCall',id:'call-1',name:'subagent',arguments:{agent:'plan-coverage-reviewer',task:'review'}}]}},{type:'message',id:'r1',parentId:'a1',message:{role:'toolResult',toolCallId:'call-1',toolName:'subagent',isError:false,content:[{type:'text',text:'review complete'}],details:{agent:'plan-coverage-reviewer',status:'done',output:'# Coverage Design Review\n\n## Meaningful Coverage Gaps\n\nOne realistic gap.'}}},{type:'message',id:'a2',parentId:'r1',message:{role:'assistant',content:[{type:'toolCall',id:'call-2',name:'subagent',arguments:{agent:'plan-red-team-gate',task:'review'}}]}},{type:'message',id:'r2',parentId:'a2',message:{role:'toolResult',toolCallId:'call-2',toolName:'subagent',isError:true,content:[{type:'text',text:'model unavailable'}],details:{agent:'plan-red-team-gate',status:'error',output:''}}}];
fs.writeFileSync(piPath,`${pi.map(JSON.stringify).join('\n')}\n`);
const oc={messages:[{info:{role:'assistant'},parts:[{type:'tool',tool:'task',id:'task-1',state:{status:'completed',input:{subagent_type:'plan-fact-auditor'},output:'# Fact Audit Report\n\n## Fact Audit Verdict\n\nPass'}}]}]};fs.writeFileSync(ocPath,`${JSON.stringify(oc)}\n`);
NODE
node "$repo_root/scripts/export-review-artifacts.js" --runtime pi --input "$pi_trace" --out "$pi_artifacts" --run-id smoke-pi --subject-id plan-v2 --subject-revision 2 >/dev/null
node "$repo_root/scripts/export-review-artifacts.js" --runtime opencode --input "$opencode_trace" --out "$opencode_artifacts" --run-id smoke-opencode >/dev/null
node - "$pi_artifacts" "$opencode_artifacts" <<'NODE'
const fs=require('fs'),path=require('path');const [piDir,ocDir]=process.argv.slice(2);const pi=JSON.parse(fs.readFileSync(path.join(piDir,'manifest.json'),'utf8')),oc=JSON.parse(fs.readFileSync(path.join(ocDir,'manifest.json'),'utf8'));if(pi.counts.total!==2||pi.counts.succeeded!==1||pi.counts.failed!==1)process.exit(1);if(pi.subject.id!=='plan-v2'||pi.subject.revision!=='2')process.exit(1);const receipt=JSON.parse(fs.readFileSync(path.join(piDir,pi.reviewers[0].receipt),'utf8'));if(!receipt.output_sha256||receipt.reviewer!=='plan-coverage-reviewer'||!receipt.headings.includes('Coverage Design Review'))process.exit(1);if(oc.counts.total!==1||oc.counts.succeeded!==1||oc.reviewers[0].reviewer!=='plan-fact-auditor')process.exit(1);
NODE
pass review_artifact_export

for script in "$repo_root"/scripts/*.sh; do bash -n "$script"; done
node --check "$repo_root/scripts/check-pi-session.js"
node --check "$repo_root/scripts/run-opencode-benchmarks.js"
node --check "$repo_root/scripts/export-review-artifacts.js"
node --check "$repo_root/adapters/opencode/review-artifact.js"
node --check "$repo_root/adapters/pi/review-artifact.js"
pass script_syntax

rm -- "$global_dir/agents/ping-pong-plan.md"; printf 'user file\n' >"$global_dir/agents/ping-pong-plan.md"; ln -s "$temp_root" "$global_dir/agents/unrelated.md"
"$repo_root/scripts/unlink-opencode-local.sh" --global-dir "$global_dir" --pi-agent-dir "$pi_dir" --shared-skill-dir "$skills_dir" >/dev/null
[ -f "$global_dir/agents/ping-pong-plan.md" ] || fail unlink_preserves_real_file
[ -L "$global_dir/agents/unrelated.md" ] || fail unlink_preserves_unrelated_link
[ ! -e "$pi_dir/agents/plan-contract-checker.md" ] && [ ! -L "$pi_dir/agents/plan-contract-checker.md" ] || fail unlink_removes_pi_agent
[ ! -e "$skills_dir/plan-improvement-scout" ] && [ ! -L "$skills_dir/plan-improvement-scout" ] || fail unlink_removes_shared_skill
[ ! -e "$global_dir/plugins/$AC_OPENCODE_ARTIFACT_PLUGIN" ] && [ ! -L "$global_dir/plugins/$AC_OPENCODE_ARTIFACT_PLUGIN" ] || fail unlink_removes_opencode_adapter
[ ! -e "$pi_dir/extensions/$AC_PI_ARTIFACT_EXTENSION" ] && [ ! -L "$pi_dir/extensions/$AC_PI_ARTIFACT_EXTENSION" ] || fail unlink_removes_pi_adapter
pass unlink_safe

printf 'SUMMARY status=pass agents=12 skills=8 adapters=2 mandatory_flow_reviewers=8\n'
