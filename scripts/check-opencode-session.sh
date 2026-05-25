#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/check-opencode-session.sh [session-id]

Checks an exported OpenCode session for task-tool calls to the required
ping-pong-plan subagents. If no session ID is provided, checks the latest
OpenCode session for the current working directory.

Options:
  -h, --help    Show this help.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -gt 1 ]]; then
  usage >&2
  exit 2
fi

session_id="${1:-}"

if [[ -z "$session_id" ]]; then
  if ! latest_sessions="$(opencode session list --max-count 1 --format json)"; then
    echo "opencode session list failed." >&2
    exit 2
  fi

  session_id="$(printf "%s\n" "$latest_sessions" | node -e '
const fs = require("fs");
const raw = fs.readFileSync(0, "utf8");

let sessions;
try {
  sessions = JSON.parse(raw);
} catch (error) {
  console.error(`Could not parse opencode session list JSON: ${error.message}`);
  process.exit(2);
}

if (!Array.isArray(sessions) || sessions.length === 0 || !sessions[0].id) {
  console.error("No OpenCode sessions found for the current working directory.");
  process.exit(1);
}

process.stdout.write(sessions[0].id);
')"
fi

if ! export_output="$(opencode export "$session_id")"; then
  echo "opencode export failed for session: $session_id" >&2
  exit 2
fi

printf "%s\n" "$export_output" | node -e '
const fs = require("fs");

const required = [
  "plan-improver-model2",
  "plan-improver-model3",
  "plan-validation-designer",
  "plan-red-team-gate",
  "plan-implementation-simulator",
  "plan-fact-auditor",
  "plan-contract-checker",
];

const raw = fs.readFileSync(0, "utf8");
const start = raw.indexOf("{");

if (start === -1) {
  console.error("No JSON object found in opencode export output.");
  process.exit(2);
}

const jsonText = raw
  .slice(start)
  .replace(/\x1b\[[0-?]*[ -/]*[@-~]/g, "")
  .replace(/[\u0000-\u001F]/g, "");

let exported = null;
let parseWarning = "";
try {
  exported = JSON.parse(jsonText);
} catch (error) {
  parseWarning = error.message;
}

const found = new Map(required.map((name) => [name, 0]));
const taskCalls = [];

function parseInput(input) {
  if (typeof input !== "string") {
    return input;
  }

  try {
    return JSON.parse(input);
  } catch {
    return input;
  }
}

function visit(value) {
  if (!value || typeof value !== "object") {
    return;
  }

  if (value.tool === "task") {
    const state = value.state && typeof value.state === "object" ? value.state : {};
    const input = parseInput(state.input ?? value.input ?? {});
    const subagentType = input && typeof input === "object" ? input.subagent_type : undefined;

    taskCalls.push({
      subagentType: subagentType || "<missing subagent_type>",
      status: state.status || value.status || "unknown",
    });

    if (found.has(subagentType)) {
      found.set(subagentType, found.get(subagentType) + 1);
    }
  }

  for (const child of Object.values(value)) {
    visit(child);
  }
}

function scanRawExport(text) {
  const cleaned = text.replace(/\x1b\[[0-?]*[ -/]*[@-~]/g, "");
  const toolPattern = /"tool"\s*:\s*"task"/g;
  let match;

  while ((match = toolPattern.exec(cleaned)) !== null) {
    const window = cleaned.slice(match.index, match.index + 8000);
    const subagentMatch = window.match(/"subagent_type"\s*:\s*"([^"]+)"/);
    const subagentType = subagentMatch ? subagentMatch[1] : "<missing subagent_type>";

    taskCalls.push({
      subagentType,
      status: "unknown",
    });

    if (found.has(subagentType)) {
      found.set(subagentType, found.get(subagentType) + 1);
    }
  }
}

if (exported) {
  visit(exported);
} else {
  scanRawExport(raw);
}

const rawId = raw.match(/"id"\s*:\s*"(ses_[^"]+)"/);
const rawTitle = raw.match(/"title"\s*:\s*"([^"]+)"/);
const rawDirectory = raw.match(/"directory"\s*:\s*"([^"]+)"/);
const info = exported ? exported.info || {} : {
  id: rawId ? rawId[1] : undefined,
  title: rawTitle ? rawTitle[1] : undefined,
  directory: rawDirectory ? rawDirectory[1] : undefined,
};

if (parseWarning) {
  console.error(`Warning: strict JSON parse failed, used task-call text scan instead: ${parseWarning}`);
  console.error("");
}

const sessionId = info.id || "<unknown>";
const sessionTitle = info.title || "";
const sessionDirectory = info.directory || "";

console.log(`SESSION_ID=${sessionId}`);
console.log(`SESSION_TITLE=${sessionTitle}`);
console.log(`SESSION_DIRECTORY=${sessionDirectory}`);
console.log("");
console.log(`Session: ${sessionId}${sessionTitle ? ` (${sessionTitle})` : ""}`);
if (sessionDirectory) {
  console.log(`Directory: ${sessionDirectory}`);
}
console.log("");
console.log("Required ping-pong subagent task calls:");

let missing = 0;
let foundRequired = 0;
for (const name of required) {
  const count = found.get(name) || 0;
  if (count === 0) {
    missing += 1;
    console.log(`SUBAGENT name=${name} status=missing count=0`);
    console.log(`- ${name}: missing`);
  } else {
    foundRequired += 1;
    console.log(`SUBAGENT name=${name} status=found count=${count}`);
    console.log(`- ${name}: found (${count} call${count === 1 ? "" : "s"})`);
  }
}

console.log(`SUMMARY required=${required.length} found=${foundRequired} missing=${missing} task_calls=${taskCalls.length}`);

const otherTaskCalls = taskCalls.filter((call) => !found.has(call.subagentType));
if (otherTaskCalls.length > 0) {
  console.log("");
  console.log("Other task calls:");
  for (const call of otherTaskCalls) {
    console.log(`- ${call.subagentType}: ${call.status}`);
  }
}

if (taskCalls.length === 0) {
  console.log("");
  console.log("No task-tool calls were found in this exported session.");
}

if (missing > 0) {
  console.error("");
  console.error(`Missing ${missing} required subagent task call${missing === 1 ? "" : "s"}.`);
  process.exit(1);
}
'
