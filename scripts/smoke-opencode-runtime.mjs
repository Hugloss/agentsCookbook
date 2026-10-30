#!/usr/bin/env node
// Deterministic contract regressions. The CLI transport is stubbed; these are
// not native runtime or model-quality qualification runs.
import assert from "node:assert/strict"
import fs from "node:fs"
import os from "node:os"
import path from "node:path"
import { spawnSync } from "node:child_process"
import { fileURLToPath, pathToFileURL } from "node:url"

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "cookbook-opencode-regressions-"))
const target = path.join(scratch, "target repo")
const globalDir = path.join(scratch, "opencode config")
const skillsDir = path.join(scratch, "shared skills")
const bin = path.join(scratch, "bin")
const trace = path.join(scratch, "export.json")
const commandLog = path.join(scratch, "commands.jsonl")
const reviewers = JSON.parse(fs.readFileSync(path.join(repo, "reviewers.json"), "utf8"))
const sessionId = "ses_contract_probe"
let checks = 0
const pass = name => { checks++; console.log(`SMOKE name=${name} status=pass`) }

function run(script, args = [], additions = {}) {
  const env = { ...process.env, PATH: `${bin}${path.delimiter}${process.env.PATH}`, AC_TEST_REPO: repo,
    AC_TEST_TRACE: trace, AC_TEST_COMMANDS: commandLog, AC_TEST_VERSION: "1.19.5", ...additions }
  delete env.AGENTS_COOKBOOK_RUN_DIR
  if (additions.AGENTS_COOKBOOK_RUN_DIR) env.AGENTS_COOKBOOK_RUN_DIR = additions.AGENTS_COOKBOOK_RUN_DIR
  return spawnSync("bash", [path.join(repo, "scripts", script), ...args], { cwd: target, env, encoding: "utf8", timeout: 30000 })
}

function expectedStatus(result, status, name) {
  assert.equal(result.error, undefined, `${name}: ${result.error}`)
  assert.equal(result.status, status, `${name}:\n${result.stdout}\n${result.stderr}`)
  pass(name)
}

function exportFixture() {
  return {
    info: { id: sessionId, agent: "ping-pong-plan", title: "Contract probe", directory: target, time: { created: 10, updated: 30 } },
    messages: [{
      info: { id: "msg_review", sessionID: sessionId, role: "assistant", agent: "ping-pong-plan", time: { created: 20 } },
      parts: reviewers.map((name, index) => ({
        id: `part_${index}`, messageID: "msg_review", sessionID: sessionId, callID: `call_${index}`, type: "tool", tool: "task",
        state: { status: "completed", input: { subagent_type: name }, output: `<task id="ses_child_${index}" state="completed">\n<task_result>\nCLEAN: bounded review completed.\n</task_result>\n</task>` },
      })),
    }],
  }
}

function checkExport(name, mutate, status = 1, options = {}) {
  const value = exportFixture()
  mutate(value)
  fs.writeFileSync(trace, JSON.stringify(value))
  const result = run("check-opencode-session.sh", ["--db", path.join(scratch, "missing.db"), "--scope", "session", "--no-agent-log-check", ...(options.args || []), sessionId], options.env)
  expectedStatus(result, status, name)
  return result
}

try {
  for (const dir of [target, globalDir, skillsDir, bin, path.join(globalDir, "agents"), path.join(globalDir, "plugins")]) fs.mkdirSync(dir, { recursive: true })
  for (const name of fs.readdirSync(path.join(repo, "agents")).filter(name => name.endsWith(".md"))) {
    fs.symlinkSync(path.join(repo, "agents", name), path.join(globalDir, "agents", name))
  }
  const skills = fs.readdirSync(path.join(repo, "skills")).filter(name => fs.existsSync(path.join(repo, "skills", name, "SKILL.md")))
  for (const name of skills) fs.symlinkSync(path.join(repo, "skills", name), path.join(skillsDir, name))
  const entry = spawnSync("bash", ["-c", 'source "$1"; ac_opencode_artifact_entry_source "$2"', "entrypoint-fixture",
    path.join(repo, "scripts/lib-opencode.sh"), path.join(repo, "adapters/opencode/review-artifact.js")], { encoding: "utf8" })
  assert.equal(entry.status, 0, entry.stderr)
  fs.writeFileSync(path.join(globalDir, "plugins/agents-cookbook-review-artifact.js"), entry.stdout)
  fs.writeFileSync(path.join(bin, "opencode"), `#!/usr/bin/env node
const fs=require("fs"),path=require("path");const args=process.argv.slice(2),repo=process.env.AC_TEST_REPO,variant=process.env.AC_TEST_VARIANT;
fs.appendFileSync(process.env.AC_TEST_COMMANDS,JSON.stringify(args)+"\\n");
if(args[0]==="--version"){console.log(process.env.AC_TEST_VERSION);process.exit(0)}
if(args[0]==="export"){process.stdout.write(fs.readFileSync(process.env.AC_TEST_TRACE,"utf8"));process.exit(0)}
if(args[0]==="session"&&args[1]==="list"){console.log(process.env.AC_TEST_SESSIONS||"[]");process.exit(0)}
if(args[0]==="debug"&&args[1]==="skill"){
const names=fs.readdirSync(path.join(repo,"skills")).filter(n=>fs.existsSync(path.join(repo,"skills",n,"SKILL.md")));
if(variant==="catalog-stderr")console.error("Native catalog diagnostic on stderr");
console.log(JSON.stringify(names.map((name,i)=>({name:variant==="skill-substring"&&i===0?name+"-shadow":name,description:name,content:variant==="large-catalog"?"x".repeat(4096):""}))));process.exit(0)}
if(args[0]==="debug"&&args[1]==="agent"){
const name=args[2],primary=["ping-pong-plan","ping-ping-build","subagent-router"].includes(name),build=name==="ping-ping-build";
const tools={invalid:false,question:false,bash:build,read:true,glob:true,grep:true,edit:build,write:build,task:primary,webfetch:false,todowrite:false,skill:!primary};
if(process.env.AGENTS_COOKBOOK_RUN_DIR&&variant!=="missing-artifact"){tools.review_artifact=!primary;tools.review_artifact_read=primary}
if(variant==="extra-tool")tools.external_write=true;if(variant==="subagent-conflict")tools.subagent=true;
console.log(JSON.stringify({name:variant==="wrong-agent"?"other":name,mode:primary?"primary":"subagent",tools,prompt:fs.readFileSync(path.join(repo,"agents",name+".md"),"utf8")}));process.exit(0)}
console.error("Unexpected stub CLI call: "+args.join(" "));process.exit(9);
`, { mode: 0o755 })

  const preflight = ["--global-dir", globalDir, "--shared-skill-dir", skillsDir, target]
  expectedStatus(run("preflight-opencode-ping-pong.sh", preflight), 0, "opencode_absent_disabled_artifact_tools")
  expectedStatus(run("check-opencode-effective-reviewers.sh", [target]), 0, "opencode_effective_reviewers_without_artifacts")
  expectedStatus(run("preflight-opencode-ping-pong.sh", preflight, { AGENTS_COOKBOOK_RUN_DIR: path.join(scratch, "run") }), 0, "opencode_artifact_tool_mode")
  expectedStatus(run("preflight-opencode-ping-pong.sh", preflight, { AC_TEST_VARIANT: "large-catalog" }), 0, "opencode_large_catalog_regular_file_capture")
  expectedStatus(run("preflight-opencode-ping-pong.sh", preflight, { AC_TEST_VARIANT: "catalog-stderr" }), 0, "opencode_catalog_stderr_is_not_json")
  for (const variant of ["extra-tool", "subagent-conflict", "wrong-agent", "skill-substring"]) {
    expectedStatus(run("preflight-opencode-ping-pong.sh", preflight, { AC_TEST_VARIANT: variant }), 1, `opencode_preflight_rejects_${variant}`)
  }
  expectedStatus(run("preflight-opencode-ping-pong.sh", preflight, { AGENTS_COOKBOOK_RUN_DIR: path.join(scratch, "run"), AC_TEST_VARIANT: "missing-artifact" }), 1, "opencode_required_artifact_tool_missing")
  for (const version of ["opencode v2.2.3", "opencode v2.2.4", "unrecognized output"]) {
    fs.writeFileSync(commandLog, "")
    expectedStatus(run("check-opencode-effective-reviewers.sh", [target], { AC_TEST_VERSION: version }), 1, `opencode_unsupported_version_${version.replaceAll(" ", "_")}`)
    assert.deepEqual(fs.readFileSync(commandLog, "utf8").trim().split("\n").map(JSON.parse), [["--version"]])
  }

  checkExport("opencode_completed_review_gate", () => {}, 0)
  for (const status of ["error", "pending", "running", "unknown"]) {
    const result = checkExport(`opencode_rejects_${status}_tasks`, value => value.messages[0].parts.forEach(part => { part.state.status = status }))
    assert.match(result.stdout, /SCOPE_UNUSABLE_TASK_CALLS=9/)
  }
  for (const output of ["", "  \n", '<task id="ses_child" state="completed">\n<task_result> \n </task_result>\n</task>', '<task id="ses_child" state="running">\n<task_result>Started</task_result>\n</task>']) {
    checkExport(`opencode_rejects_empty_or_running_result_${checks}`, value => { value.messages[0].parts[0].state.output = output })
  }
  checkExport("opencode_rejects_background_launch", value => { value.messages[0].parts[0].state.metadata = { background: true } })
  checkExport("opencode_incomplete_native_envelope", value => { value.messages[0].parts[0].state.output = '<task id="ses_child" state="completed"><task_result>review</task_result>' })
  checkExport("opencode_legacy_empty_result", value => { value.messages[0].parts[0].state.output = 'task_id: ses_child\n\n<task_result> \n </task_result>' })
  checkExport("opencode_legacy_completed_result", value => { value.messages[0].parts[0].state.output = 'task_id: ses_child\n\n<task_result>CLEAN: inspected scope.</task_result>' }, 0)
  checkExport("opencode_nested_payload_is_not_execution", value => { value.untrusted = value.messages[0].parts; value.messages[0].parts = [] })
  checkExport("opencode_duplicate_call_identity", value => { value.messages[0].parts[1].callID = value.messages[0].parts[0].callID }, 2)
  checkExport("opencode_duplicate_part_identity", value => { value.messages[0].parts[1].id = value.messages[0].parts[0].id }, 2)
  checkExport("opencode_foreign_session", value => { value.info.id = "ses_other" }, 2)
  checkExport("opencode_foreign_message", value => { value.messages[0].info.sessionID = "ses_other" }, 2)
  checkExport("opencode_foreign_part", value => { value.messages[0].parts[0].messageID = "msg_other" }, 2)
  checkExport("opencode_user_payload_is_not_execution", value => { value.messages[0].info.role = "user" }, 2)
  checkExport("opencode_missing_call_identity", value => { delete value.messages[0].parts[0].callID }, 2)
  checkExport("opencode_unverified_primary", value => { delete value.info.agent; delete value.messages[0].info.agent })
  checkExport("opencode_foreign_task_primary", value => { value.messages[0].info.agent = "other-primary" })
  const jsonFailure = checkExport("opencode_failed_gate_json_exit", value => { value.messages[0].parts[0].state.status = "error" }, 1, { args: ["--json"] })
  assert.equal(JSON.parse(jsonFailure.stdout).exit_code, 1)
  fs.writeFileSync(trace, JSON.stringify(exportFixture()).slice(0, -1))
  const malformed = run("check-opencode-session.sh", ["--db", path.join(scratch, "missing.db"), "--scope", "session", "--no-agent-log-check", "--failures-only", sessionId])
  expectedStatus(malformed, 2, "opencode_malformed_export_never_text_scans")
  assert.match(malformed.stderr, /Invalid OpenCode session evidence/)

  fs.writeFileSync(trace, JSON.stringify(exportFixture()))
  const selected = run("check-opencode-session.sh", ["--db", path.join(scratch, "missing.db"), "--scope", "session", "--no-agent-log-check"], {
    AC_TEST_SESSIONS: JSON.stringify([{ id: "ses_other", directory: scratch }, { id: sessionId, directory: target }]),
  })
  expectedStatus(selected, 0, "opencode_latest_session_binds_current_directory")
  expectedStatus(run("check-opencode-session.sh", ["--db", path.join(scratch, "missing.db"), "--scope", "session", "--no-agent-log-check"], {
    AC_TEST_SESSIONS: JSON.stringify([{ id: "ses_other", directory: scratch }]),
  }), 1, "opencode_other_directory_cannot_qualify")
  expectedStatus(run("check-opencode-session.sh", ["--db", path.join(scratch, "missing.db"), "--scope", "latest-turn", "--no-agent-log-check", sessionId]), 1, "opencode_missing_scope_evidence_stays_incomplete")
  expectedStatus(run("check-opencode-session.sh", ["--db", path.join(scratch, "missing.db"), "--scope", "session", sessionId], { AC_TEST_VERSION: "opencode v2.2.4" }), 2, "opencode_v2_session_contract_not_guessed")

  // Exercise the default SQLite route with real SQLite query semantics. Python's
  // standard-library driver supplies the CLI transport when sqlite3 is absent;
  // no database or package is installed into the user's environment.
  const python = spawnSync("python3", ["--version"], { encoding: "utf8" })
  assert.equal(python.status, 0, "SQLite regression fixtures require Python 3's standard-library sqlite3")
  fs.writeFileSync(path.join(bin, "sqlite3"), `#!/usr/bin/env python3
import json,sqlite3,sys
db,query=sys.argv[-2:]
with sqlite3.connect("file:"+db+"?mode=ro",uri=True) as connection:
    connection.row_factory=sqlite3.Row
    rows=connection.execute(query).fetchall()
    if "-json" in sys.argv: print(json.dumps([dict(row) for row in rows]))
    else:
        for row in rows: print("|".join(str(value) for value in row))
`, { mode: 0o755 })
  const dbPath = path.join(scratch, "session.db")
  const seedDatabase = `import json,sqlite3,sys
db,raw,variant=sys.argv[1:]
fixture=json.loads(raw)
with sqlite3.connect(db) as c:
    c.executescript("DROP TABLE IF EXISTS session;DROP TABLE IF EXISTS session_message;DROP TABLE IF EXISTS message;DROP TABLE IF EXISTS part;CREATE TABLE session(id TEXT,parent_id TEXT,title TEXT,agent TEXT,directory TEXT,time_created INTEGER,time_updated INTEGER);CREATE TABLE session_message(id TEXT,session_id TEXT,type TEXT,time_created INTEGER,time_updated INTEGER,data TEXT);CREATE TABLE message(id TEXT,session_id TEXT,time_created INTEGER,time_updated INTEGER,data TEXT);CREATE TABLE part(id TEXT,message_id TEXT,session_id TEXT,time_created INTEGER,time_updated INTEGER,data TEXT);")
    info=fixture["info"];sid=info["id"]
    c.execute("INSERT INTO session VALUES(?,?,?,?,?,?,?)",(sid,None,info["title"],info["agent"],info["directory"],10,50))
    message=fixture["messages"][0]
    c.execute("INSERT INTO message VALUES(?,?,?,?,?)",(message["info"]["id"],sid,20,30,json.dumps(message["info"])))
    for part in message["parts"]: c.execute("INSERT INTO part VALUES(?,?,?,?,?,?)",(part["id"],part["messageID"],sid,20,30,json.dumps(part)))
    if variant in ["user","new-turn"]:
        c.execute("INSERT INTO message VALUES(?,?,?,?,?)",("msg_user",sid,15 if variant=="user" else 40,40,json.dumps({"role":"user"})))
    if variant=="other-primary":
        c.execute("INSERT INTO session_message VALUES(?,?,?,?,?,?)",("switch",sid,"agent-switched",40,40,json.dumps({"agent":"other-primary"})))
    if variant=="child":
        c.execute("INSERT INTO session VALUES(?,?,?,?,?,?,?)",("ses_newer_child",sid,"Reviewer", "plan-coverage-reviewer", info["directory"],20,90))
`
  function checkDatabase(name, variant, status, args = [], mutate = () => {}) {
    const value = exportFixture()
    mutate(value)
    const seeded = spawnSync("python3", ["-c", seedDatabase, dbPath, JSON.stringify(value), variant], { encoding: "utf8" })
    assert.equal(seeded.status, 0, seeded.stderr)
    const result = run("check-opencode-session.sh", ["--db", dbPath, "--no-agent-log-check", ...args])
    expectedStatus(result, status, name)
    assert.match(result.stdout, /TIMELINE_SOURCE=db/)
    return result
  }
  checkDatabase("opencode_sqlite_default_segment", "", 0, [sessionId])
  const failedDatabase = checkDatabase("opencode_sqlite_failed_tasks", "", 1, [sessionId], value => value.messages[0].parts.forEach(part => { part.state.status = "error" }))
  assert.match(failedDatabase.stdout, /SCOPE_UNUSABLE_TASK_CALLS=9/)
  checkDatabase("opencode_sqlite_latest_turn", "user", 0, ["--scope", "latest-turn", sessionId])
  checkDatabase("opencode_sqlite_missing_user_prompt", "", 1, ["--scope", "latest-turn", sessionId])
  checkDatabase("opencode_sqlite_new_turn_cannot_reuse_reviews", "new-turn", 1, ["--scope", "latest-turn", sessionId])
  checkDatabase("opencode_sqlite_unknown_primary_cannot_reuse_segment", "other-primary", 1, [sessionId])
  const rootSelection = checkDatabase("opencode_sqlite_latest_selects_root_session", "child", 0)
  assert.match(rootSelection.stdout, new RegExp(`SESSION_ID=${sessionId}`))

  // Exercise the real artifact write/read implementations. Only the runtime's
  // schema factory is replaced so this regression requires no package install.
  const adapterRoot = path.join(scratch, "adapter")
  const adapterDir = path.join(adapterRoot, "adapters/opencode")
  fs.mkdirSync(adapterDir, { recursive: true })
  fs.copyFileSync(path.join(repo, "reviewers.json"), path.join(adapterRoot, "reviewers.json"))
  fs.writeFileSync(path.join(adapterDir, "tool.mjs"), 'export const tool=value=>value;const schema={describe(){return this},optional(){return this}};tool.schema={string:()=>({...schema})};\n')
  const modulePath = path.join(adapterDir, "review-artifact.mjs")
  fs.copyFileSync(path.join(repo, "adapters/opencode/review-artifact.js"), modulePath)
  const { AgentsCookbookReviewArtifacts } = await import(pathToFileURL(modulePath))
  const { tool } = await import(pathToFileURL(path.join(adapterDir, "tool.mjs")))
  const reviewer = reviewers[0]
  let artifactCase = 0
  async function artifactFixture() {
    const runRoot = path.join(scratch, `artifacts-${artifactCase++}`)
    process.env.AGENTS_COOKBOOK_RUN_DIR = runRoot
    const api = (await AgentsCookbookReviewArtifacts(tool)).tool
    const args = { artifact_id: reviewer, summary: "CLEAN: bounded review.", content: "# Review\n\nCLEAN 🔎" }
    const receipt = JSON.parse(await api.review_artifact.execute(args, { agent: reviewer, sessionID: "ses_reviewer" }))
    const report = path.join(runRoot, "reviews", `${reviewer}.md`)
    const receiptPath = path.join(runRoot, "receipts", `${reviewer}.json`)
    return { api, runRoot, report, receiptPath, receipt, read: () => api.review_artifact_read.execute({ artifact_id: reviewer }, { agent: "ping-pong-plan" }) }
  }
  const valid = await artifactFixture()
  assert.equal(await valid.read(), "# Review\n\nCLEAN 🔎\n")
  pass("opencode_artifact_round_trip")
  await assert.rejects(() => AgentsCookbookReviewArtifacts(), /tool factory is missing/)
  pass("opencode_canonical_factory_requires_native_entrypoint")
  const changed = await artifactFixture()
  fs.writeFileSync(changed.report, "# Review\n\nCLEAR 🔎\n")
  await assert.rejects(changed.read, /does not match its receipt/)
  pass("opencode_artifact_same_length_tamper")
  const absent = await artifactFixture()
  fs.unlinkSync(absent.receiptPath)
  await assert.rejects(absent.read)
  pass("opencode_artifact_missing_receipt")
  for (const [field, value] of [["schema_version", 2], ["runtime", "pi"], ["run_id", "other-run"], ["reviewer", reviewers[1]], ["artifact_id", reviewers[1]], ["artifact", "reviews/other.md"], ["chars", "24"], ["sha256", "bad"], ["summary", " "]]) {
    const item = await artifactFixture()
    fs.writeFileSync(item.receiptPath, JSON.stringify({ ...item.receipt, [field]: value }))
    await assert.rejects(item.read)
    pass(`opencode_receipt_rejects_${field}`)
  }
  for (const directory of ["reviews", "receipts"]) {
    const item = await artifactFixture()
    const outside = path.join(scratch, `outside-${artifactCase}`)
    fs.renameSync(path.join(item.runRoot, directory), outside)
    fs.symlinkSync(outside, path.join(item.runRoot, directory))
    await assert.rejects(item.read, /escapes configured run root/)
    pass(`opencode_${directory}_directory_escape`)
  }
  for (const leaf of ["report", "receiptPath"]) {
    const item = await artifactFixture()
    const outside = path.join(scratch, `outside-leaf-${artifactCase}`)
    fs.renameSync(item[leaf], outside)
    fs.symlinkSync(outside, item[leaf])
    await assert.rejects(item.read, /escapes/)
    pass(`opencode_${leaf}_leaf_escape`)
  }
  console.log(`SUMMARY status=pass checks=${checks} native_runtime=false model_calls=0`)
} finally {
  fs.rmSync(scratch, { recursive: true, force: true })
}
