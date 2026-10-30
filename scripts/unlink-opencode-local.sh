#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-opencode.sh
. "$script_dir/lib-opencode.sh"

usage() {
  cat <<'USAGE'
Usage: scripts/unlink-opencode-local.sh [--dry-run] [--global-dir DIR] [--pi-agent-dir DIR] [--shared-skill-dir DIR]

Remove only this checkout's agent/skill/adapter symlinks and exact unmodified
OpenCode native entry. Preserve foreign or modified files.
USAGE
}

dry_run=false; global_dir_arg=""; pi_agent_dir_arg=""; shared_skill_dir_arg=""
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
opencode_adapter="$(ac_opencode_artifact_adapter "$repo_root")"
pi_adapter="$(ac_pi_artifact_adapter "$repo_root")"
pi_adapter_dir="$(dirname -- "$pi_adapter")"
if [ -n "$global_dir_arg" ]; then global_dir="$(ac_absolute_path "$global_dir_arg")"; elif ! global_dir="$(ac_default_global_dir)"; then ac_die "HOME is not set"; fi
if [ -n "$pi_agent_dir_arg" ]; then pi_agent_dir="$(ac_absolute_path "$pi_agent_dir_arg")"; elif ! pi_agent_dir="$(ac_default_pi_agent_dir)"; then ac_die "HOME is not set"; fi
if [ -n "$shared_skill_dir_arg" ]; then shared_skill_dir="$(ac_absolute_path "$shared_skill_dir_arg")"; elif ! shared_skill_dir="$(ac_default_shared_skill_dir)"; then ac_die "HOME is not set"; fi
command -v node >/dev/null 2>&1 || ac_die "Node.js is required to verify OpenCode entry ownership before removal"

removed_any=false
remove_owned_link() {
  local candidate="$1" expected="$2" label="$3" raw resolved
  if [ ! -e "$candidate" ] && [ ! -L "$candidate" ]; then return 0; fi
  [ -L "$candidate" ] || { ac_info "UNLINK type=$label status=preserved_not_symlink path=$candidate"; return 0; }
  raw="$(readlink -- "$candidate" 2>/dev/null || true)"; resolved="$(realpath -- "$candidate" 2>/dev/null || true)"
  if [ "$raw" != "$expected" ] && [ "$resolved" != "$expected" ]; then return 0; fi
  if [ "$dry_run" = true ]; then ac_info "UNLINK type=$label status=would_remove path=$candidate target=$raw"; else rm -- "$candidate"; ac_info "UNLINK type=$label status=removed path=$candidate target=$raw"; fi
  removed_any=true
}

remove_empty_dir() {
  local candidate="$1"
  if [ -d "$candidate" ] && [ ! -L "$candidate" ] && [ -z "$(find "$candidate" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
    if [ "$dry_run" = true ]; then ac_info "DIR status=would_remove_empty path=$candidate"; else rmdir -- "$candidate"; ac_info "DIR status=removed_empty path=$candidate"; fi
    removed_any=true
  fi
}

# Inspect installed names as well as current sources, so deleted or renamed
# upstream files do not leave dangling cookbook-owned links behind.
for candidate in "$global_dir/agents/"*.md "$pi_agent_dir/agents/"*.md; do
  [ -L "$candidate" ] || continue
  name="${candidate##*/}"
  remove_owned_link "$candidate" "$agent_src_dir/$name" "Agent"
  remove_owned_link "$candidate" "$repo_root/.opencode/agents/$name" "LegacyAgent"
done
for candidate in "$shared_skill_dir/"*; do
  [ -L "$candidate" ] || continue
  name="${candidate##*/}"
  remove_owned_link "$candidate" "$skill_src_dir/$name" "SharedSkill"
  remove_owned_link "$candidate" "$repo_root/.agents/skills/$name" "LegacySharedSkill"
done
for candidate in "$global_dir/skills/"*; do
  [ -L "$candidate" ] || continue
  name="${candidate##*/}"
  remove_owned_link "$candidate" "$repo_root/.opencode/skills/$name" "OlderLegacySkill"
done
opencode_entry="$global_dir/plugins/$AC_OPENCODE_ARTIFACT_PLUGIN"
if ac_opencode_artifact_entry_matches "$opencode_entry" "$opencode_adapter"; then
  if [ "$dry_run" = true ]; then ac_info "UNLINK type=OpenCodeArtifactEntry status=would_remove path=$opencode_entry"; else rm -- "$opencode_entry"; ac_info "UNLINK type=OpenCodeArtifactEntry status=removed path=$opencode_entry"; fi
  removed_any=true
else
  remove_owned_link "$opencode_entry" "$opencode_adapter" "LegacyOpenCodeArtifactPlugin"
fi
remove_owned_link "$pi_agent_dir/extensions/$AC_PI_ARTIFACT_EXTENSION" "$pi_adapter_dir" "PiArtifactExtension"
remove_owned_link "$pi_agent_dir/extensions/$AC_PI_ARTIFACT_EXTENSION_LEGACY" "$pi_adapter" "LegacyPiArtifactExtension"

remove_empty_dir "$global_dir/agents"
remove_empty_dir "$global_dir/plugins"
remove_empty_dir "$pi_agent_dir/agents"
remove_empty_dir "$pi_agent_dir/extensions"
remove_empty_dir "$shared_skill_dir"
remove_empty_dir "$global_dir/skills"

ac_info "SUMMARY status=pass removed=$removed_any dry_run=$dry_run"
