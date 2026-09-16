import crypto from "node:crypto"
import fs from "node:fs"
import path from "node:path"
import { Type } from "typebox"
import {
  activeReviewerName,
  reviewerAllowedTools,
  reviewerToolAllowed,
} from "./reviewer-tool-boundary.js"

const MAX_REPORT_CHARS = 65536
const MAX_SUMMARY_CHARS = 1200
const SAFE_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$/
const REVIEWER_ARTIFACT_IDS = new Set([
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

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex")
}

function configuredRunRoot() {
  const configured = process.env.AGENTS_COOKBOOK_RUN_DIR || ""
  if (!configured) return ""
  if (!path.isAbsolute(configured)) throw new Error("AGENTS_COOKBOOK_RUN_DIR must be absolute")
  fs.mkdirSync(configured, { recursive: true })
  return fs.realpathSync(configured)
}

function requireRunRoot() {
  const root = configuredRunRoot()
  if (!root) throw new Error("AGENTS_COOKBOOK_RUN_DIR is not configured")
  return root
}

function ensureChildDir(root, name) {
  const target = path.join(root, name)
  fs.mkdirSync(target, { recursive: true })
  const resolved = fs.realpathSync(target)
  const prefix = `${root}${path.sep}`
  if (resolved !== root && !resolved.startsWith(prefix)) throw new Error(`${name} escapes configured run root`)
  return resolved
}

function validateId(value) {
  const id = String(value || "")
  if (!SAFE_ID.test(id)) throw new Error("artifact_id must match [A-Za-z0-9][A-Za-z0-9._-]{0,95}")
  if (!REVIEWER_ARTIFACT_IDS.has(id)) throw new Error(`unknown reviewer artifact_id: ${id}`)
  return id
}

function writeArtifact(args, reviewerName) {
  const root = requireRunRoot()
  const reviews = ensureChildDir(root, "reviews")
  const receipts = ensureChildDir(root, "receipts")
  const id = validateId(args.artifact_id)
  if (!reviewerName) throw new Error("review_artifact is available only to a delegated reviewer child")
  if (id !== reviewerName) {
    throw new Error(`artifact_id must equal current reviewer name: ${reviewerName}`)
  }

  const report = String(args.content || "").trim()
  const summary = String(args.summary || "").trim()
  if (!report) throw new Error("content must not be empty")
  if (report.length > MAX_REPORT_CHARS) throw new Error(`content exceeds ${MAX_REPORT_CHARS} characters`)
  if (!summary) throw new Error("summary must not be empty")
  if (summary.length > MAX_SUMMARY_CHARS) throw new Error(`summary exceeds ${MAX_SUMMARY_CHARS} characters`)

  const artifactPath = path.join(reviews, `${id}.md`)
  const receiptPath = path.join(receipts, `${id}.json`)
  if (fs.existsSync(artifactPath) || fs.existsSync(receiptPath)) {
    throw new Error(`artifact already exists for ${id}; use a new run directory`)
  }

  const body = `${report}\n`
  const receipt = {
    schema_version: 1,
    runtime: "pi",
    run_id: path.basename(root),
    reviewer: reviewerName,
    artifact_id: id,
    subject_id: args.subject_id || null,
    subject_revision: args.subject_revision || null,
    artifact: `reviews/${id}.md`,
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

function readArtifact(args) {
  const root = requireRunRoot()
  const reviews = ensureChildDir(root, "reviews")
  const id = validateId(args.artifact_id)
  const candidate = path.join(reviews, `${id}.md`)
  const resolved = fs.realpathSync(candidate)
  const prefix = `${reviews}${path.sep}`
  if (!resolved.startsWith(prefix)) throw new Error("artifact escapes review directory")
  const body = fs.readFileSync(resolved, "utf8")
  if (body.length > MAX_REPORT_CHARS + 1) throw new Error("artifact exceeds configured report limit")
  return body
}

export default function registerAgentsCookbookReviewArtifacts(pi) {
  const reviewerName = activeReviewerName()
  const runRoot = configuredRunRoot()
  const artifactEnabled = Boolean(runRoot)

  if (artifactEnabled && reviewerName) {
    pi.registerTool({
      name: "review_artifact",
      label: "Save review artifact",
      description: "Save one full reviewer report in the configured run store and return only its compact receipt.",
      parameters: Type.Object({
        artifact_id: Type.String({ description: "Stable artifact id; reviewer agents use their exact agent name." }),
        summary: Type.String({ description: "Compact material findings summary, at most 1200 characters." }),
        content: Type.String({ description: "Complete skill-defined Markdown review artifact." }),
        subject_id: Type.Optional(Type.String({ description: "Optional reviewed subject id." })),
        subject_revision: Type.Optional(Type.String({ description: "Optional reviewed subject revision." })),
      }),
      async execute(_toolCallId, params) {
        const receipt = writeArtifact(params, reviewerName)
        return {
          content: [{ type: "text", text: JSON.stringify(receipt) }],
          details: receipt,
        }
      },
    })
  }

  if (artifactEnabled && !reviewerName) {
    pi.registerTool({
      name: "review_artifact_read",
      label: "Read review artifact",
      description: "Read one named reviewer artifact from the configured run store; no arbitrary paths are accepted.",
      parameters: Type.Object({
        artifact_id: Type.String({ description: "Reviewer artifact id to read." }),
      }),
      async execute(_toolCallId, params) {
        const body = readArtifact(params)
        return {
          content: [{ type: "text", text: body }],
          details: { artifact_id: params.artifact_id, chars: body.length },
        }
      },
    })
  }

  // pi-open-agents cannot derive a finite child --tools whitelist when an
  // OpenCode-compatible permission block contains a wildcard entry, even when
  // that wildcard is "*": deny. Canonical reviewer agents deliberately retain
  // wildcard deny-by-default for OpenCode. In a Pi reviewer child, enforce the
  // equivalent finite boundary here using the authoritative child identity.
  if (reviewerName) {
    const allowedTools = reviewerAllowedTools({ artifactEnabled })
    const applyReviewerToolBoundary = () => pi.setActiveTools(allowedTools)

    // Apply during extension registration and again after Pi has completed
    // session initialization. The latter is the documented lifecycle point for
    // runtime tool selection and protects against later startup configuration.
    applyReviewerToolBoundary()
    pi.on("session_start", async () => {
      applyReviewerToolBoundary()
    })

    // Defense-in-depth: even if another extension later changes visibility,
    // execution still fails closed for every out-of-policy tool.
    pi.on("tool_call", async (event) => {
      if (reviewerToolAllowed(event.toolName, { artifactEnabled })) return undefined
      return {
        block: true,
        reason: `Agents Cookbook reviewer ${reviewerName} is not allowed to use tool ${event.toolName}`,
      }
    })
  }
}
