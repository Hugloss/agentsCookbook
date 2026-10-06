import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const sourceFile = fs.realpathSync(fileURLToPath(import.meta.url))
const reviewers = JSON.parse(fs.readFileSync(path.resolve(path.dirname(sourceFile), "../../reviewers.json"), "utf8"))

export const PI_REVIEWER_AGENTS = Object.freeze(reviewers)

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
