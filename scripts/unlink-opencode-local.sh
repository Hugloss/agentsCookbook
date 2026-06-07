#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-opencode.sh
. "$script_dir/lib-opencode.sh"

usage() {
  cat <<'USAGE'
Usage: scripts/unlink-opencode-local.sh [--dry-run] [--global-dir DIR]

Remove only this agentsCookbook repo's global OpenCode agent, prompt, and skill symlinks.

Options:
  --dry-run          Print planned changes without modifying the global OpenCode dir.
  --global-dir DIR   OpenCode config dir. Defaults to ${XDG_CONFIG_HOME:-$HOME/.config}/opencode.
  --help             Show this help.

This script never removes real files, real directories, unrelated symlinks, or any opencode.json file.
USAGE
}

dry_run=false
global_dir_arg=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --help)
      usage
      exit 0
      ;;
    --dry-run)
      dry_run=true
      ;;
    --global-dir)
      shift
      [ "$#" -gt 0 ] || ac_die "--global-dir requires a directory argument"
      global_dir_arg="$1"
      ;;
    --*)
      usage >&2
      ac_die "unknown option: $1"
      ;;
    *)
      usage >&2
      ac_die "unexpected argument: $1"
      ;;
  esac
  shift
done

repo_root="$(ac_repo_root_from_script "${BASH_SOURCE[0]}")"
repo_opencode="$repo_root/.opencode"

if [ -n "$global_dir_arg" ]; then
  global_dir="$(ac_absolute_path "$global_dir_arg")"
elif ! global_dir="$(ac_default_global_dir)"; then
  ac_die "HOME is not set and --global-dir was not provided"
fi

agents_dir="$global_dir/agents"
prompts_dir="$global_dir/prompts"
skills_dir="$global_dir/skills"

removed_any=false

remove_if_cookbook_symlink() {
  local path="$1"
  local label="$2"
  local resolved

  if [ ! -e "$path" ] && [ ! -L "$path" ]; then
    ac_info "UNLINK type=$label status=not_present path=$path"
    return 0
  fi

  if [ ! -L "$path" ]; then
    ac_info "UNLINK type=$label status=preserved_not_symlink path=$path"
    return 0
  fi

  resolved="$(realpath -- "$path" 2>/dev/null || true)"
  if [ -z "$resolved" ]; then
    ac_info "UNLINK type=$label status=preserved_unresolved path=$path"
    return 0
  fi

  case "$resolved" in
    "$repo_opencode"|"$repo_opencode"/*)
      if [ "$dry_run" = true ]; then
        ac_info "UNLINK type=$label status=would_remove path=$path target=$resolved"
      else
        rm -- "$path"
        ac_info "UNLINK type=$label status=removed path=$path target=$resolved"
      fi
      removed_any=true
      ;;
    *)
      ac_info "UNLINK type=$label status=preserved_unrelated path=$path target=$resolved"
      ;;
  esac
}

dir_is_empty() {
  local path="$1"
  [ -d "$path" ] && [ ! -L "$path" ] && [ -z "$(find "$path" -mindepth 1 -maxdepth 1 -print -quit)" ]
}

remove_empty_dir() {
  local path="$1"

  if dir_is_empty "$path"; then
    if [ "$dry_run" = true ]; then
      ac_info "DIR status=would_remove_empty path=$path"
    else
      rmdir -- "$path"
      ac_info "DIR status=removed_empty path=$path"
    fi
    removed_any=true
  elif [ -e "$path" ] || [ -L "$path" ]; then
    ac_info "DIR status=preserved_non_empty_or_non_directory path=$path"
  fi
}

for agent_name in $AC_PRIMARY_AGENT_FILES; do
  remove_if_cookbook_symlink "$agents_dir/$agent_name" "agent"
done

for prompt_name in $AC_PROMPT_FILES; do
  remove_if_cookbook_symlink "$prompts_dir/$prompt_name" "prompt"
done

for skill_name in $AC_SKILL_NAMES; do
  remove_if_cookbook_symlink "$skills_dir/$skill_name" "skill"
done

remove_empty_dir "$agents_dir"
remove_empty_dir "$prompts_dir"
remove_empty_dir "$skills_dir"

if [ "$removed_any" = false ]; then
  ac_info "SUMMARY status=pass removed=false global_dir=$global_dir"
else
  ac_info "SUMMARY status=pass removed=true dry_run=$dry_run global_dir=$global_dir"
fi
