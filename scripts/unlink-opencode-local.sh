#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-opencode.sh
. "$script_dir/lib-opencode.sh"

usage() {
  cat <<'USAGE'
Usage: scripts/unlink-opencode-local.sh [--dry-run] [--global-dir DIR] [--pi-agent-dir DIR] [--shared-skill-dir DIR]

Remove only this checkout's OpenCode/Pi agent and shared-skill symlinks,
including cookbook-owned links made by the prior hidden-source layout.
USAGE
}

dry_run=false
global_dir_arg=""
pi_agent_dir_arg=""
shared_skill_dir_arg=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --help) usage; exit 0 ;;
    --dry-run) dry_run=true ;;
    --global-dir) shift; [ "$#" -gt 0 ] || ac_die "--global-dir requires a directory"; global_dir_arg="$1" ;;
    --pi-agent-dir) shift; [ "$#" -gt 0 ] || ac_die "--pi-agent-dir requires a directory"; pi_agent_dir_arg="$1" ;;
    --shared-skill-dir) shift; [ "$#" -gt 0 ] || ac_die "--shared-skill-dir requires a directory"; shared_skill_dir_arg="$1" ;;
    --*) usage >&2; ac_die "unknown option: $1" ;;
    *) usage >&2; ac_die "unexpected argument: $1" ;;
  esac
  shift
done

repo_root="$(ac_repo_root_from_script "${BASH_SOURCE[0]}")"
agent_src_dir="$(ac_agent_source_dir "$repo_root")"
skill_src_dir="$(ac_skill_source_dir "$repo_root")"
if [ -n "$global_dir_arg" ]; then global_dir="$(ac_absolute_path "$global_dir_arg")"; elif ! global_dir="$(ac_default_global_dir)"; then ac_die "HOME is not set"; fi
if [ -n "$pi_agent_dir_arg" ]; then pi_agent_dir="$(ac_absolute_path "$pi_agent_dir_arg")"; elif ! pi_agent_dir="$(ac_default_pi_agent_dir)"; then ac_die "HOME is not set"; fi
if [ -n "$shared_skill_dir_arg" ]; then shared_skill_dir="$(ac_absolute_path "$shared_skill_dir_arg")"; elif ! shared_skill_dir="$(ac_default_shared_skill_dir)"; then ac_die "HOME is not set"; fi

removed_any=false
remove_owned_link() {
  local path="$1" expected="$2" label="$3" raw resolved
  if [ ! -e "$path" ] && [ ! -L "$path" ]; then return 0; fi
  [ -L "$path" ] || { ac_info "UNLINK type=$label status=preserved_not_symlink path=$path"; return 0; }
  raw="$(readlink -- "$path" 2>/dev/null || true)"
  resolved="$(realpath -- "$path" 2>/dev/null || true)"
  if [ "$raw" != "$expected" ] && [ "$resolved" != "$expected" ]; then return 0; fi
  if [ "$dry_run" = true ]; then ac_info "UNLINK type=$label status=would_remove path=$path target=$raw"; else rm -- "$path"; ac_info "UNLINK type=$label status=removed path=$path target=$raw"; fi
  removed_any=true
}

remove_empty_dir() {
  local path="$1"
  if [ -d "$path" ] && [ ! -L "$path" ] && [ -z "$(find "$path" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
    if [ "$dry_run" = true ]; then ac_info "DIR status=would_remove_empty path=$path"; else rmdir -- "$path"; ac_info "DIR status=removed_empty path=$path"; fi
    removed_any=true
  fi
}

for agent_file in $AC_AGENT_FILES; do
  remove_owned_link "$global_dir/agents/$agent_file" "$agent_src_dir/$agent_file" "OpenCodeAgent"
  remove_owned_link "$pi_agent_dir/agents/$agent_file" "$agent_src_dir/$agent_file" "PiAgent"
  remove_owned_link "$global_dir/agents/$agent_file" "$repo_root/.opencode/agents/$agent_file" "LegacyOpenCodeAgent"
  remove_owned_link "$pi_agent_dir/agents/$agent_file" "$repo_root/.opencode/agents/$agent_file" "LegacyPiAgent"
done
for skill_name in $AC_SKILL_NAMES; do
  remove_owned_link "$shared_skill_dir/$skill_name" "$skill_src_dir/$skill_name" "SharedSkill"
  remove_owned_link "$shared_skill_dir/$skill_name" "$repo_root/.agents/skills/$skill_name" "LegacySharedSkill"
  remove_owned_link "$global_dir/skills/$skill_name" "$repo_root/.opencode/skills/$skill_name" "OlderLegacySkill"
done

remove_empty_dir "$global_dir/agents"
remove_empty_dir "$pi_agent_dir/agents"
remove_empty_dir "$shared_skill_dir"
remove_empty_dir "$global_dir/skills"

ac_info "SUMMARY status=pass removed=$removed_any dry_run=$dry_run"
