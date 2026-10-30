import crypto from "node:crypto"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const sourceFile = fs.realpathSync(fileURLToPath(import.meta.url))
const reviewers = JSON.parse(fs.readFileSync(path.resolve(path.dirname(sourceFile), "../../reviewers.json"), "utf8"))

const MAX_REPORT_CHARS = 65536
const MAX_SUMMARY_CHARS = 1200
const SAFE_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$/
const REVIEWER_AGENT_IDS = new Set(reviewers)
const PRIMARY_AGENT_IDS = new Set([
  "ping-pong-plan",
  "ping-ping-build",
  "subagent-router",
])

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex")
}

function requireRunRoot() {
  const configured = process.env.AGENTS_COOKBOOK_RUN_DIR || ""
  if (!configured) throw new Error("AGENTS_COOKBOOK_RUN_DIR is not configured")
  if (!path.isAbsolute(configured)) throw new Error("AGENTS_COOKBOOK_RUN_DIR must be absolute")
  fs.mkdirSync(configured, { recursive: true })
  return fs.realpathSync(configured)
}

function ensureChildDir(root, name) {
  const target = path.join(root, name)
  fs.mkdirSync(target, { recursive: true })
  const resolved = fs.realpathSync(target)
  const prefix = `${root}${path.sep}`
  if (!resolved.startsWith(prefix)) throw new Error(`${name} escapes configured run root`)
  return resolved
}

function validateId(value) {
  const id = String(value || "")
  if (!SAFE_ID.test(id)) throw new Error("artifact_id must match [A-Za-z0-9][A-Za-z0-9._-]{0,95}")
  if (!REVIEWER_AGENT_IDS.has(id)) throw new Error(`unknown reviewer artifact_id: ${id}`)
  return id
}

function currentAgent(context) {
  return String(context && context.agent ? context.agent : "")
}

function writeArtifact(args, context) {
  const root = requireRunRoot()
  const reviews = ensureChildDir(root, "reviews")
  const receipts = ensureChildDir(root, "receipts")
  const agent = currentAgent(context)
  const requestedId = validateId(args.artifact_id)
  if (!REVIEWER_AGENT_IDS.has(agent)) throw new Error(`review_artifact is reviewer-only; current agent: ${agent || "unknown"}`)
  if (agent !== requestedId) throw new Error(`artifact_id must equal current reviewer name: ${agent}`)

  const report = String(args.content || "").trim()
  const summary = String(args.summary || "").trim()
  if (!report) throw new Error("content must not be empty")
  if (report.length > MAX_REPORT_CHARS) throw new Error(`content exceeds ${MAX_REPORT_CHARS} characters`)
  if (!summary) throw new Error("summary must not be empty")
  if (summary.length > MAX_SUMMARY_CHARS) throw new Error(`summary exceeds ${MAX_SUMMARY_CHARS} characters`)

  const artifactPath = path.join(reviews, `${requestedId}.md`)
  const receiptPath = path.join(receipts, `${requestedId}.json`)
  if (fs.existsSync(artifactPath) || fs.existsSync(receiptPath)) {
    throw new Error(`artifact already exists for ${requestedId}; use a new run directory`)
  }

  const body = `${report}\n`
  const receipt = {
    schema_version: 1,
    runtime: "opencode",
    run_id: path.basename(root),
    reviewer: agent,
    artifact_id: requestedId,
    session_id: context.sessionID || null,
    subject_id: args.subject_id || null,
    subject_revision: args.subject_revision || null,
    artifact: `reviews/${requestedId}.md`,
    sha256: sha256(body),
    chars: body.length,
    summary,
  }

  fs.writeFileSync(artifactPath, body, { encoding: "utf8", flag: "wx" })
  try {
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt, null, 2)}\n`, { encoding: "utf8", flag: "wx" })
  } catch (error) {
    try { fs.unlinkSync(artifactPath) } catch {}
    throw error
  }
  return receipt
}

function readArtifact(args, context) {
  const agent = currentAgent(context)
  if (!PRIMARY_AGENT_IDS.has(agent)) throw new Error(`review_artifact_read is primary-only; current agent: ${agent || "unknown"}`)

  const root = requireRunRoot()
  const reviews = ensureChildDir(root, "reviews")
  const receipts = ensureChildDir(root, "receipts")
  const id = validateId(args.artifact_id)
  const artifactPath = fs.realpathSync(path.join(reviews, `${id}.md`))
  const receiptPath = fs.realpathSync(path.join(receipts, `${id}.json`))
  if (!artifactPath.startsWith(`${reviews}${path.sep}`)) throw new Error("artifact escapes review directory")
  if (!receiptPath.startsWith(`${receipts}${path.sep}`)) throw new Error("receipt escapes receipt directory")
  const body = fs.readFileSync(artifactPath, "utf8")
  if (!body.trim()) throw new Error("artifact must not be empty")
  if (body.length > MAX_REPORT_CHARS + 1) throw new Error("artifact exceeds configured report limit")
  const receipt = JSON.parse(fs.readFileSync(receiptPath, "utf8"))
  if (!receipt || typeof receipt !== "object" || Array.isArray(receipt)
    || receipt.schema_version !== 1 || receipt.runtime !== "opencode"
    || receipt.run_id !== path.basename(root)
    || receipt.artifact_id !== id || receipt.reviewer !== id
    || receipt.artifact !== `reviews/${id}.md`) {
    throw new Error("receipt does not identify this OpenCode reviewer artifact")
  }
  if (typeof receipt.summary !== "string" || !receipt.summary.trim()
    || receipt.summary.length > MAX_SUMMARY_CHARS) throw new Error("receipt summary is invalid")
  if (!Number.isInteger(receipt.chars) || receipt.chars !== body.length
    || receipt.sha256 !== sha256(body)) throw new Error("artifact does not match its receipt")
  return body
}

// The config-local native entrypoint resolves the host SDK and supplies its
// tool factory. Bare imports here would resolve at the cookbook's realpath.
export const AgentsCookbookReviewArtifacts = async (tool) => {
  if (!process.env.AGENTS_COOKBOOK_RUN_DIR) return {}
  if (typeof tool !== "function" || typeof tool.schema?.string !== "function") {
    throw new Error("OpenCode tool factory is missing; reinstall the cookbook OpenCode entrypoint")
  }

  return {
    tool: {
      review_artifact: tool({
        description: "Save one full reviewer report in the configured run store and return only its compact receipt.",
        args: {
          artifact_id: tool.schema.string().describe("Stable artifact id; reviewer agents use their exact agent name."),
          summary: tool.schema.string().describe("Compact material findings summary, at most 1200 characters."),
          content: tool.schema.string().describe("Complete skill-defined Markdown review artifact."),
          subject_id: tool.schema.string().optional().describe("Optional reviewed subject id."),
          subject_revision: tool.schema.string().optional().describe("Optional reviewed subject revision."),
        },
        async execute(args, context) {
          return JSON.stringify(writeArtifact(args, context))
        },
      }),
      review_artifact_read: tool({
        description: "Read one named reviewer artifact from the configured run store; no arbitrary paths are accepted.",
        args: {
          artifact_id: tool.schema.string().describe("Reviewer artifact id to read."),
        },
        async execute(args, context) {
          return readArtifact(args, context)
        },
      }),
    },
  }
}
