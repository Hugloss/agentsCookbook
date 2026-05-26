#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-opencode.sh
. "$script_dir/lib-opencode.sh"

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

if [ -n "$global_dir_arg" ]; then
  global_dir="$(ac_absolute_path "$global_dir_arg")"
elif ! global_dir="$(ac_default_global_dir)"; then
  ac_die "HOME is not set and --global-dir was not provided"
fi

agent_src_dir="$repo_root/.opencode/agents"
prompt_src_dir="$repo_root/.opencode/prompts"
agents_dir="$global_dir/agents"
prompts_dir="$global_dir/prompts"

[ -d "$agent_src_dir" ] || ac_die "source agents directory is missing: $agent_src_dir"
[ -d "$prompt_src_dir" ] || ac_die "source prompts directory is missing: $prompt_src_dir"

move_to_backup() {
  local path="$1"
  local backup
  backup="$(ac_backup_path_for "$path")"
  if [ "$dry_run" = true ]; then
    ac_info "DRY_RUN action=backup path=$path backup=$backup"
  else
    mv -- "$path" "$backup"
    ac_info "BACKUP path=$path backup=$backup"
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
      ac_die "conflict at $path; expected a real directory"
    fi
  fi

  if [ "$dry_run" = true ]; then
    ac_info "DIR status=would_create path=$path"
  else
    mkdir -p -- "$path"
    ac_info "DIR status=created path=$path"
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
      ac_info "LINK type=$label status=already_correct path=$dest target=$src"
      return 0
    fi
    if [ "$force" != true ]; then
      ac_die "conflict at $dest; pass --force to back it up before linking"
    fi
    move_to_backup "$dest"
  elif [ -e "$dest" ]; then
    if [ "$force" != true ]; then
      ac_die "conflict at $dest; pass --force to back it up before linking"
    fi
    move_to_backup "$dest"
  fi

  if [ "$dry_run" = true ]; then
    ac_info "LINK type=$label status=would_create path=$dest target=$src"
  else
    ln -s -- "$src" "$dest"
    ac_info "LINK type=$label status=created path=$dest target=$src"
  fi
}

verify_link_one() {
  local src="$1"
  local dest="$2"
  local label="$3"
  local resolved

  if [ "$dry_run" = true ]; then
    return 0
  fi
  if [ ! -L "$dest" ]; then
    ac_die "post-link verification failed for $dest; expected $label symlink"
  fi
  resolved="$(realpath -- "$dest" 2>/dev/null || true)"
  if [ "$resolved" != "$src" ]; then
    ac_die "post-link verification failed for $dest; resolved=${resolved:-<unresolved>} expected=$src"
  fi
  ac_info "VERIFY type=$label status=pass path=$dest target=$src"
}

ensure_real_dir "$global_dir" false
ensure_real_dir "$agents_dir" true
ensure_real_dir "$prompts_dir" true

agent_count=0
for agent_name in $AC_PRIMARY_AGENT_FILES; do
  agent_src="$agent_src_dir/$agent_name"
  [ -f "$agent_src" ] || ac_die "required agent Markdown file is missing: $agent_src"
  link_one "$agent_src" "$agents_dir/$agent_name" "Agent"
  agent_count=$((agent_count + 1))
done

prompt_count=0
for prompt_name in $AC_PROMPT_FILES; do
  prompt_src="$prompt_src_dir/$prompt_name"
  [ -f "$prompt_src" ] || ac_die "required prompt Markdown file is missing: $prompt_src"
  link_one "$prompt_src" "$prompts_dir/$prompt_name" "Prompt"
  prompt_count=$((prompt_count + 1))
done

for agent_name in $AC_PRIMARY_AGENT_FILES; do
  verify_link_one "$agent_src_dir/$agent_name" "$agents_dir/$agent_name" "Agent"
done

for prompt_name in $AC_PROMPT_FILES; do
  verify_link_one "$prompt_src_dir/$prompt_name" "$prompts_dir/$prompt_name" "Prompt"
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

SUMMARY status=pass agents=$agent_count prompts=$prompt_count dry_run=$dry_run global_dir=$global_dir
Linked $agent_count agent file(s) and $prompt_count prompt file(s). This script did not create or edit any opencode.json file.
NEXT_STEPS
