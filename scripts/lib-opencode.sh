# Shared helpers for the agentsCookbook OpenCode/Pi scripts.

AC_PRIMARY_AGENT_FILES="
ping-ping-build.md
ping-pong-plan.md
subagent-router.md
"

# Exactly these eight reviewers are mandatory in Ping-Pong/Ping-Ping.
AC_FLOW_REVIEWER_AGENT_FILES="
plan-coverage-reviewer.md
plan-improver-model2.md
plan-improver-model3.md
plan-validation-designer.md
plan-red-team-gate.md
plan-implementation-simulator.md
plan-fact-auditor.md
plan-contract-checker.md
"

# Standalone capabilities are installable but are not silently added to the
# mandatory eight-review workflow.
AC_STANDALONE_AGENT_FILES="
code-performance-optimization-auditor.md
"

AC_AGENT_FILES="$AC_PRIMARY_AGENT_FILES$AC_FLOW_REVIEWER_AGENT_FILES$AC_STANDALONE_AGENT_FILES"

AC_SKILL_NAMES="
plan-gap-scout
alternative-route-challenge
validation-gap-finder
coverage-design-review
implementation-dry-run
fact-grounding-auditor
repository-improvement-scout
codebase-finding-derivation
plan-contract-guard
red-team-leftover-gate
code-performance-optimization-audit
stale-work-race-review
ui-lifecycle-race-review
atomic-operation-review
retry-idempotency-review
resource-lifetime-review
failure-contract-review
sensitive-data-masking
semantic-identity-invariance-review
evidence-projection-preservation-review
completeness-accounting-review
bounded-authority-monotonicity-review
cache-validity-binding-review
persistence-roundtrip-convergence-review
evidence-provenance-binding-review
unknown-state-collapse-review
cross-surface-convergence-review
semantic-noninterference-review
evidence-visibility-enforcement-review
authority-escalation-review
semantic-redecision-review
durable-commit-path-review
resolved-fact-regression-review
state-authority-review
invalid-state-model-review
aggregate-hard-failure-masking-review
measurement-comparability-review
evidence-readiness-review
baseline-self-authorization-review
single-observation-review
call-chain-collapse-review
alternate-path-removal-review
hidden-side-effect-review
dependency-surface-review
test-work-amplification-review
repeated-test-setup-review
test-isolation-boundary-review
test-orchestration-complexity-review
deterministic-causality-test-review
test-state-contamination-review
test-contract-coupling-review
architecture-risk-triage
"

AC_FLOW_REVIEWER_SKILL_MAP="
plan-coverage-reviewer coverage-design-review liteLLM/gpt-oss
plan-improver-model2 plan-gap-scout liteLLM/gpt-oss
plan-improver-model3 alternative-route-challenge liteLLM/gpt-oss
plan-validation-designer validation-gap-finder liteLLM/gpt-oss
plan-red-team-gate red-team-leftover-gate liteLLM/gpt-oss
plan-implementation-simulator implementation-dry-run liteLLM/gpt-oss
plan-fact-auditor fact-grounding-auditor liteLLM/gemma4
plan-contract-checker plan-contract-guard liteLLM/gemma4
"

AC_STANDALONE_AGENT_SKILL_MAP="
code-performance-optimization-auditor code-performance-optimization-audit liteLLM/devstral
"

AC_OPENCODE_ARTIFACT_PLUGIN="agents-cookbook-review-artifact.js"
AC_PI_ARTIFACT_EXTENSION="agents-cookbook-review-artifact"
AC_PI_ARTIFACT_EXTENSION_LEGACY="agents-cookbook-review-artifact.js"
AC_AGENT_DESCRIPTION_MAX=160
AC_SKILL_DESCRIPTION_MAX=160
AC_DESCRIPTION_TARGET=120

ac_die() { printf 'Error: %s\n' "$*" >&2; exit 1; }
ac_info() { printf '%s\n' "$*"; }

ac_absolute_path() {
  local path="$1"
  case "$path" in /*) printf '%s\n' "$path" ;; *) printf '%s/%s\n' "$PWD" "$path" ;; esac
}

ac_resolve_dir() { local path="$1"; [ -d "$path" ] || return 1; cd -- "$path" 2>/dev/null && pwd -P; }

ac_default_global_dir() {
  if [ -n "${XDG_CONFIG_HOME:-}" ]; then printf '%s/opencode\n' "$XDG_CONFIG_HOME"; return 0; fi
  if [ -n "${HOME:-}" ]; then printf '%s/.config/opencode\n' "$HOME"; return 0; fi
  return 1
}

ac_default_data_dir() {
  if [ -n "${XDG_DATA_HOME:-}" ]; then printf '%s/opencode\n' "$XDG_DATA_HOME"; return 0; fi
  if [ -n "${HOME:-}" ]; then printf '%s/.local/share/opencode\n' "$HOME"; return 0; fi
  return 1
}

ac_default_pi_agent_dir() {
  if [ -n "${PI_CODING_AGENT_DIR:-}" ]; then printf '%s\n' "$PI_CODING_AGENT_DIR"; return 0; fi
  if [ -n "${HOME:-}" ]; then printf '%s/.pi/agent\n' "$HOME"; return 0; fi
  return 1
}

# Runtime install location only; repository authority is skills/.
ac_default_shared_skill_dir() {
  if [ -n "${HOME:-}" ]; then printf '%s/.agents/skills\n' "$HOME"; return 0; fi
  return 1
}

ac_repo_root_from_script() {
  local script_path="$1" script_dir
  script_dir="$(cd -- "$(dirname -- "$script_path")" && pwd -P)"
  cd -- "$script_dir/.." && pwd -P
}

ac_agent_source_dir() { printf '%s/agents\n' "$1"; }
ac_skill_source_dir() { printf '%s/skills\n' "$1"; }
ac_opencode_artifact_adapter() { printf '%s/adapters/opencode/review-artifact.js\n' "$1"; }
ac_pi_artifact_adapter() { printf '%s/adapters/pi/review-artifact.js\n' "$1"; }

ac_backup_path_for() {
  local original="$1" stamp candidate n
  stamp="$(date +%Y%m%d-%H%M%S)"
  candidate="$original.agents-cookbook-backup-$stamp"
  n=1
  while [ -e "$candidate" ] || [ -L "$candidate" ]; do candidate="$original.agents-cookbook-backup-$stamp.$n"; n=$((n + 1)); done
  printf '%s\n' "$candidate"
}
