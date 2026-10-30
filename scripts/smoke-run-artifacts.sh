#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/.." && pwd -P)"
temp_root="$(mktemp -d "${TMPDIR:-/tmp}/agents-cookbook-artifacts.XXXXXX")"
cleanup() { rm -rf "$temp_root"; }
trap cleanup EXIT

node "$script_dir/smoke-artifacts-fixtures.js" "$temp_root" "$repo_root"
