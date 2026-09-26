#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-opencode.sh
. "$script_dir/lib-opencode.sh"

usage() {
  cat <<'USAGE'
Usage: scripts/link-opencode-local.sh [--dry-run] [--force] [--global-dir DIR] [--pi-agent-dir DIR] [--shared-skill-dir DIR]

Install canonical agents/skills and the optional bounded review-artifact adapters
for OpenCode and Pi. Artifact tools register only when AGENTS_COOKBOOK_RUN_DIR
is set for the runtime process.
USAGE
}

dry_run=false; force=false; global_dir_arg=""; pi_agent_dir_arg=""; shared_skill_dir_arg=""
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
if [ -n "$global_dir_arg" ]; then global_dir="$(ac_absolute_path "$global_dir_arg")"; elif ! global_dir="$(ac_default_global_dir)"; then ac_die "HOME is not set"; fi
if [ -n "$pi_agent_dir_arg" ]; then pi_agent_dir="$(ac_absolute_path "$pi_agent_dir_arg")"; elif ! pi_agent_dir="$(ac_default_pi_agent_dir)"; then ac_die "HOME is not set"; fi
if [ -n "$shared_skill_dir_arg" ]; then shared_skill_dir="$(ac_absolute_path "$shared_skill_dir_arg")"; elif ! shared_skill_dir="$(ac_default_shared_skill_dir)"; then ac_die "HOME is not set"; fi

agent_src_dir="$(ac_agent_source_dir "$repo_root")"
skill_src_dir="$(ac_skill_source_dir "$repo_root")"
AC_SKILL_NAMES="$(ac_skill_names "$repo_root")"
opencode_adapter="$(ac_opencode_artifact_adapter "$repo_root")"
pi_adapter="$(ac_pi_artifact_adapter "$repo_root")"
pi_adapter_dir="$(dirname -- "$pi_adapter")"
opencode_agents_dir="$global_dir/agents"
opencode_plugins_dir="$global_dir/plugins"
pi_agents_dir="$pi_agent_dir/agents"
pi_extensions_dir="$pi_agent_dir/extensions"

[ -d "$agent_src_dir" ] || ac_die "source agents directory missing: $agent_src_dir"
[ -d "$skill_src_dir" ] || ac_die "source skills directory missing: $skill_src_dir"
[ -f "$opencode_adapter" ] || ac_die "OpenCode adapter missing: $opencode_adapter"
[ -f "$pi_adapter" ] || ac_die "Pi adapter missing: $pi_adapter"
[ -f "$pi_adapter_dir/index.js" ] || ac_die "Pi extension entry missing: $pi_adapter_dir/index.js"
[ -f "$pi_adapter_dir/reviewer-tool-boundary.js" ] || ac_die "Pi extension helper missing: $pi_adapter_dir/reviewer-tool-boundary.js"

move_to_backup() {
  local path="$1" backup; backup="$(ac_backup_path_for "$path")"
  if [ "$dry_run" = true ]; then ac_info "DRY_RUN action=backup path=$path backup=$backup"; else mv -- "$path" "$backup"; ac_info "BACKUP path=$path backup=$backup"; fi
}

ensure_real_dir() {
  local path="$1"
  if [ -e "$path" ] || [ -L "$path" ]; then
    if [ -d "$path" ] && [ ! -L "$path" ]; then return 0; fi
    [ "$force" = true ] || ac_die "conflict at $path; expected a real directory"
    move_to_backup "$path"
  fi
  if [ "$dry_run" = true ]; then ac_info "DIR status=would_create path=$path"; else mkdir -p -- "$path"; ac_info "DIR status=created path=$path"; fi
}

link_target_matches() {
  local dest="$1" expected="$2" raw resolved
  [ -L "$dest" ] || return 1
  raw="$(readlink -- "$dest" 2>/dev/null || true)"; resolved="$(realpath -- "$dest" 2>/dev/null || true)"
  [ "$raw" = "$expected" ] || [ "$resolved" = "$expected" ]
}

remove_owned_legacy_link() {
  local dest="$1" expected="$2" label="$3" raw
  link_target_matches "$dest" "$expected" || return 0
  raw="$(readlink -- "$dest" 2>/dev/null || true)"
  if [ "$dry_run" = true ]; then ac_info "MIGRATE type=$label status=would_remove path=$dest target=$raw"; else rm -- "$dest"; ac_info "MIGRATE type=$label status=removed path=$dest target=$raw"; fi
}

link_one() {
  local src="$1" dest="$2" label="$3" legacy_expected="${4:-}" raw resolved
  if [ -L "$dest" ]; then
    raw="$(readlink -- "$dest" 2>/dev/null || true)"; resolved="$(realpath -- "$dest" 2>/dev/null || true)"
    if [ "$raw" = "$src" ] || [ "$resolved" = "$src" ]; then ac_info "LINK type=$label status=already_correct path=$dest target=$src"; return 0; fi
    if [ -n "$legacy_expected" ] && { [ "$raw" = "$legacy_expected" ] || [ "$resolved" = "$legacy_expected" ]; }; then
      if [ "$dry_run" = true ]; then ac_info "MIGRATE type=$label status=would_replace_legacy path=$dest old_target=$raw new_target=$src"; return 0; fi
      rm -- "$dest"; ac_info "MIGRATE type=$label status=removed_legacy path=$dest target=$raw"
    else
      [ "$force" = true ] || ac_die "conflict at $dest; pass --force to back it up before linking"
      move_to_backup "$dest"
    fi
  elif [ -e "$dest" ]; then
    [ "$force" = true ] || ac_die "conflict at $dest; pass --force to back it up before linking"
    move_to_backup "$dest"
  fi
  if [ "$dry_run" = true ]; then ac_info "LINK type=$label status=would_create path=$dest target=$src"; else ln -s -- "$src" "$dest"; ac_info "LINK type=$label status=created path=$dest target=$src"; fi
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
ensure_real_dir "$opencode_plugins_dir"
ensure_real_dir "$pi_agent_dir"
ensure_real_dir "$pi_agents_dir"
ensure_real_dir "$pi_extensions_dir"
ensure_real_dir "$(dirname -- "$shared_skill_dir")"
ensure_real_dir "$shared_skill_dir"

legacy_pi_extension="$pi_extensions_dir/$AC_PI_ARTIFACT_EXTENSION_LEGACY"
if [ -e "$legacy_pi_extension" ] || [ -L "$legacy_pi_extension" ]; then
  if link_target_matches "$legacy_pi_extension" "$pi_adapter"; then
    remove_owned_legacy_link "$legacy_pi_extension" "$pi_adapter" "PiArtifactExtension"
  else
    [ "$force" = true ] || ac_die "conflict at $legacy_pi_extension; pass --force to back it up before linking"
    move_to_backup "$legacy_pi_extension"
  fi
fi

for skill_name in $AC_SKILL_NAMES; do remove_owned_legacy_link "$global_dir/skills/$skill_name" "$repo_root/.opencode/skills/$skill_name" "OlderLegacySkill"; done

agent_count=0
for agent_file in $AC_AGENT_FILES; do
  src="$agent_src_dir/$agent_file"; legacy="$repo_root/.opencode/agents/$agent_file"
  [ -f "$src" ] || ac_die "required agent Markdown file missing: $src"
  link_one "$src" "$opencode_agents_dir/$agent_file" "OpenCodeAgent" "$legacy"
  link_one "$src" "$pi_agents_dir/$agent_file" "PiAgent" "$legacy"
  agent_count=$((agent_count + 1))
done

skill_count=0
for skill_name in $AC_SKILL_NAMES; do
  src="$skill_src_dir/$skill_name"; legacy="$repo_root/.agents/skills/$skill_name"
  [ -f "$src/SKILL.md" ] || ac_die "required skill file missing: $src/SKILL.md"
  link_one "$src" "$shared_skill_dir/$skill_name" "SharedSkill" "$legacy"
  skill_count=$((skill_count + 1))
done

link_one "$opencode_adapter" "$opencode_plugins_dir/$AC_OPENCODE_ARTIFACT_PLUGIN" "OpenCodeArtifactPlugin"
link_one "$pi_adapter_dir" "$pi_extensions_dir/$AC_PI_ARTIFACT_EXTENSION" "PiArtifactExtension"

for agent_file in $AC_AGENT_FILES; do
  verify_link "$agent_src_dir/$agent_file" "$opencode_agents_dir/$agent_file" "OpenCode agent"
  verify_link "$agent_src_dir/$agent_file" "$pi_agents_dir/$agent_file" "Pi agent"
done
for skill_name in $AC_SKILL_NAMES; do verify_link "$skill_src_dir/$skill_name" "$shared_skill_dir/$skill_name" "shared skill"; done
verify_link "$opencode_adapter" "$opencode_plugins_dir/$AC_OPENCODE_ARTIFACT_PLUGIN" "OpenCode artifact plugin"
verify_link "$pi_adapter_dir" "$pi_extensions_dir/$AC_PI_ARTIFACT_EXTENSION" "Pi artifact extension"

cat <<NEXT_STEPS
Installed cookbook links from canonical sources:
  Source agents:     $agent_src_dir
  Source skills:     $skill_src_dir
  OpenCode agents:   $opencode_agents_dir
  OpenCode plugin:   $opencode_plugins_dir/$AC_OPENCODE_ARTIFACT_PLUGIN
  Pi agents:         $pi_agents_dir
  Pi extension:      $pi_extensions_dir/$AC_PI_ARTIFACT_EXTENSION
  Shared skills:     $shared_skill_dir

Set AGENTS_COOKBOOK_RUN_DIR to an absolute per-run directory to enable bounded live artifact tools. Leave it unset for normal full-review-output behavior.

SUMMARY status=pass agents_per_runtime=$agent_count skills=$skill_count adapters=2 mandatory_flow_reviewers=8 dry_run=$dry_run
NEXT_STEPS
