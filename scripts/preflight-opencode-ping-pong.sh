#!/usr/bin/env bash
set -u

usage() {
  cat <<'USAGE'
Usage: scripts/preflight-opencode-ping-pong.sh [--global-dir DIR] [target-repo]

Run read-only checks before starting a long ping-pong-plan or ping-ping-build
OpenCode session. The target repo defaults to the current directory.

Options:
  --global-dir DIR   OpenCode config dir. Defaults to ${XDG_CONFIG_HOME:-$HOME/.config}/opencode.
  -h, --help         Show this help.

This script does not create, edit, or remove files.
USAGE
}

failures=0
debug_retries="${OPENCODE_PREFLIGHT_RETRIES:-3}"
debug_retry_sleep="${OPENCODE_PREFLIGHT_RETRY_SLEEP:-1}"

pass() {
  printf 'CHECK name=%s status=pass %s\n' "$1" "${2:-}"
}

fail() {
  failures=$((failures + 1))
  printf 'CHECK name=%s status=fail %s\n' "$1" "${2:-}"
}

info() {
  printf 'INFO %s\n' "$*"
}

default_global_dir() {
  if [ -n "${XDG_CONFIG_HOME:-}" ]; then
    printf '%s/opencode\n' "$XDG_CONFIG_HOME"
    return 0
  fi
  if [ -n "${HOME:-}" ]; then
    printf '%s/.config/opencode\n' "$HOME"
    return 0
  fi
  return 1
}

absolute_path() {
  local path="$1"
  case "$path" in
    /*)
      printf '%s\n' "$path"
      ;;
    *)
      printf '%s/%s\n' "$PWD" "$path"
      ;;
  esac
}

resolve_dir() {
  local path="$1"
  if [ ! -d "$path" ]; then
    return 1
  fi
  cd -- "$path" 2>/dev/null && pwd -P
}

check_command() {
  local command_name="$1"
  if command -v "$command_name" >/dev/null 2>&1; then
    pass "command_$command_name" "path=$(command -v "$command_name")"
  else
    fail "command_$command_name" "missing"
  fi
}

check_symlink_target() {
  local name="$1"
  local dest="$2"
  local expected="$3"
  local resolved

  if [ ! -L "$dest" ]; then
    fail "$name" "path=$dest expected_symlink_to=$expected"
    return
  fi

  resolved="$(realpath -- "$dest" 2>/dev/null || true)"
  if [ "$resolved" = "$expected" ]; then
    pass "$name" "path=$dest target=$expected"
  else
    fail "$name" "path=$dest resolved=${resolved:-<unresolved>} expected=$expected"
  fi
}

run_debug_agent() {
  local target_dir="$1"
  local agent_name="$2"
  local attempt=1
  local output status

  while [ "$attempt" -le "$debug_retries" ]; do
    output="$(cd -- "$target_dir" && opencode debug agent "$agent_name" 2>&1)"
    status="$?"
    if [ "$status" -eq 0 ]; then
      printf '%s\n' "$output"
      return 0
    fi

    if [ "$attempt" -lt "$debug_retries" ]; then
      printf 'INFO debug_retry agent=%s attempt=%s status=%s\n' "$agent_name" "$attempt" "$status" >&2
      sleep "$debug_retry_sleep"
    fi

    attempt=$((attempt + 1))
  done

  case "$output" in
    *"PRAGMA wal_checkpoint"*)
      output="$output
Hint: OpenCode reported a database checkpoint failure. Close other running OpenCode sessions and rerun this preflight."
      ;;
  esac

  printf '%s\n' "$output"
  return "$status"
}

check_debug_prompt() {
  local target_dir="$1"
  local agent_name="$2"
  local check_name="$3"
  local output

  if ! output="$(run_debug_agent "$target_dir" "$agent_name")"; then
    fail "$check_name" "agent=$agent_name debug_failed"
    printf '%s\n' "$output" >&2
    return
  fi

  if printf '%s\n' "$output" \
    | node -e '
const fs = require("fs");
const raw = fs.readFileSync(0, "utf8");
let data;
try {
  data = JSON.parse(raw);
} catch (error) {
  console.error(`debug JSON parse failed: ${error.message}`);
  process.exit(2);
}
const prompt = String(data.prompt || "");
const required = [
  "Allowed Task Calls:",
  "Never call `general`",
  "internal invocation audit",
  "subagent_type",
];
const missing = required.filter((needle) => !prompt.includes(needle));
if (missing.length > 0) {
  console.error(`missing prompt text: ${missing.join(", ")}`);
  process.exit(1);
}
'; then
    pass "$check_name" "agent=$agent_name"
  else
    fail "$check_name" "agent=$agent_name missing_required_prompt_text"
  fi
}

check_reviewer_debug() {
  local target_dir="$1"
  local agent_name="$2"
  local prompt_path="$3"
  local output

  if ! output="$(run_debug_agent "$target_dir" "$agent_name")"; then
    fail "debug_$agent_name" "agent=$agent_name debug_failed"
    printf '%s\n' "$output" >&2
    return
  fi

  if printf '%s\n' "$output" \
    | node -e '
const fs = require("fs");
const raw = fs.readFileSync(0, "utf8");
let data;
try {
  data = JSON.parse(raw);
} catch (error) {
  console.error(`debug JSON parse failed: ${error.message}`);
  process.exit(2);
}
const tools = data.tools || {};
const badTools = [];
for (const tool of ["edit", "bash", "task"]) {
  if (tools[tool] !== false) {
    badTools.push(`${tool}=${tools[tool]}`);
  }
}
const prompt = String(data.prompt || "");
if (badTools.length > 0) {
  console.error(`bad reviewer tools: ${badTools.join(", ")}`);
  process.exit(1);
}
if (!prompt || !prompt.includes("You may use only these read-only tools")) {
  console.error("reviewer prompt did not load expected read-only instructions");
  process.exit(1);
}
  '; then
    pass "debug_$agent_name" "agent=$agent_name read_only=true prompt=$prompt_path"
  else
    fail "debug_$agent_name" "agent=$agent_name invalid_effective_config"
  fi
}

global_dir_arg=""
target_arg=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --global-dir)
      shift
      if [ "$#" -eq 0 ]; then
        usage >&2
        fail "arguments" "--global-dir requires a directory argument"
        exit 2
      fi
      global_dir_arg="$1"
      ;;
    --*)
      usage >&2
      fail "arguments" "unknown_option=$1"
      exit 2
      ;;
    *)
      if [ -n "$target_arg" ]; then
        usage >&2
        fail "arguments" "too_many_target_repos"
        exit 2
      fi
      target_arg="$1"
      ;;
  esac
  shift
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/.." && pwd -P)"

if [ -n "$global_dir_arg" ]; then
  global_dir="$(absolute_path "$global_dir_arg")"
elif ! global_dir="$(default_global_dir)"; then
  fail "global_dir" "HOME is not set and --global-dir was not provided"
  exit 1
fi

target_arg="${target_arg:-$PWD}"
if ! target_dir="$(resolve_dir "$target_arg")"; then
  fail "target_repo" "path=$target_arg not_a_directory"
  exit 1
fi

agents_dir="$global_dir/agents"
prompts_dir="$global_dir/prompts"
agent_src_dir="$repo_root/.opencode/agents"
prompt_src_dir="$repo_root/.opencode/prompts"
target_config="$target_dir/opencode.json"

info "repo_root=$repo_root"
info "target_repo=$target_dir"
info "global_dir=$global_dir"

check_command node
check_command opencode
check_command realpath

check_symlink_target "global_agent_ping_pong_plan" "$agents_dir/ping-pong-plan.md" "$agent_src_dir/ping-pong-plan.md"
check_symlink_target "global_agent_ping_ping_build" "$agents_dir/ping-ping-build.md" "$agent_src_dir/ping-ping-build.md"

for prompt_name in \
  plan-contract-checker.md \
  plan-fact-auditor.md \
  plan-implementation-simulator.md \
  plan-improver.md \
  plan-red-team-gate.md \
  plan-validation-designer.md
do
  check_symlink_target "global_prompt_${prompt_name%.md}" "$prompts_dir/$prompt_name" "$prompt_src_dir/$prompt_name"
done

if [ -f "$target_config" ]; then
  pass "target_opencode_json_exists" "path=$target_config"
else
  fail "target_opencode_json_exists" "path=$target_config missing"
fi

if [ -f "$target_config" ]; then
  if node -e '
const fs = require("fs");
const path = process.argv[1];
const required = [
  ["plan-improver-model2", "plan-improver.md"],
  ["plan-improver-model3", "plan-improver.md"],
  ["plan-validation-designer", "plan-validation-designer.md"],
  ["plan-red-team-gate", "plan-red-team-gate.md"],
  ["plan-implementation-simulator", "plan-implementation-simulator.md"],
  ["plan-fact-auditor", "plan-fact-auditor.md"],
  ["plan-contract-checker", "plan-contract-checker.md"],
];
const data = JSON.parse(fs.readFileSync(path, "utf8"));
const agents = data.agent || {};
const agentNames = Object.keys(agents);
const missing = [];
const bad = [];
for (const [name, promptFile] of required) {
  const agent = agents[name];
  if (!agent) {
    missing.push(name);
    continue;
  }
  const expectedPrompt = `{file:~/.config/opencode/prompts/${promptFile}}`;
  if (agent.mode !== "subagent") bad.push(`${name}.mode=${agent.mode}`);
  if (agent.prompt !== expectedPrompt) bad.push(`${name}.prompt=${agent.prompt}`);
  const permission = agent.permission || {};
  for (const tool of ["edit", "bash", "task"]) {
    if (permission[tool] !== "deny") bad.push(`${name}.permission.${tool}=${permission[tool]}`);
  }
  for (const tool of ["read", "grep", "glob", "list"]) {
    if (permission[tool] !== "allow") bad.push(`${name}.permission.${tool}=${permission[tool]}`);
  }
}
const extra = agentNames.filter((name) => !required.some(([requiredName]) => requiredName === name));
if (missing.length || bad.length || extra.length) {
  if (missing.length) console.error(`missing=${missing.join(",")}`);
  if (bad.length) console.error(`bad=${bad.join(",")}`);
  if (extra.length) console.error(`extra=${extra.join(",")}`);
  process.exit(1);
}
' "$target_config"; then
    pass "target_reviewer_config" "required=7 extra=0 prompt_base=~/.config/opencode/prompts"
  else
    fail "target_reviewer_config" "path=$target_config expected_exact_seven_global_prompt_reviewers"
  fi
fi

check_debug_prompt "$target_dir" "ping-pong-plan" "debug_ping_pong_plan_prompt"
check_debug_prompt "$target_dir" "ping-ping-build" "debug_ping_ping_build_prompt"

check_reviewer_debug "$target_dir" "plan-improver-model2" "plan-improver.md"
check_reviewer_debug "$target_dir" "plan-improver-model3" "plan-improver.md"
check_reviewer_debug "$target_dir" "plan-validation-designer" "plan-validation-designer.md"
check_reviewer_debug "$target_dir" "plan-red-team-gate" "plan-red-team-gate.md"
check_reviewer_debug "$target_dir" "plan-implementation-simulator" "plan-implementation-simulator.md"
check_reviewer_debug "$target_dir" "plan-fact-auditor" "plan-fact-auditor.md"
check_reviewer_debug "$target_dir" "plan-contract-checker" "plan-contract-checker.md"

if [ -d "$repo_root/.git" ]; then
  cookbook_status="$(git -C "$repo_root" status --porcelain 2>/dev/null || true)"
  if [ -z "$cookbook_status" ]; then
    pass "cookbook_worktree" "changes=none"
  else
    pass "cookbook_worktree" "changes=present informational=true"
  fi
else
  pass "cookbook_worktree" "git_repo=false informational=true"
fi

if [ "$failures" -eq 0 ]; then
  printf 'SUMMARY status=pass failures=0\n'
  exit 0
fi

printf 'SUMMARY status=fail failures=%s\n' "$failures"
exit 1
