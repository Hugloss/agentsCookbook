#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-opencode.sh
. "$script_dir/lib-opencode.sh"

usage() {
  cat <<'USAGE'
Usage: scripts/link-opencode-local.sh [--dry-run] [--force] [--global-dir DIR] [--pi-agent-dir DIR] [--shared-skill-dir DIR]

Link this checkout's agents for both OpenCode and Pi, and link their shared
reviewer skills. Pi requires the pi-open-agents extension.

Options:
  --dry-run               Print planned changes without modifying anything.
  --force                 Back up conflicting destinations before linking.
  --global-dir DIR        OpenCode config dir (default: ${XDG_CONFIG_HOME:-$HOME/.config}/opencode).
  --pi-agent-dir DIR      Pi agent dir (default: ${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}).
  --shared-skill-dir DIR  Cross-runtime skill dir (default: $HOME/.agents/skills).
  --help                  Show this help.

This script never creates or edits opencode.json or Pi settings.json.
USAGE
}

dry_run=false
force=false
global_dir_arg=""
pi_agent_dir_arg=""
shared_skill_dir_arg=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --help) usage; exit 0 ;;
    --dry-run) dry_run=true ;;
    --force) force=true ;;
    --global-dir) shift; [ "$#" -gt 0 ] || ac_die "--global-dir requires a directory argument"; global_dir_arg="$1" ;;
    --pi-agent-dir) shift; [ "$#" -gt 0 ] || ac_die "--pi-agent-dir requires a directory argument"; pi_agent_dir_arg="$1" ;;
    --shared-skill-dir) shift; [ "$#" -gt 0 ] || ac_die "--shared-skill-dir requires a directory argument"; shared_skill_dir_arg="$1" ;;
    --*) usage >&2; ac_die "unknown option: $1" ;;
    *) usage >&2; ac_die "unexpected argument: $1" ;;
  esac
  shift
done

repo_root="$(ac_repo_root_from_script "${BASH_SOURCE[0]}")"
if [ -n "$global_dir_arg" ]; then global_dir="$(ac_absolute_path "$global_dir_arg")"; elif ! global_dir="$(ac_default_global_dir)"; then ac_die "HOME is not set and --global-dir was not provided"; fi
if [ -n "$pi_agent_dir_arg" ]; then pi_agent_dir="$(ac_absolute_path "$pi_agent_dir_arg")"; elif ! pi_agent_dir="$(ac_default_pi_agent_dir)"; then ac_die "HOME is not set and --pi-agent-dir was not provided"; fi
if [ -n "$shared_skill_dir_arg" ]; then shared_skill_dir="$(ac_absolute_path "$shared_skill_dir_arg")"; elif ! shared_skill_dir="$(ac_default_shared_skill_dir)"; then ac_die "HOME is not set and --shared-skill-dir was not provided"; fi

agent_src_dir="$repo_root/.opencode/agents"
skill_src_dir="$repo_root/.agents/skills"
opencode_agents_dir="$global_dir/agents"
pi_agents_dir="$pi_agent_dir/agents"
[ -d "$agent_src_dir" ] || ac_die "source agents directory is missing: $agent_src_dir"
[ -d "$skill_src_dir" ] || ac_die "source skills directory is missing: $skill_src_dir"

move_to_backup() {
  local path="$1" backup
  backup="$(ac_backup_path_for "$path")"
  if [ "$dry_run" = true ]; then ac_info "DRY_RUN action=backup path=$path backup=$backup"; else mv -- "$path" "$backup"; ac_info "BACKUP path=$path backup=$backup"; fi
}

ensure_real_dir() {
  local path="$1"
  if [ -e "$path" ] || [ -L "$path" ]; then
    if [ -d "$path" ] && [ ! -L "$path" ]; then return 0; fi
    if [ "$force" = true ]; then move_to_backup "$path"; else ac_die "conflict at $path; expected a real directory"; fi
  fi
  if [ "$dry_run" = true ]; then ac_info "DIR status=would_create path=$path"; else mkdir -p -- "$path"; ac_info "DIR status=created path=$path"; fi
}

link_one() {
  local src="$1" dest="$2" label="$3" resolved
  if [ -L "$dest" ]; then
    resolved="$(realpath -- "$dest" 2>/dev/null || true)"
    if [ "$resolved" = "$src" ]; then ac_info "LINK type=$label status=already_correct path=$dest target=$src"; return 0; fi
    [ "$force" = true ] || ac_die "conflict at $dest; pass --force to back it up before linking"
    move_to_backup "$dest"
  elif [ -e "$dest" ]; then
    [ "$force" = true ] || ac_die "conflict at $dest; pass --force to back it up before linking"
    move_to_backup "$dest"
  fi
  if [ "$dry_run" = true ]; then ac_info "LINK type=$label status=would_create path=$dest target=$src"; else ln -s -- "$src" "$dest"; ac_info "LINK type=$label status=created path=$dest target=$src"; fi
}

remove_legacy_link() {
  local dest="$1" expected="$2" label="$3" raw resolved
  [ -L "$dest" ] || return 0
  raw="$(readlink -- "$dest" 2>/dev/null || true)"
  resolved="$(realpath -- "$dest" 2>/dev/null || true)"
  if [ "$raw" != "$expected" ] && [ "$resolved" != "$expected" ]; then return 0; fi
  if [ "$dry_run" = true ]; then ac_info "MIGRATE type=$label status=would_remove_legacy path=$dest target=$raw"; else rm -- "$dest"; ac_info "MIGRATE type=$label status=removed_legacy path=$dest target=$raw"; fi
}

verify_link() {
  local src="$1" dest="$2" label="$3" resolved
  [ "$dry_run" = true ] && return 0
  [ -L "$dest" ] || ac_die "post-link verification failed for $dest; expected $label symlink"
  resolved="$(realpath -- "$dest" 2>/dev/null || true)"
  [ "$resolved" = "$src" ] || ac_die "post-link verification failed for $dest; resolved=${resolved:-<unresolved>} expected=$src"
}

ensure_real_dir "$global_dir"
ensure_real_dir "$opencode_agents_dir"
ensure_real_dir "$pi_agent_dir"
ensure_real_dir "$pi_agents_dir"
ensure_real_dir "$(dirname -- "$shared_skill_dir")"
ensure_real_dir "$shared_skill_dir"

# Safely remove only symlinks created by the old prompt/skill installer.
for prompt_name in $AC_LEGACY_PROMPT_FILES; do
  remove_legacy_link "$global_dir/prompts/$prompt_name" "$repo_root/.opencode/prompts/$prompt_name" "legacy_prompt"
done
for skill_name in $AC_SKILL_NAMES; do
  remove_legacy_link "$global_dir/skills/$skill_name" "$repo_root/.opencode/skills/$skill_name" "legacy_skill"
done

agent_count=0
for agent_file in $AC_AGENT_FILES; do
  src="$agent_src_dir/$agent_file"
  [ -f "$src" ] || ac_die "required agent Markdown file is missing: $src"
  link_one "$src" "$opencode_agents_dir/$agent_file" "OpenCodeAgent"
  link_one "$src" "$pi_agents_dir/$agent_file" "PiAgent"
  agent_count=$((agent_count + 1))
done

skill_count=0
for skill_name in $AC_SKILL_NAMES; do
  src="$skill_src_dir/$skill_name"
  [ -f "$src/SKILL.md" ] || ac_die "required skill file is missing: $src/SKILL.md"
  link_one "$src" "$shared_skill_dir/$skill_name" "SharedSkill"
  skill_count=$((skill_count + 1))
done

for agent_file in $AC_AGENT_FILES; do
  verify_link "$agent_src_dir/$agent_file" "$opencode_agents_dir/$agent_file" "OpenCode agent"
  verify_link "$agent_src_dir/$agent_file" "$pi_agents_dir/$agent_file" "Pi agent"
done
for skill_name in $AC_SKILL_NAMES; do verify_link "$skill_src_dir/$skill_name" "$shared_skill_dir/$skill_name" "shared skill"; done

cat <<NEXT_STEPS

Installed cookbook links for both runtimes:
  OpenCode agents: $opencode_agents_dir
  Pi agents:       $pi_agents_dir
  Shared skills:   $shared_skill_dir

Pi must have pi-open-agents installed and enabled. Run both preflights before a long workflow:
  scripts/preflight-opencode-ping-pong.sh
  scripts/preflight-pi-ping-pong.sh

SUMMARY status=pass agents_per_runtime=$agent_count skills=$skill_count dry_run=$dry_run
NEXT_STEPS
