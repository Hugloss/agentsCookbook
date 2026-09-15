# Shared helpers for the agentsCookbook OpenCode shell scripts.

AC_PRIMARY_AGENT_FILES="
ping-ping-build.md
ping-pong-plan.md
subagent-router.md
"

AC_REVIEWER_AGENT_FILES="
plan-coverage-reviewer.md
plan-improver-model2.md
plan-improver-model3.md
plan-validation-designer.md
plan-red-team-gate.md
plan-implementation-simulator.md
plan-fact-auditor.md
plan-contract-checker.md
"

AC_AGENT_FILES="$AC_PRIMARY_AGENT_FILES$AC_REVIEWER_AGENT_FILES"

AC_SKILL_NAMES="
coverage-design-review
fact-grounding-auditor
implementation-dry-run
plan-contract-guard
plan-improvement-scout
red-team-leftover-gate
validation-gap-finder
"

AC_REVIEWER_SKILL_MAP="
plan-coverage-reviewer coverage-design-review liteLLM/gpt-oss
plan-improver-model2 plan-improvement-scout liteLLM/gpt-oss
plan-improver-model3 plan-improvement-scout liteLLM/gpt-oss
plan-validation-designer validation-gap-finder liteLLM/gpt-oss
plan-red-team-gate red-team-leftover-gate liteLLM/gpt-oss
plan-implementation-simulator implementation-dry-run liteLLM/gpt-oss
plan-fact-auditor fact-grounding-auditor liteLLM/gemma4
plan-contract-checker plan-contract-guard liteLLM/gemma4
"

# Removed source files retained only so installers can clean up cookbook-owned
# symlinks from installations made by older versions.
AC_LEGACY_PROMPT_FILES="
plan-contract-checker.md
plan-fact-auditor.md
plan-implementation-simulator.md
plan-improver.md
plan-red-team-gate.md
plan-validation-designer.md
"

ac_die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

ac_info() {
  printf '%s\n' "$*"
}

ac_absolute_path() {
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

ac_resolve_dir() {
  local path="$1"
  if [ ! -d "$path" ]; then
    return 1
  fi
  cd -- "$path" 2>/dev/null && pwd -P
}

ac_default_global_dir() {
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

ac_default_data_dir() {
  if [ -n "${XDG_DATA_HOME:-}" ]; then
    printf '%s/opencode\n' "$XDG_DATA_HOME"
    return 0
  fi
  if [ -n "${HOME:-}" ]; then
    printf '%s/.local/share/opencode\n' "$HOME"
    return 0
  fi
  return 1
}

ac_default_pi_agent_dir() {
  if [ -n "${PI_CODING_AGENT_DIR:-}" ]; then
    printf '%s\n' "$PI_CODING_AGENT_DIR"
    return 0
  fi
  if [ -n "${HOME:-}" ]; then
    printf '%s/.pi/agent\n' "$HOME"
    return 0
  fi
  return 1
}

ac_default_shared_skill_dir() {
  if [ -n "${HOME:-}" ]; then
    printf '%s/.agents/skills\n' "$HOME"
    return 0
  fi
  return 1
}

ac_repo_root_from_script() {
  local script_path="$1"
  local script_dir
  script_dir="$(cd -- "$(dirname -- "$script_path")" && pwd -P)"
  cd -- "$script_dir/.." && pwd -P
}

ac_backup_path_for() {
  local original="$1"
  local stamp candidate n
  stamp="$(date +%Y%m%d-%H%M%S)"
  candidate="$original.agents-cookbook-backup-$stamp"
  n=1
  while [ -e "$candidate" ] || [ -L "$candidate" ]; do
    candidate="$original.agents-cookbook-backup-$stamp.$n"
    n=$((n + 1))
  done
  printf '%s\n' "$candidate"
}
