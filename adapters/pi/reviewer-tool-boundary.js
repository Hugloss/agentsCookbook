export const PI_REVIEWER_AGENTS = Object.freeze([
  "plan-improver-model2",
  "plan-improver-model3",
  "plan-validation-designer",
  "plan-coverage-reviewer",
  "plan-red-team-gate",
  "plan-implementation-simulator",
  "plan-fact-auditor",
  "plan-contract-checker",
  "code-performance-optimization-auditor",
])

const REVIEWER_SET = new Set(PI_REVIEWER_AGENTS)

// Pi built-ins needed by cookbook reviewers. Skills are advertised in the
// system prompt and can be opened through read; reviewers never need shell,
// project mutation, delegation, or artifact-read authority.
export const PI_REVIEWER_BASE_TOOLS = Object.freeze([
  "read",
  "grep",
  "find",
  "ls",
])

export function activeReviewerName(env = process.env) {
  const depth = Number(env.PI_OPEN_AGENTS_DEPTH || "0")
  const name = String(env.PI_OPEN_AGENTS_NAME || "")
  return Number.isFinite(depth) && depth > 0 && REVIEWER_SET.has(name) ? name : ""
}

export function reviewerAllowedTools({ artifactEnabled = false } = {}) {
  return artifactEnabled
    ? [...PI_REVIEWER_BASE_TOOLS, "review_artifact"]
    : [...PI_REVIEWER_BASE_TOOLS]
}

export function reviewerToolAllowed(toolName, { artifactEnabled = false } = {}) {
  return reviewerAllowedTools({ artifactEnabled }).includes(String(toolName || ""))
}
