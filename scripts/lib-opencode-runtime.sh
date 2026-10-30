# OpenCode's native CLI owns installation and configuration. This guard only
# selects the cookbook adapter contract before invoking version-specific APIs.

ac_require_opencode_v1() {
  local output major
  if ! command -v opencode >/dev/null 2>&1; then
    printf 'OpenCode CLI is unavailable; install/select OpenCode 1.x for this adapter.\n' >&2
    return 1
  fi
  if ! output="$(opencode --version 2>&1)"; then
    printf 'Could not read the selected OpenCode CLI version: %s\n' "$output" >&2
    return 1
  fi
  output="${output%$'\r'}"
  if [[ ! "$output" =~ ^(opencode[[:space:]]+)?v?([0-9]+)\.([0-9]+)\.([0-9]+)([-+][A-Za-z0-9.+-]+)?$ ]]; then
    printf 'Unrecognized OpenCode version output: %s. Cannot select a supported adapter contract.\n' "$output" >&2
    return 1
  fi
  major="${BASH_REMATCH[2]}"
  AC_OPENCODE_VERSION="${BASH_REMATCH[2]}.${BASH_REMATCH[3]}.${BASH_REMATCH[4]}${BASH_REMATCH[5]}"
  if [[ "$major" != 1 ]]; then
    printf 'OpenCode %s is unsupported by this cookbook runtime adapter. It uses the OpenCode 1.x plugin, debug-agent and session-export contracts. OpenCode 2 requires a plugin/API migration; select a separate 1.x installation for this flow or use canonical skills directly. See adapters/opencode/README.md.\n' "$AC_OPENCODE_VERSION" >&2
    return 1
  fi
}
