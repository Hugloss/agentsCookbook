#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-opencode.sh
. "$script_dir/lib-opencode.sh"

usage() {
  cat <<'USAGE'
Usage: scripts/check-opencode-session.sh [--scope latest-segment|latest-turn|session] [--expect-subagent NAME] [--expect-no-subagent] [--db PATH] [--log-dir DIR] [--no-agent-log-check] [--failures-only] [--json] [session-id]

Checks an OpenCode session for task-tool calls to the required planning/build
reviewer subagents, or for one routed reviewer when the scoped primary agent is
subagent-router. If no session ID is provided, checks the latest OpenCode
session for the current working directory.

Options:
  --scope VALUE             Validation scope. Defaults to latest-segment.
                            latest-segment checks the latest primary-agent segment.
                            latest-turn checks only after the latest user prompt.
                            session checks the whole session.
  --expect-subagent NAME    For subagent-router scopes, require this exact
                            reviewer subagent_type.
  --expect-no-subagent      For subagent-router scopes, require no reviewer
                            task call at all.
  --db PATH                 OpenCode SQLite DB. Defaults to
                            ${XDG_DATA_HOME:-$HOME/.local/share}/opencode/opencode.db.
  --log-dir DIR             OpenCode log dir. Defaults to
                            ${XDG_DATA_HOME:-$HOME/.local/share}/opencode/log.
  --no-agent-log-check      Do not scan OpenCode logs for primary-agent attribution.
  --failures-only           Print compact grep-friendly failure details only.
  --json                    Print JSON with exit_code, stdout lines, and stderr lines.
  -h, --help                Show this help.
USAGE
}

sql_string() {
  local value="$1"
  local escaped
  escaped="$(printf '%s' "$value" | sed "s/'/''/g")"
  printf "'%s'" "$escaped"
}

query_json() {
  local db="$1"
  local sql="$2"
  sqlite3 -json "$db" "$sql"
}

scope="latest-segment"
db_path=""
log_dir=""
agent_log_check=1
session_id=""
expected_subagent=""
expected_no_subagent=0
failures_only=0
json_output=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --scope)
      shift
      if [[ $# -eq 0 ]]; then
        usage >&2
        echo "--scope requires latest-segment, latest-turn, or session." >&2
        exit 2
      fi
      scope="$1"
      ;;
    --expect-subagent)
      shift
      if [[ $# -eq 0 ]]; then
        usage >&2
        echo "--expect-subagent requires a reviewer subagent name." >&2
        exit 2
      fi
      expected_subagent="$1"
      ;;
    --expect-no-subagent)
      expected_no_subagent=1
      ;;
    --db)
      shift
      if [[ $# -eq 0 ]]; then
        usage >&2
        echo "--db requires a path argument." >&2
        exit 2
      fi
      db_path="$1"
      ;;
    --log-dir)
      shift
      if [[ $# -eq 0 ]]; then
        usage >&2
        echo "--log-dir requires a directory argument." >&2
        exit 2
      fi
      log_dir="$1"
      ;;
    --no-agent-log-check)
      agent_log_check=0
      ;;
    --failures-only)
      failures_only=1
      ;;
    --json)
      json_output=1
      ;;
    --*)
      usage >&2
      echo "Unknown option: $1" >&2
      exit 2
      ;;
    *)
      if [[ -n "$session_id" ]]; then
        usage >&2
        echo "Too many session IDs." >&2
        exit 2
      fi
      session_id="$1"
      ;;
  esac
  shift
done

case "$scope" in
  latest-segment|latest-turn|session)
    ;;
  *)
    usage >&2
    echo "Invalid --scope value: $scope" >&2
    exit 2
    ;;
esac

if [[ -z "$db_path" || -z "$log_dir" ]]; then
  if data_dir="$(ac_default_data_dir)"; then
    db_path="${db_path:-$data_dir/opencode.db}"
    log_dir="${log_dir:-$data_dir/log}"
  fi
fi

if [[ -n "$expected_subagent" && "$expected_no_subagent" -eq 1 ]]; then
  usage >&2
  echo "--expect-subagent and --expect-no-subagent are mutually exclusive." >&2
  exit 2
fi

temp_dir="$(mktemp -d "${TMPDIR:-/tmp}/opencode-session-check.XXXXXX")"
cleanup() {
  rm -rf "$temp_dir"
}
trap cleanup EXIT

db_available=0
if command -v sqlite3 >/dev/null 2>&1 && [[ -n "$db_path" && -f "$db_path" ]]; then
  db_available=1
fi

if [[ -z "$session_id" && "$db_available" -eq 1 ]]; then
  target_dir="$(pwd -P)"
  latest_sql="select id from session where directory=$(sql_string "$target_dir") order by time_updated desc limit 1;"
  session_id="$(sqlite3 -noheader "$db_path" "$latest_sql" 2>/dev/null || true)"
fi

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

session_file="$temp_dir/session.json"
events_file="$temp_dir/events.json"
messages_file="$temp_dir/messages.json"
parts_file="$temp_dir/parts.json"
export_file="$temp_dir/export.txt"
timeline_source="none"

printf '[]\n' >"$session_file"
printf '[]\n' >"$events_file"
printf '[]\n' >"$messages_file"
printf '[]\n' >"$parts_file"
: >"$export_file"

if [[ "$db_available" -eq 1 ]]; then
  session_sql="select id,parent_id,title,agent,directory,time_created,time_updated from session where id=$(sql_string "$session_id");"
  events_sql="select id,type,time_created,time_updated,data from session_message where session_id=$(sql_string "$session_id") order by time_created,id;"
  messages_sql="select id,time_created,time_updated,data from message where session_id=$(sql_string "$session_id") order by time_created,id;"
  parts_sql="select id,message_id,time_created,time_updated,data from part where session_id=$(sql_string "$session_id") order by time_created,id;"

  if query_json "$db_path" "$session_sql" >"$session_file" \
    && query_json "$db_path" "$events_sql" >"$events_file" \
    && query_json "$db_path" "$messages_sql" >"$messages_file" \
    && query_json "$db_path" "$parts_sql" >"$parts_file"; then
    if node -e 'const fs=require("fs"); const rows=JSON.parse(fs.readFileSync(process.argv[1],"utf8")); process.exit(Array.isArray(rows)&&rows.length>0?0:1);' "$session_file"; then
      timeline_source="db"
    fi
  fi
fi

if [[ "$timeline_source" != "db" ]]; then
  if ! opencode export "$session_id" >"$export_file"; then
    echo "opencode export failed for session: $session_id" >&2
    exit 2
  fi
  timeline_source="export"
fi

export OPENCODE_SESSION_CHECK_SCOPE="$scope"
export OPENCODE_SESSION_CHECK_SESSION_ID="$session_id"
export OPENCODE_SESSION_CHECK_EXPECT_SUBAGENT="$expected_subagent"
export OPENCODE_SESSION_CHECK_TIMELINE_SOURCE="$timeline_source"
export OPENCODE_SESSION_CHECK_DB_PATH="$db_path"
export OPENCODE_SESSION_CHECK_SESSION_FILE="$session_file"
export OPENCODE_SESSION_CHECK_EVENTS_FILE="$events_file"
export OPENCODE_SESSION_CHECK_MESSAGES_FILE="$messages_file"
export OPENCODE_SESSION_CHECK_PARTS_FILE="$parts_file"
export OPENCODE_SESSION_CHECK_EXPORT_FILE="$export_file"
export OPENCODE_SESSION_CHECK_LOG_DIR="$log_dir"
export OPENCODE_SESSION_CHECK_AGENT_LOG="$agent_log_check"
export OPENCODE_SESSION_CHECK_EXPECT_NO_SUBAGENT="$expected_no_subagent"

node_stdout="$temp_dir/node.stdout"
node_stderr="$temp_dir/node.stderr"

set +e
node >"$node_stdout" 2>"$node_stderr" <<'NODE'
const fs = require("fs");
const path = require("path");

const required = [
  "plan-improver-model2",
  "plan-improver-model3",
  "plan-validation-designer",
  "plan-red-team-gate",
  "plan-implementation-simulator",
  "plan-fact-auditor",
  "plan-contract-checker",
];
const requiredSet = new Set(required);
const workflowAgents = new Set(["ping-pong-plan", "ping-ping-build"]);
const scopedPrimaryAgents = new Set(["ping-pong-plan", "ping-ping-build", "subagent-router"]);
const forbiddenPlanningTools = new Set(["write", "edit", "bash", "patch", "todowrite"]);

const checkScope = process.env.OPENCODE_SESSION_CHECK_SCOPE || "latest-segment";
const timelineSource = process.env.OPENCODE_SESSION_CHECK_TIMELINE_SOURCE || "none";
const requestedSessionId = process.env.OPENCODE_SESSION_CHECK_SESSION_ID || "";
const expectedSubagent = process.env.OPENCODE_SESSION_CHECK_EXPECT_SUBAGENT || "";
const expectedNoSubagent = process.env.OPENCODE_SESSION_CHECK_EXPECT_NO_SUBAGENT === "1";

if (expectedSubagent && !requiredSet.has(expectedSubagent)) {
  console.error(`Invalid --expect-subagent value: ${expectedSubagent}`);
  process.exit(2);
}
if (expectedSubagent && expectedNoSubagent) {
  console.error("--expect-subagent and --expect-no-subagent are mutually exclusive.");
  process.exit(2);
}

function readJsonFile(file, fallback) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return fallback;
  }
}

function parseMaybeJson(value) {
  if (typeof value !== "string") {
    return value;
  }
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

function valueTime(value) {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function formatTime(value) {
  if (!value) {
    return "unknown";
  }
  return new Date(value).toISOString();
}

function addCount(map, key) {
  map.set(key, (map.get(key) || 0) + 1);
}

function summarizeCalls(calls) {
  const found = new Map(required.map((name) => [name, 0]));
  for (const call of calls) {
    if (found.has(call.subagentType)) {
      found.set(call.subagentType, found.get(call.subagentType) + 1);
    }
  }
  let missing = 0;
  let foundRequired = 0;
  let duplicates = 0;
  for (const name of required) {
    const count = found.get(name) || 0;
    if (count === 0) {
      missing += 1;
    } else {
      foundRequired += 1;
      if (count > 1) {
        duplicates += 1;
      }
    }
  }
  const unexpectedCalls = calls.filter((call) => !requiredSet.has(call.subagentType));
  return { found, foundRequired, missing, duplicates, unexpectedCalls };
}

function summarizeRouterCalls(calls, invalidToolCalls) {
  const unexpectedCalls = calls.filter((call) => !requiredSet.has(call.subagentType));
  const selectedCalls = calls.filter((call) => requiredSet.has(call.subagentType));
  const selected = selectedCalls.length === 1 ? selectedCalls[0].subagentType : "";
  const noReviewerPass = expectedNoSubagent && calls.length === 0 && invalidToolCalls.length === 0;
  const status = noReviewerPass || (
    calls.length === 1
    && unexpectedCalls.length === 0
    && selected
    && (!expectedSubagent || selected === expectedSubagent)
    && invalidToolCalls.length === 0
  )
    ? "pass"
    : "fail";
  return {
    status,
    selected,
    selectedCalls,
    unexpectedCalls,
    expectedMismatch: Boolean(expectedSubagent && selected && selected !== expectedSubagent),
    missingExpected: Boolean(expectedSubagent && !selected),
    noReviewerExpected: expectedNoSubagent,
    noReviewerMatched: noReviewerPass,
  };
}

function summarizeInvalidTools(calls) {
  const forbiddenCalls = calls.filter((call) => forbiddenPlanningTools.has(call.tool));
  const counts = new Map();
  for (const call of calls) {
    addCount(counts, call.tool || "<unknown>");
  }
  return { forbiddenCalls, counts };
}

function collectDbTimeline() {
  const sessionRows = readJsonFile(process.env.OPENCODE_SESSION_CHECK_SESSION_FILE, []);
  const session = Array.isArray(sessionRows) && sessionRows.length > 0 ? sessionRows[0] : null;
  if (!session) {
    return null;
  }

  const eventRows = readJsonFile(process.env.OPENCODE_SESSION_CHECK_EVENTS_FILE, []);
  const messageRows = readJsonFile(process.env.OPENCODE_SESSION_CHECK_MESSAGES_FILE, []);
  const partRows = readJsonFile(process.env.OPENCODE_SESSION_CHECK_PARTS_FILE, []);

  const messages = messageRows.map((row) => {
    const data = parseMaybeJson(row.data) || {};
    return {
      id: row.id,
      role: data.role || "",
      time: valueTime(row.time_created),
    };
  }).sort((a, b) => a.time - b.time || a.id.localeCompare(b.id));

  const switches = eventRows
    .filter((row) => row.type === "agent-switched")
    .map((row) => {
      const data = parseMaybeJson(row.data) || {};
      return {
        id: row.id,
        agent: data.agent || "unknown",
        time: valueTime(row.time_created),
      };
    })
    .sort((a, b) => a.time - b.time || a.id.localeCompare(b.id));

  const taskCalls = [];
  const invalidToolCalls = [];
  for (const row of partRows) {
    const data = parseMaybeJson(row.data) || {};
    const state = data.state && typeof data.state === "object" ? data.state : {};

    if (data.tool === "task") {
      const input = parseMaybeJson(state.input ?? data.input ?? {});
      const subagentType = input && typeof input === "object" ? input.subagent_type : undefined;
      taskCalls.push({
        id: row.id,
        messageId: row.message_id || "",
        time: valueTime(row.time_created),
        subagentType: subagentType || "<missing subagent_type>",
        status: state.status || data.status || "unknown",
      });
    }

    if (data.tool === "invalid") {
      const input = parseMaybeJson(state.input ?? data.input ?? {});
      invalidToolCalls.push({
        id: row.id,
        messageId: row.message_id || "",
        time: valueTime(row.time_created),
        tool: input && typeof input === "object" && input.tool ? input.tool : "<unknown>",
        status: state.status || data.status || "unknown",
        error: input && typeof input === "object" && input.error ? input.error : String(state.output || ""),
      });
    }
  }

  const maxTimes = [
    valueTime(session.time_updated),
    ...messages.map((message) => message.time),
    ...switches.map((event) => event.time),
    ...taskCalls.map((call) => call.time),
    ...invalidToolCalls.map((call) => call.time),
  ];

  return {
    source: "db",
    session: {
      id: session.id || requestedSessionId,
      title: session.title || "",
      directory: session.directory || "",
      createdAgent: session.agent || "unknown",
      start: valueTime(session.time_created),
      end: Math.max(...maxTimes, valueTime(session.time_created)),
    },
    messages,
    switches,
    taskCalls,
    invalidToolCalls,
  };
}

function collectSubagentTypeMatches(text) {
  const matches = [];
  const rawPattern = /"subagent_type"\s*:\s*"([^"]+)"/g;
  const escapedPattern = /\\"subagent_type\\"\s*:\s*\\"([^\\"]+)\\"/g;
  let match;
  while ((match = rawPattern.exec(text)) !== null) {
    matches.push({ index: match.index, value: match[1] });
  }
  while ((match = escapedPattern.exec(text)) !== null) {
    matches.push({ index: match.index, value: match[1] });
  }
  matches.sort((a, b) => a.index - b.index);
  return matches;
}

function collectExportTimeline() {
  const raw = fs.readFileSync(process.env.OPENCODE_SESSION_CHECK_EXPORT_FILE, "utf8");
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

  const taskCalls = [];
  const invalidToolCalls = [];
  function visit(value) {
    if (!value || typeof value !== "object") {
      return;
    }
    if (value.tool === "task") {
      const state = value.state && typeof value.state === "object" ? value.state : {};
      const input = parseMaybeJson(state.input ?? value.input ?? {});
      const subagentType = input && typeof input === "object" ? input.subagent_type : undefined;
      taskCalls.push({
        id: value.id || "",
        messageId: value.messageID || value.messageId || "",
        time: 0,
        subagentType: subagentType || "<missing subagent_type>",
        status: state.status || value.status || "unknown",
      });
    }
    if (value.tool === "invalid") {
      const state = value.state && typeof value.state === "object" ? value.state : {};
      const input = parseMaybeJson(state.input ?? value.input ?? {});
      invalidToolCalls.push({
        id: value.id || "",
        messageId: value.messageID || value.messageId || "",
        time: 0,
        tool: input && typeof input === "object" && input.tool ? input.tool : "<unknown>",
        status: state.status || value.status || "unknown",
        error: input && typeof input === "object" && input.error ? input.error : String(state.output || ""),
      });
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
      const nextTaskPattern = /"tool"\s*:\s*"task"/g;
      nextTaskPattern.lastIndex = match.index + match[0].length;
      const nextTaskMatch = nextTaskPattern.exec(cleaned);
      const nextTask = nextTaskMatch ? nextTaskMatch.index : -1;
      const maxWindowEnd = Math.min(cleaned.length, match.index + 250000);
      const windowEnd = nextTask === -1 ? maxWindowEnd : Math.min(nextTask, maxWindowEnd);
      const window = cleaned.slice(match.index, windowEnd);
      const subagentMatches = collectSubagentTypeMatches(window);
      const subagentType = subagentMatches.length > 0
        ? subagentMatches[subagentMatches.length - 1].value
        : "<missing subagent_type>";
      taskCalls.push({
        id: "",
        messageId: "",
        time: 0,
        subagentType,
        status: "unknown",
      });
    }

    const invalidPattern = /"tool"\s*:\s*"invalid"/g;
    while ((match = invalidPattern.exec(cleaned)) !== null) {
      const window = cleaned.slice(match.index, Math.min(cleaned.length, match.index + 20000));
      const toolMatch = window.match(/"tool"\s*:\s*"([^"]+)"/);
      const attemptedToolMatch = window.match(/"input"\s*:\s*\{[^}]*"tool"\s*:\s*"([^"]+)"/);
      const errorMatch = window.match(/"error"\s*:\s*"([^"]+)"/);
      invalidToolCalls.push({
        id: "",
        messageId: "",
        time: 0,
        tool: attemptedToolMatch ? attemptedToolMatch[1] : (toolMatch ? toolMatch[1] : "<unknown>"),
        status: "unknown",
        error: errorMatch ? errorMatch[1] : "",
      });
    }
  }

  if (exported) {
    visit(exported);
  } else {
    scanRawExport(raw);
  }

  if (parseWarning) {
    console.error(`Warning: strict JSON parse failed, used task-call text scan instead: ${parseWarning}`);
    console.error("");
  }

  const rawId = raw.match(/"id"\s*:\s*"(ses_[^"]+)"/);
  const rawTitle = raw.match(/"title"\s*:\s*"([^"]+)"/);
  const rawDirectory = raw.match(/"directory"\s*:\s*"([^"]+)"/);
  const info = exported ? exported.info || {} : {
    id: rawId ? rawId[1] : undefined,
    title: rawTitle ? rawTitle[1] : undefined,
    directory: rawDirectory ? rawDirectory[1] : undefined,
  };

  return {
    source: exported ? "export-strict" : "export-raw-scan",
    session: {
      id: info.id || requestedSessionId || "<unknown>",
      title: info.title || "",
      directory: info.directory || "",
      createdAgent: "unknown",
      start: 0,
      end: 0,
    },
    messages: [],
    switches: [],
    taskCalls,
    invalidToolCalls,
  };
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function scanAgentLogs(id) {
  const enabled = process.env.OPENCODE_SESSION_CHECK_AGENT_LOG !== "0";
  const logDir = process.env.OPENCODE_SESSION_CHECK_LOG_DIR || "";
  const result = {
    status: enabled ? "missing" : "disabled",
    createdAgent: "unknown",
    primaryCounts: new Map(),
    matchedFiles: 0,
  };
  if (!enabled || !logDir) {
    return result;
  }

  let entries;
  try {
    entries = fs.readdirSync(logDir, { withFileTypes: true });
  } catch {
    return result;
  }

  const files = entries
    .filter((entry) => entry.isFile() && entry.name.endsWith(".log"))
    .map((entry) => path.join(logDir, entry.name))
    .sort();

  const idPattern = escapeRegExp(id);
  const sessionCreatePattern = new RegExp(`service=session id=${idPattern}\\b.*\\bcreated\\b`);
  const primaryPattern = new RegExp(`service=llm\\b.*\\bsession\\.id=${idPattern}\\b.*\\bmode=primary\\b`);
  const agentPattern = /\bagent=([^ ]+)/;

  for (const file of files) {
    let text;
    try {
      text = fs.readFileSync(file, "utf8");
    } catch {
      continue;
    }
    if (!text.includes(id)) {
      continue;
    }
    result.matchedFiles += 1;
    for (const line of text.split(/\r?\n/)) {
      if (!line.includes(id)) {
        continue;
      }
      if (result.createdAgent === "unknown" && sessionCreatePattern.test(line) && !line.includes(" parentID=")) {
        const match = line.match(agentPattern);
        if (match) {
          result.createdAgent = match[1];
        }
      }
      if (primaryPattern.test(line)) {
        const match = line.match(agentPattern);
        if (match && match[1] !== "title") {
          addCount(result.primaryCounts, match[1]);
        }
      }
    }
  }
  if (result.matchedFiles > 0) {
    result.status = "found";
  }
  return result;
}

function buildScope(timeline) {
  if (checkScope === "session") {
    return {
      start: timeline.session.start,
      end: timeline.session.end,
      agent: timeline.session.createdAgent,
      userMessageId: "",
      available: true,
    };
  }

  if (timeline.source !== "db") {
    return {
      start: 0,
      end: 0,
      agent: "unknown",
      userMessageId: "",
      available: false,
    };
  }

  if (checkScope === "latest-turn") {
    const userMessages = timeline.messages.filter((message) => message.role === "user");
    const latestUser = userMessages[userMessages.length - 1];
    if (!latestUser) {
      return {
        start: timeline.session.start,
        end: timeline.session.end,
        agent: timeline.session.createdAgent,
        userMessageId: "",
        available: true,
      };
    }
    const priorSwitches = timeline.switches.filter((event) => event.time <= latestUser.time && scopedPrimaryAgents.has(event.agent));
    const latestSwitch = priorSwitches[priorSwitches.length - 1];
    return {
      start: latestUser.time,
      end: timeline.session.end,
      agent: latestSwitch ? latestSwitch.agent : timeline.session.createdAgent,
      userMessageId: latestUser.id,
      available: true,
    };
  }

  const workflowSwitches = timeline.switches.filter((event) => scopedPrimaryAgents.has(event.agent));
  const latestSwitch = workflowSwitches[workflowSwitches.length - 1];
  return {
    start: latestSwitch ? latestSwitch.time : timeline.session.start,
    end: timeline.session.end,
    agent: latestSwitch ? latestSwitch.agent : timeline.session.createdAgent,
    userMessageId: "",
    available: true,
  };
}

function primaryCountsFromDb(timeline) {
  const counts = new Map();
  if (timeline.session.createdAgent && scopedPrimaryAgents.has(timeline.session.createdAgent)) {
    addCount(counts, timeline.session.createdAgent);
  }
  for (const event of timeline.switches) {
    if (scopedPrimaryAgents.has(event.agent)) {
      addCount(counts, event.agent);
    }
  }
  return counts;
}

const timeline = timelineSource === "db" ? collectDbTimeline() : collectExportTimeline();
if (!timeline) {
  console.error("Could not load OpenCode session timeline from DB or export.");
  process.exit(2);
}

const agentLog = scanAgentLogs(timeline.session.id);
const dbPrimaryCounts = timeline.source === "db" ? primaryCountsFromDb(timeline) : new Map();
const primaryCounts = dbPrimaryCounts.size > 0 ? dbPrimaryCounts : agentLog.primaryCounts;
const primaryAgents = Array.from(primaryCounts.keys()).sort();
const createdAgent = timeline.session.createdAgent !== "unknown" ? timeline.session.createdAgent : agentLog.createdAgent;
const workflowPrimaryAgents = primaryAgents.filter((agent) => workflowAgents.has(agent));
const createdWorkflowAgent = workflowAgents.has(createdAgent) ? createdAgent : "";
const createdMismatch = createdWorkflowAgent
  ? workflowPrimaryAgents.some((agent) => agent !== createdWorkflowAgent)
  : false;
const mixedPrimaryAgents = workflowPrimaryAgents.length > 1 || createdMismatch;

const scopeInfo = buildScope(timeline);
let scopedCalls = [];
let scopedInvalidToolCalls = [];
let scopedUnavailable = false;
if (!scopeInfo.available) {
  scopedUnavailable = true;
  if (checkScope === "session") {
    scopedCalls = timeline.taskCalls;
    scopedInvalidToolCalls = timeline.invalidToolCalls || [];
  }
} else if (checkScope === "session") {
  scopedCalls = timeline.taskCalls;
  scopedInvalidToolCalls = timeline.invalidToolCalls || [];
} else {
  scopedCalls = timeline.taskCalls.filter((call) => call.time >= scopeInfo.start && call.time <= scopeInfo.end);
  scopedInvalidToolCalls = (timeline.invalidToolCalls || []).filter((call) => call.time >= scopeInfo.start && call.time <= scopeInfo.end);
}

const sessionSummary = summarizeCalls(timeline.taskCalls);
const scopeSummary = summarizeCalls(scopedCalls);
const sessionInvalidSummary = summarizeInvalidTools(timeline.invalidToolCalls || []);
const scopeInvalidSummary = summarizeInvalidTools(scopedInvalidToolCalls);
const isRouterScope = scopeInfo.agent === "subagent-router";
const forbiddenInvalidInScope = scopeInfo.agent === "ping-pong-plan"
  ? scopeInvalidSummary.forbiddenCalls
  : [];
const routerInvalidInScope = isRouterScope
  ? scopeInvalidSummary.forbiddenCalls
  : [];
const routerSummary = isRouterScope
  ? summarizeRouterCalls(scopedCalls, routerInvalidInScope)
  : null;
const invalidExpectedScope = Boolean(expectedSubagent && !isRouterScope);
const invalidNoSubagentScope = Boolean(expectedNoSubagent && !isRouterScope);

if (invalidNoSubagentScope) {
  console.error("");
  console.error(`--expect-no-subagent is only valid when the selected scope agent is subagent-router; scope agent is ${scopeInfo.agent || "unknown"}.`);
  process.exit(2);
}

const routerNoReviewerPass = Boolean(isRouterScope && expectedNoSubagent && routerSummary && routerSummary.noReviewerMatched);
const routerSummaryRequired = routerNoReviewerPass ? 0 : 1;
const routerSummaryFound = routerNoReviewerPass ? 0 : (routerSummary && routerSummary.selected ? 1 : 0);
const routerSummaryMissing = routerNoReviewerPass ? 0 : (routerSummary && routerSummary.selected ? 0 : 1);
const routerSummaryDuplicates = routerNoReviewerPass ? 0 : (scopedCalls.length > 1 ? scopedCalls.length - 1 : 0);

console.log(`SESSION_ID=${timeline.session.id}`);
console.log(`SESSION_TITLE=${timeline.session.title}`);
console.log(`SESSION_DIRECTORY=${timeline.session.directory}`);
console.log(`TIMELINE_SOURCE=${timeline.source}`);
console.log(`CHECK_SCOPE=${checkScope}`);
console.log(`SCOPE_START=${formatTime(scopeInfo.start)}`);
console.log(`SCOPE_END=${formatTime(scopeInfo.end)}`);
console.log(`SCOPE_AGENT=${scopeInfo.agent || "unknown"}`);
if (checkScope === "latest-turn") {
  console.log(`SCOPE_USER_MESSAGE_ID=${scopeInfo.userMessageId || "unknown"}`);
}
console.log(`SCOPE_TASK_CALLS=${scopedCalls.length}`);
console.log(`SCOPE_INVALID_TOOL_CALLS=${scopedInvalidToolCalls.length}`);
console.log(`AGENT_LOG=${agentLog.status}`);
console.log(`SESSION_CREATED_AGENT=${createdAgent}`);
console.log(`SESSION_PRIMARY_AGENTS=${primaryAgents.length ? primaryAgents.join(",") : "unknown"}`);
for (const name of primaryAgents) {
  console.log(`PRIMARY_AGENT name=${name} count=${primaryCounts.get(name) || 0}`);
}
console.log(`MIXED_PRIMARY_AGENT status=${mixedPrimaryAgents ? "fail" : "pass"} agents=${primaryAgents.length ? primaryAgents.join(",") : "unknown"}`);
console.log("");
console.log(`Session: ${timeline.session.id}${timeline.session.title ? ` (${timeline.session.title})` : ""}`);
if (timeline.session.directory) {
  console.log(`Directory: ${timeline.session.directory}`);
}
console.log("");

if (scopedUnavailable) {
  console.log("Scoped validation is unavailable without the OpenCode SQLite timeline.");
  console.log("Use --scope session for export-only validation, or provide --db PATH.");
} else if (isRouterScope) {
  console.log("Routed reviewer task call in scope:");
  const selected = routerSummary.noReviewerExpected ? "none" : (routerSummary.selected || "none");
  console.log(`ROUTER_SUBAGENT name=${selected} status=${routerSummary.status} task_calls=${scopedCalls.length}`);
  if (expectedSubagent) {
    console.log(`ROUTER_EXPECTED name=${expectedSubagent} status=${routerSummary.expectedMismatch || routerSummary.missingExpected ? "fail" : "pass"}`);
  } else if (expectedNoSubagent) {
    console.log(`ROUTER_EXPECTED name=none status=${routerSummary.noReviewerMatched ? "pass" : "fail"}`);
  } else {
    console.log("ROUTER_EXPECTED name=none status=skipped");
  }
  for (const call of scopedCalls) {
    console.log(`ROUTER_TASK subagent_type=${call.subagentType} status=${call.status}`);
  }
} else {
  console.log("Required reviewer subagent task calls in scope:");
  for (const name of required) {
    const count = scopeSummary.found.get(name) || 0;
    if (count === 0) {
      console.log(`SUBAGENT name=${name} status=missing count=0`);
      console.log(`- ${name}: missing`);
    } else {
      console.log(`SUBAGENT name=${name} status=found count=${count}`);
      console.log(`- ${name}: found (${count} call${count === 1 ? "" : "s"})`);
    }
  }
}

if (isRouterScope) {
  console.log(`ROUTER_SUMMARY status=${routerSummary.status} selected=${routerSummary.selected || "none"} expected=${expectedSubagent || "none"} task_calls=${scopedCalls.length} unexpected=${routerSummary.unexpectedCalls.length} forbidden_invalid_tools=${routerInvalidInScope.length}`);
  console.log(`SCOPE_SUMMARY mode=router required=${routerSummaryRequired} found=${routerSummaryFound} missing=${routerSummaryMissing} duplicates=${routerSummaryDuplicates} unexpected=${routerSummary.unexpectedCalls.length} invalid_tools=${scopedInvalidToolCalls.length} forbidden_invalid_tools=${routerInvalidInScope.length} task_calls=${scopedCalls.length}`);
} else {
  console.log(`SCOPE_SUMMARY required=${required.length} found=${scopeSummary.foundRequired} missing=${scopeSummary.missing} duplicates=${scopeSummary.duplicates} unexpected=${scopeSummary.unexpectedCalls.length} invalid_tools=${scopedInvalidToolCalls.length} forbidden_invalid_tools=${forbiddenInvalidInScope.length} task_calls=${scopedCalls.length}`);
}
if (isRouterScope) {
  console.log(`SUMMARY mode=router required=${routerSummaryRequired} found=${routerSummaryFound} missing=${routerSummaryMissing} duplicates=${routerSummaryDuplicates} unexpected=${routerSummary.unexpectedCalls.length} invalid_tools=${(timeline.invalidToolCalls || []).length} forbidden_invalid_tools=${routerInvalidInScope.length} mixed_agents=${mixedPrimaryAgents ? 1 : 0} agent_log=${agentLog.status} task_calls=${timeline.taskCalls.length}`);
} else {
  console.log(`SUMMARY required=${required.length} found=${sessionSummary.foundRequired} missing=${sessionSummary.missing} duplicates=${sessionSummary.duplicates} unexpected=${sessionSummary.unexpectedCalls.length} invalid_tools=${(timeline.invalidToolCalls || []).length} forbidden_invalid_tools=${sessionInvalidSummary.forbiddenCalls.length} mixed_agents=${mixedPrimaryAgents ? 1 : 0} agent_log=${agentLog.status} task_calls=${timeline.taskCalls.length}`);
}

if (!scopedUnavailable && !isRouterScope && scopeSummary.duplicates > 0) {
  console.log("");
  console.log("Duplicate required reviewer task calls in scope:");
  for (const name of required) {
    const count = scopeSummary.found.get(name) || 0;
    if (count > 1) {
      console.log(`DUPLICATE_SUBAGENT name=${name} count=${count}`);
    }
  }
}

if (!scopedUnavailable && !isRouterScope && scopeSummary.unexpectedCalls.length > 0) {
  console.log("");
  console.log("Unexpected task calls in scope:");
  for (const call of scopeSummary.unexpectedCalls) {
    console.log(`UNEXPECTED_TASK subagent_type=${call.subagentType} status=${call.status}`);
  }
  console.log("");
  console.log("Other task calls in scope:");
  for (const call of scopeSummary.unexpectedCalls) {
    console.log(`- ${call.subagentType}: ${call.status}`);
  }
}

if (!scopedUnavailable && scopedInvalidToolCalls.length > 0) {
  console.log("");
  console.log("Invalid tool calls in scope:");
  for (const call of scopedInvalidToolCalls) {
    console.log(`INVALID_TOOL tool=${call.tool} status=${call.status}`);
    if (scopeInfo.agent === "ping-pong-plan" && forbiddenPlanningTools.has(call.tool)) {
      console.log(`FORBIDDEN_PLANNING_TOOL_ATTEMPT tool=${call.tool} agent=ping-pong-plan status=${call.status}`);
    } else if (scopeInfo.agent === "subagent-router" && forbiddenPlanningTools.has(call.tool)) {
      console.log(`ROUTER_FORBIDDEN_TOOL_ATTEMPT tool=${call.tool} agent=subagent-router status=${call.status}`);
    }
  }
}

if (!scopedUnavailable && scopedCalls.length === 0) {
  console.log("");
  console.log("No task-tool calls were found in the selected scope.");
  if (scopeInfo.agent === "ping-ping-build") {
    console.log("Hint: this scope used ping-ping-build. Reviewer calls should happen after implementation evidence exists; if it ended before review, the review loop is incomplete.");
  } else if (scopeInfo.agent === "ping-pong-plan") {
    console.log("Hint: this scope used ping-pong-plan but did not record reviewer task calls. Start a fresh session after updating global links and confirm the strict prompt is loaded.");
  } else if (scopeInfo.agent === "subagent-router") {
    console.log("Hint: this scope used subagent-router but did not record a reviewer task call. Start a fresh router session after updating global links and confirm the router prompt is loaded.");
  }
}

if (!scopedUnavailable && isRouterScope && scopedCalls.length !== 1) {
  if (expectedNoSubagent && scopedCalls.length === 0) {
    // No-reviewer router handoff is valid when explicitly requested.
  } else {
    console.error("");
    console.error(`Router scope expected exactly one reviewer task call, found ${scopedCalls.length}.`);
  }
}

if (!scopedUnavailable && isRouterScope && routerSummary.unexpectedCalls.length > 0) {
  console.error("");
  console.error(`Router scope found ${routerSummary.unexpectedCalls.length} task call${routerSummary.unexpectedCalls.length === 1 ? "" : "s"} with an unexpected subagent_type.`);
}

if (!scopedUnavailable && isRouterScope && routerSummary.expectedMismatch) {
  console.error("");
  console.error(`Router scope selected ${routerSummary.selected}, expected ${expectedSubagent}.`);
}

if (!scopedUnavailable && isRouterScope && expectedNoSubagent && !routerSummary.noReviewerMatched) {
  console.error("");
  console.error(`Router scope expected no reviewer task call, found ${scopedCalls.length}.`);
}

if (!scopedUnavailable && invalidExpectedScope) {
  console.error("");
  console.error(`--expect-subagent is only valid when the selected scope agent is subagent-router; scope agent is ${scopeInfo.agent || "unknown"}.`);
}

if (mixedPrimaryAgents) {
  console.error("");
  console.error(`Session mixed primary workflow agents: ${primaryAgents.join(",") || "unknown"}. Start a fresh session with only ping-pong-plan or only ping-ping-build.`);
}

let failed = false;
if (scopedUnavailable) {
  failed = true;
}
if (!scopedUnavailable && (
  (!isRouterScope && (
    scopeSummary.missing > 0
    || scopeSummary.duplicates > 0
    || scopeSummary.unexpectedCalls.length > 0
  ))
  || (isRouterScope && routerSummary.status !== "pass")
  || forbiddenInvalidInScope.length > 0
  || invalidExpectedScope
)) {
  failed = true;
}
if (mixedPrimaryAgents) {
  failed = true;
}

if (failed) {
  console.error("");
  if (scopedUnavailable) {
    console.error(`Scoped validation is unavailable for --scope ${checkScope}.`);
  }
  if (!scopedUnavailable && scopeSummary.missing > 0) {
    if (!isRouterScope) {
      console.error(`Missing ${scopeSummary.missing} required subagent task call${scopeSummary.missing === 1 ? "" : "s"} in scope.`);
    }
  }
  if (!scopedUnavailable && !isRouterScope && scopeSummary.duplicates > 0) {
    console.error(`Found ${scopeSummary.duplicates} duplicated required subagent task target${scopeSummary.duplicates === 1 ? "" : "s"} in scope.`);
  }
  if (!scopedUnavailable && !isRouterScope && scopeSummary.unexpectedCalls.length > 0) {
    console.error(`Found ${scopeSummary.unexpectedCalls.length} unexpected task call${scopeSummary.unexpectedCalls.length === 1 ? "" : "s"} in scope.`);
  }
  if (!scopedUnavailable && forbiddenInvalidInScope.length > 0) {
    const tools = Array.from(new Set(forbiddenInvalidInScope.map((call) => call.tool))).join(",");
    console.error(`Found ${forbiddenInvalidInScope.length} forbidden unavailable tool attempt${forbiddenInvalidInScope.length === 1 ? "" : "s"} in ping-pong-plan scope: ${tools}. Use ping-ping-build for implementation.`);
  }
  if (!scopedUnavailable && isRouterScope && routerInvalidInScope.length > 0) {
    const tools = Array.from(new Set(routerInvalidInScope.map((call) => call.tool))).join(",");
    console.error(`Found ${routerInvalidInScope.length} forbidden unavailable tool attempt${routerInvalidInScope.length === 1 ? "" : "s"} in subagent-router scope: ${tools}. The router must stay read-only.`);
  }
  process.exit(1);
}
NODE
node_status="$?"
set -e

if [[ "$json_output" -eq 1 ]]; then
  node -e '
const fs = require("fs");
const exitCode = Number(process.argv[1]);
const stdoutPath = process.argv[2];
const stderrPath = process.argv[3];
function lines(path) {
  const text = fs.readFileSync(path, "utf8");
  return text.length ? text.replace(/\n$/, "").split(/\n/) : [];
}
process.stdout.write(JSON.stringify({
  exit_code: exitCode,
  stdout: lines(stdoutPath),
  stderr: lines(stderrPath),
}, null, 2) + "\n");
' "$node_status" "$node_stdout" "$node_stderr"
elif [[ "$failures_only" -eq 1 ]]; then
  awk '
    /^SESSION_ID=/ ||
    /^SESSION_TITLE=/ ||
    /^SESSION_DIRECTORY=/ ||
    /^TIMELINE_SOURCE=/ ||
    /^CHECK_SCOPE=/ ||
    /^SCOPE_AGENT=/ ||
    /^MIXED_PRIMARY_AGENT status=fail/ ||
    /^ROUTER_SUBAGENT / ||
    /^ROUTER_EXPECTED .*status=fail/ ||
    /^ROUTER_TASK / ||
    /^ROUTER_FORBIDDEN_TOOL_ATTEMPT / ||
    /^ROUTER_SUMMARY / ||
    /^SUBAGENT .*status=missing/ ||
    /^DUPLICATE_SUBAGENT / ||
    /^UNEXPECTED_TASK / ||
    /^INVALID_TOOL / ||
    /^FORBIDDEN_PLANNING_TOOL_ATTEMPT / ||
    /^SCOPE_SUMMARY / ||
    /^SUMMARY / {
      print
    }
  ' "$node_stdout"
  awk '
    /^Warning:/ ||
    /^Session mixed primary workflow agents:/ ||
    /^Router scope / ||
    /^--expect-subagent / ||
    /^Scoped validation is unavailable/ ||
    /^Missing / ||
    /^Found / {
      print
    }
  ' "$node_stderr" >&2
else
  cat "$node_stdout"
  cat "$node_stderr" >&2
fi

exit "$node_status"
