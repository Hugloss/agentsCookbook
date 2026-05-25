#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/link-opencode-local.sh [--dry-run] [--force] [--global-dir DIR]

Create global OpenCode symlinks that point back to this agentsCookbook checkout.

Options:
  --dry-run          Print planned changes without modifying the global OpenCode dir.
  --force            Back up existing non-matching destinations before linking.
  --global-dir DIR   OpenCode config dir. Defaults to ${XDG_CONFIG_HOME:-$HOME/.config}/opencode.
  --help             Show this help.

This script never creates or edits any opencode.json file.
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
force=false
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
    --force)
      force=true
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

if [ -n "$global_dir_arg" ]; then
  global_dir="$(absolute_path "$global_dir_arg")"
else
  global_dir="$(default_global_dir)"
fi

agent_src_dir="$repo_root/.opencode/agents"
prompt_src_dir="$repo_root/.opencode/prompts"
agents_dir="$global_dir/agents"
prompts_dir="$global_dir/prompts"

[ -d "$agent_src_dir" ] || die "source agents directory is missing: $agent_src_dir"
[ -d "$prompt_src_dir" ] || die "source prompts directory is missing: $prompt_src_dir"

backup_path_for() {
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

move_to_backup() {
  local path="$1"
  local backup
  backup="$(backup_path_for "$path")"
  if [ "$dry_run" = true ]; then
    info "DRY RUN: would move $path to $backup"
  else
    mv -- "$path" "$backup"
    info "Backed up $path to $backup"
  fi
}

ensure_real_dir() {
  local path="$1"
  local forceable="${2:-false}"

  if [ -e "$path" ] || [ -L "$path" ]; then
    if [ -d "$path" ] && [ ! -L "$path" ]; then
      return 0
    fi
    if [ "$force" = true ] && [ "$forceable" = true ]; then
      move_to_backup "$path"
    else
      die "conflict at $path; expected a real directory"
    fi
  fi

  if [ "$dry_run" = true ]; then
    info "DRY RUN: would create directory $path"
  else
    mkdir -p -- "$path"
    info "Created directory $path"
  fi
}

link_one() {
  local src="$1"
  local dest="$2"
  local label="$3"
  local resolved

  if [ -L "$dest" ]; then
    resolved="$(realpath -- "$dest" 2>/dev/null || true)"
    if [ "$resolved" = "$src" ]; then
      info "$label link already correct: $dest -> $src"
      return 0
    fi
    if [ "$force" != true ]; then
      die "conflict at $dest; pass --force to back it up before linking"
    fi
    move_to_backup "$dest"
  elif [ -e "$dest" ]; then
    if [ "$force" != true ]; then
      die "conflict at $dest; pass --force to back it up before linking"
    fi
    move_to_backup "$dest"
  fi

  if [ "$dry_run" = true ]; then
    info "DRY RUN: would link $dest -> $src"
  else
    ln -s -- "$src" "$dest"
    info "Linked $dest -> $src"
  fi
}

ensure_real_dir "$global_dir" false
ensure_real_dir "$agents_dir" true
ensure_real_dir "$prompts_dir" true

agent_count=0
for agent_src in "$agent_src_dir"/*.md; do
  [ -f "$agent_src" ] || die "no agent Markdown files found in $agent_src_dir"
  agent_name="$(basename -- "$agent_src")"
  link_one "$agent_src" "$agents_dir/$agent_name" "Agent"
  agent_count=$((agent_count + 1))
done

prompt_count=0
for prompt_src in "$prompt_src_dir"/*.md; do
  [ -f "$prompt_src" ] || die "no prompt Markdown files found in $prompt_src_dir"
  prompt_name="$(basename -- "$prompt_src")"
  link_one "$prompt_src" "$prompts_dir/$prompt_name" "Prompt"
  prompt_count=$((prompt_count + 1))
done

cat <<NEXT_STEPS

Installed global OpenCode cookbook symlinks in:
  $global_dir

Next steps for a target repo:
  1. Copy or merge this example into the target repo's opencode.json:
     $repo_root/.opencode/examples/opencode.local-symlink.example.json
  2. OpenCode discovers ping-pong-plan from:
     $agents_dir/ping-pong-plan.md
     and ping-ping-build from:
     $agents_dir/ping-ping-build.md
  3. The example config reads subagent prompts from:
     ~/.config/opencode/prompts/

Linked $agent_count agent file(s) and $prompt_count prompt file(s). This script did not create or edit any opencode.json file.
NEXT_STEPS
