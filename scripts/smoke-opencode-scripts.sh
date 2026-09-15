#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/.." && pwd -P)"
pass() { printf 'SMOKE name=%s status=pass %s\n' "$1" "${2:-}"; }
fail() { printf 'SMOKE name=%s status=fail %s\n' "$1" "${2:-}" >&2; exit 1; }

assert_link() {
  local name="$1" path="$2" expected="$3" resolved
  [ -L "$path" ] || fail "$name" "missing=$path"
  resolved="$(realpath -- "$path" 2>/dev/null || true)"
  [ "$resolved" = "$expected" ] || fail "$name" "resolved=${resolved:-<unresolved>} expected=$expected"
  pass "$name"
}

create_fake_session_db() {
  local path="$1" session_id="$2" agent="$3" directory="$4"
  sqlite3 "$path" <<SQL
CREATE TABLE session (id TEXT PRIMARY KEY,parent_id TEXT,title TEXT,agent TEXT,directory TEXT,time_created INTEGER,time_updated INTEGER);
CREATE TABLE session_message (id TEXT PRIMARY KEY,session_id TEXT,type TEXT,time_created INTEGER,time_updated INTEGER,data TEXT);
CREATE TABLE message (id TEXT PRIMARY KEY,session_id TEXT,time_created INTEGER,time_updated INTEGER,data TEXT);
CREATE TABLE part (id TEXT PRIMARY KEY,session_id TEXT,message_id TEXT,time_created INTEGER,time_updated INTEGER,data TEXT);
INSERT INTO session VALUES ('$session_id',NULL,'smoke','$agent','$directory',1710000000000,1710000000000);
SQL
}

temp_root="$(mktemp -d "${TMPDIR:-/tmp}/agents-cookbook-smoke.XXXXXX")"
cleanup() { rm -rf "$temp_root"; }
trap cleanup EXIT
global_dir="$temp_root/global opencode"
pi_dir="$temp_root/pi agent"
skills_dir="$temp_root/shared skills"
target_dir="$temp_root/target repo"
mkdir -p "$target_dir" "$global_dir/prompts" "$global_dir/skills"

# Simulate broken links from the retired prompts/.opencode-skills layout.
ln -s "$repo_root/.opencode/prompts/plan-improver.md" "$global_dir/prompts/plan-improver.md"
ln -s "$repo_root/.opencode/skills/plan-improvement-scout" "$global_dir/skills/plan-improvement-scout"

"$repo_root/scripts/link-opencode-local.sh" --dry-run --global-dir "$global_dir" --pi-agent-dir "$pi_dir" --shared-skill-dir "$skills_dir" >/dev/null
pass link_dry_run
"$repo_root/scripts/link-opencode-local.sh" --global-dir "$global_dir" --pi-agent-dir "$pi_dir" --shared-skill-dir "$skills_dir" >/dev/null

assert_link opencode_primary "$global_dir/agents/ping-pong-plan.md" "$repo_root/.opencode/agents/ping-pong-plan.md"
assert_link opencode_reviewer "$global_dir/agents/plan-improver-model2.md" "$repo_root/.opencode/agents/plan-improver-model2.md"
assert_link opencode_coverage_reviewer "$global_dir/agents/plan-coverage-reviewer.md" "$repo_root/.opencode/agents/plan-coverage-reviewer.md"
assert_link pi_primary "$pi_dir/agents/ping-ping-build.md" "$repo_root/.opencode/agents/ping-ping-build.md"
assert_link pi_reviewer "$pi_dir/agents/plan-contract-checker.md" "$repo_root/.opencode/agents/plan-contract-checker.md"
assert_link shared_skill "$skills_dir/plan-improvement-scout" "$repo_root/.agents/skills/plan-improvement-scout"
assert_link coverage_skill "$skills_dir/coverage-design-review" "$repo_root/.agents/skills/coverage-design-review"
[ ! -L "$global_dir/prompts/plan-improver.md" ] || fail legacy_prompt_cleanup
[ ! -L "$global_dir/skills/plan-improvement-scout" ] || fail legacy_skill_cleanup
pass legacy_links_removed

"$repo_root/scripts/preflight-opencode-ping-pong.sh" --quick --global-dir "$global_dir" --shared-skill-dir "$skills_dir" "$target_dir" >/dev/null
pass opencode_quick_preflight

# Provide a deterministic local Pi/plugin fixture for the Pi preflight.
mkdir -p "$pi_dir/npm/node_modules/pi-open-agents" "$temp_root/bin"
printf '{"version":"0.1.20"}\n' >"$pi_dir/npm/node_modules/pi-open-agents/package.json"
printf '{"extensions":["npm:pi-open-agents@0.1.20"]}\n' >"$pi_dir/settings.json"
printf '#!/usr/bin/env bash\nprintf "pi 0.85.0\\n"\n' >"$temp_root/bin/pi"
chmod +x "$temp_root/bin/pi"
PATH="$temp_root/bin:$PATH" "$repo_root/scripts/preflight-pi-ping-pong.sh" --pi-agent-dir "$pi_dir" --shared-skill-dir "$skills_dir" "$target_dir" >/dev/null
pass pi_preflight

"$repo_root/scripts/link-opencode-local.sh" --global-dir "$global_dir" --pi-agent-dir "$pi_dir" --shared-skill-dir "$skills_dir" | grep 'status=already_correct' >/dev/null
pass link_idempotent

force_dir="$temp_root/force"
mkdir -p "$force_dir/agents"
printf 'conflict\n' >"$force_dir/agents/ping-pong-plan.md"
if "$repo_root/scripts/link-opencode-local.sh" --global-dir "$force_dir" --pi-agent-dir "$temp_root/force-pi" --shared-skill-dir "$temp_root/force-skills" >/dev/null 2>&1; then fail conflict_without_force; fi
pass conflict_without_force
"$repo_root/scripts/link-opencode-local.sh" --force --global-dir "$force_dir" --pi-agent-dir "$temp_root/force-pi" --shared-skill-dir "$temp_root/force-skills" >/dev/null
find "$force_dir/agents" -name 'ping-pong-plan.md.agents-cookbook-backup-*' -print -quit | grep . >/dev/null
pass force_backup

command -v sqlite3 >/dev/null 2>&1 || fail sqlite3_missing
router_db="$temp_root/router.db"
create_fake_session_db "$router_db" ses_router_smoke subagent-router "$target_dir"
router_output="$("$repo_root/scripts/check-opencode-session.sh" --scope session --expect-no-subagent --db "$router_db" ses_router_smoke 2>&1)"
printf '%s\n' "$router_output" | grep 'ROUTER_SUBAGENT name=none status=pass task_calls=0' >/dev/null
pass checker_opencode_task_schema

node - "$temp_root" <<'NODE'
const fs = require('fs');
const path = require('path');
const root = process.argv[2];
const reviewers = [
  ['plan-improver-model2', 'plan-improvement-scout'],
  ['plan-improver-model3', 'plan-improvement-scout'],
  ['plan-validation-designer', 'validation-gap-finder'],
  ['plan-coverage-reviewer', 'coverage-design-review'],
  ['plan-red-team-gate', 'red-team-leftover-gate'],
  ['plan-implementation-simulator', 'implementation-dry-run'],
  ['plan-fact-auditor', 'fact-grounding-auditor'],
  ['plan-contract-checker', 'plan-contract-guard'],
];

function write(name, options = {}) {
  const entries = [
    { type: 'session', version: 3, id: `session-${name}`, cwd: root },
    { type: 'message', id: 'user', parentId: null, message: { role: 'user', content: [{ type: 'text', text: 'plan this' }] } },
  ];
  let parent = 'user';
  if (options.zero) {
    entries.push({ type: 'message', id: 'final', parentId: parent, message: { role: 'assistant', content: [{ type: 'text', text: 'all eight reviewers succeeded' }] } });
  } else {
    reviewers.forEach(([agent, skill], index) => {
      const callId = `call-${index}`;
      const assistantId = `assistant-${index}`;
      const resultId = `result-${index}`;
      entries.push({
        type: 'message', id: assistantId, parentId: parent,
        message: { role: 'assistant', content: [{ type: 'toolCall', id: callId, name: 'subagent', arguments: { agent, task: 'review' } }] },
      });
      const failed = options.failedFirst && index === 0;
      const wrongSkill = options.missingSkill && index === 0;
      entries.push({
        type: 'message', id: resultId, parentId: assistantId,
        message: {
          role: 'toolResult', toolCallId: callId, toolName: 'subagent', isError: failed,
          content: [{ type: 'text', text: failed ? 'review failed' : 'review complete' }],
          details: {
            agent, status: failed ? 'error' : 'done', output: failed ? '' : '# Review report',
            tools: failed ? [] : [{ name: wrongSkill ? 'grep' : 'read', args: wrongSkill ? { pattern: 'x' } : { path: `/skills/${skill}/SKILL.md` }, status: 'done' }],
          },
        },
      });
      parent = resultId;
    });
  }
  fs.writeFileSync(path.join(root, `pi-${name}.jsonl`), `${entries.map((entry) => JSON.stringify(entry)).join('\n')}\n`);
}

write('success');
write('zero', { zero: true });
write('failed-continuation', { failedFirst: true });
write('missing-skill', { missingSkill: true });
NODE

"$repo_root/scripts/check-pi-session.js" --scope session "$temp_root/pi-success.jsonl" >/dev/null
pass checker_pi_complete_trace

if "$repo_root/scripts/check-pi-session.js" --scope session "$temp_root/pi-zero.jsonl" >/dev/null 2>&1; then fail checker_pi_dishonest_summary; fi
pass checker_pi_dishonest_summary

set +e
pi_failed_output="$("$repo_root/scripts/check-pi-session.js" --scope session "$temp_root/pi-failed-continuation.jsonl" 2>&1)"
pi_failed_status=$?
set -e
[ "$pi_failed_status" -eq 1 ] || fail checker_pi_failed_continuation "status=$pi_failed_status"
printf '%s\n' "$pi_failed_output" | grep 'REVIEWER name=plan-improver-model2 invocation=failed' >/dev/null
printf '%s\n' "$pi_failed_output" | grep 'REVIEWER name=plan-contract-checker invocation=succeeded count=1 skill=plan-contract-guard skill_loaded=yes' >/dev/null
pass checker_pi_failed_continuation

set +e
pi_skill_output="$("$repo_root/scripts/check-pi-session.js" --scope session "$temp_root/pi-missing-skill.jsonl" 2>&1)"
pi_skill_status=$?
set -e
[ "$pi_skill_status" -eq 1 ] || fail checker_pi_missing_skill "status=$pi_skill_status"
printf '%s\n' "$pi_skill_output" | grep 'REVIEWER name=plan-improver-model2 invocation=succeeded count=1 skill=plan-improvement-scout skill_loaded=no' >/dev/null
pass checker_pi_missing_skill

node --check "$repo_root/scripts/run-opencode-benchmarks.js"
pass benchmark_runner_syntax

# Unlink must remove owned links while preserving user-owned paths.
rm -- "$global_dir/agents/ping-pong-plan.md"
printf 'user file\n' >"$global_dir/agents/ping-pong-plan.md"
ln -s "$temp_root" "$global_dir/agents/unrelated.md"
"$repo_root/scripts/unlink-opencode-local.sh" --global-dir "$global_dir" --pi-agent-dir "$pi_dir" --shared-skill-dir "$skills_dir" >/dev/null
[ -f "$global_dir/agents/ping-pong-plan.md" ] || fail unlink_preserves_real_file
[ -L "$global_dir/agents/unrelated.md" ] || fail unlink_preserves_unrelated_link
[ ! -e "$pi_dir/agents/plan-contract-checker.md" ] && [ ! -L "$pi_dir/agents/plan-contract-checker.md" ] || fail unlink_removes_pi_agent
[ ! -e "$skills_dir/plan-improvement-scout" ] && [ ! -L "$skills_dir/plan-improvement-scout" ] || fail unlink_removes_shared_skill
pass unlink_safe
"$repo_root/scripts/unlink-opencode-local.sh" --global-dir "$global_dir" --pi-agent-dir "$pi_dir" --shared-skill-dir "$skills_dir" >/dev/null
pass unlink_idempotent

printf 'SUMMARY status=pass\n'
