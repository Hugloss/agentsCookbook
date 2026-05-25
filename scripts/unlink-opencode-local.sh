#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/unlink-opencode-local.sh [--dry-run] [--global-dir DIR]

Remove only this agentsCookbook repo's global OpenCode symlinks.

Options:
  --dry-run          Print planned changes without modifying the global OpenCode dir.
  --global-dir DIR   OpenCode config dir. Defaults to ${XDG_CONFIG_HOME:-$HOME/.config}/opencode.
  --help             Show this help.

This script never removes real files, real directories, unrelated symlinks, or any opencode.json file.
USAGE
}

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

info() {
  printf '%s\n' "$*"
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

default_global_dir() {
  if [ -n "${XDG_CONFIG_HOME:-}" ]; then
    printf '%s/opencode\n' "$XDG_CONFIG_HOME"
    return 0
  fi
  [ -n "${HOME:-}" ] || die "HOME is not set and --global-dir was not provided"
  printf '%s/.config/opencode\n' "$HOME"
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
      [ "$#" -gt 0 ] || die "--global-dir requires a directory argument"
      global_dir_arg="$1"
      ;;
    --*)
      usage >&2
      die "unknown option: $1"
      ;;
    *)
      usage >&2
      die "unexpected argument: $1"
      ;;
  esac
  shift
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/.." && pwd -P)"
repo_opencode="$repo_root/.opencode"

if [ -n "$global_dir_arg" ]; then
  global_dir="$(absolute_path "$global_dir_arg")"
else
  global_dir="$(default_global_dir)"
fi

agents_dir="$global_dir/agents"
prompts_dir="$global_dir/prompts"

removed_any=false

remove_if_cookbook_symlink() {
  local path="$1"
  local label="$2"
  local resolved

  if [ ! -e "$path" ] && [ ! -L "$path" ]; then
    info "$label link not present: $path"
    return 0
  fi

  if [ ! -L "$path" ]; then
    info "Preserving $label because it is not a symlink: $path"
    return 0
  fi

  resolved="$(realpath -- "$path" 2>/dev/null || true)"
  if [ -z "$resolved" ]; then
    info "Preserving $label because its symlink target cannot be resolved: $path"
    return 0
  fi

  case "$resolved" in
    "$repo_opencode"|"$repo_opencode"/*)
      if [ "$dry_run" = true ]; then
        info "DRY RUN: would remove $label link $path -> $resolved"
      else
        rm -- "$path"
        info "Removed $label link $path -> $resolved"
      fi
      removed_any=true
      ;;
    *)
      info "Preserving unrelated $label symlink $path -> $resolved"
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
      info "DRY RUN: would remove empty directory $path"
    else
      rmdir -- "$path"
      info "Removed empty directory $path"
    fi
    removed_any=true
  elif [ -e "$path" ] || [ -L "$path" ]; then
    info "Preserving non-empty or non-directory path $path"
  fi
}

for agent_dest in "$agents_dir"/*.md; do
  [ -e "$agent_dest" ] || [ -L "$agent_dest" ] || continue
  remove_if_cookbook_symlink "$agent_dest" "agent"
done

for prompt_dest in "$prompts_dir"/*.md; do
  [ -e "$prompt_dest" ] || [ -L "$prompt_dest" ] || continue
  remove_if_cookbook_symlink "$prompt_dest" "prompt"
done

remove_empty_dir "$agents_dir"
remove_empty_dir "$prompts_dir"

if [ "$removed_any" = false ]; then
  info "Nothing remains to remove for $global_dir"
fi
