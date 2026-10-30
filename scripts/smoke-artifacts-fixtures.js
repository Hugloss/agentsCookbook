'use strict';

const assert = require('assert/strict');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const [scratch, repo] = process.argv.slice(2);
const reviewers = JSON.parse(fs.readFileSync(path.join(repo, 'reviewers.json'), 'utf8'));
const skills = ['plan-gap-scout', 'alternative-route-challenge', 'validation-gap-finder', 'coverage-design-review', 'red-team-leftover-gate', 'implementation-dry-run', 'fact-grounding-auditor', 'code-performance-optimization-audit', 'plan-contract-guard'];
const env = { ...process.env };
delete env.AGENTS_COOKBOOK_RUN_DIR;
delete env.NODE_OPTIONS;
let sequence = 0;
const fresh = (label) => path.join(scratch, `${++sequence}-${label}`);
const hash = (value) => crypto.createHash('sha256').update(value).digest('hex');
const json = (file, value) => fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);
const jsonl = (file, entries) => fs.writeFileSync(file, `${entries.map(JSON.stringify).join('\n')}\n`);
const readJson = (file) => JSON.parse(fs.readFileSync(file, 'utf8'));
function run(script, args, extraEnv = {}) {
  const result = spawnSync(process.execPath, [path.join(repo, 'scripts', script), ...args], { encoding: 'utf8', env: { ...env, ...extraEnv } });
  if (result.error) throw result.error;
  assert.equal(result.signal, null, result.stderr);
  return result;
}
function accepts(result) { assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`); }
function rejects(result, pattern) {
  assert.notEqual(result.status, 0, `unexpected success:\n${result.stdout}`);
  if (pattern) assert.match(`${result.stdout}\n${result.stderr}`, pattern);
}
function check(name, action) {
  try { action(); process.stdout.write(`SMOKE name=${name} status=pass\n`); }
  catch (error) { process.stderr.write(`SMOKE name=${name} status=fail\n${error.stack}\n`); process.exit(1); }
}
function receipt(root, reviewer, body, runtime = 'pi') {
  return { schema_version: 1, runtime, run_id: path.basename(root), reviewer, artifact_id: reviewer, artifact: `reviews/${reviewer}.md`, sha256: hash(body), chars: body.length, summary: `${reviewer}: material finding.` };
}
function store(names = reviewers, runtime = 'pi') {
  const root = fresh('run');
  fs.mkdirSync(path.join(root, 'reviews'), { recursive: true });
  fs.mkdirSync(path.join(root, 'receipts'));
  for (const reviewer of names) {
    const body = `# ${reviewer}\n\nMaterial finding.\n`;
    fs.writeFileSync(path.join(root, 'reviews', `${reviewer}.md`), body);
    json(path.join(root, 'receipts', `${reviewer}.json`), receipt(root, reviewer, body, runtime));
  }
  return root;
}
const storeCheck = (root, single = false) => run('check-run-artifacts.js', ['--run-dir', root, ...(single ? ['--reviewer', reviewers[0]] : [])]);

check('run_artifacts_complete_and_selected', () => {
  accepts(storeCheck(store(reviewers, 'opencode')));
  const root = store([reviewers[0]]);
  accepts(storeCheck(root, true));
  rejects(storeCheck(root), /review_file_set.*status=fail/);
});
check('run_artifacts_receipt_and_content_integrity', () => {
  const changes = [
    (value) => { value.sha256 = '0'.repeat(64); },
    (value) => { value.chars += 1; },
    (value) => { value.reviewer = reviewers[1]; },
    (value) => { value.run_id = 'another-run'; },
    (value) => { value.artifact = '../outside.md'; },
    (value) => { value.runtime = 'unknown'; },
    (value) => { value.summary = '   '; },
  ];
  for (const change of changes) {
    const root = store([reviewers[0]]), file = path.join(root, 'receipts', `${reviewers[0]}.json`), value = readJson(file);
    change(value); json(file, value); rejects(storeCheck(root, true));
  }
  for (const body of ['', 'x'.repeat(65538)]) {
    const root = store([reviewers[0]]);
    fs.writeFileSync(path.join(root, 'reviews', `${reviewers[0]}.md`), body);
    json(path.join(root, 'receipts', `${reviewers[0]}.json`), receipt(root, reviewers[0], body));
    rejects(storeCheck(root, true), /artifact_budget.*status=fail/);
  }
});
check('run_artifacts_directory_and_leaf_confinement', () => {
  for (const dir of ['reviews', 'receipts']) {
    const root = store([reviewers[0]]), outside = fresh('outside');
    fs.renameSync(path.join(root, dir), outside);
    fs.symlinkSync(outside, path.join(root, dir), 'dir');
    rejects(storeCheck(root, true), /escapes configured run root/);
  }
  for (const [dir, extension] of [['reviews', 'md'], ['receipts', 'json']]) {
    const root = store([reviewers[0]]), file = path.join(root, dir, `${reviewers[0]}.${extension}`), outside = fresh('outside-file');
    fs.renameSync(file, outside); fs.symlinkSync(outside, file);
    rejects(storeCheck(root, true), /escapes_(reviews|receipts)_dir/);
    fs.unlinkSync(outside);
    rejects(storeCheck(root, true), /missing_report_or_receipt/);
  }
  const root = store([reviewers[0]]);
  fs.renameSync(path.join(root, 'reviews'), path.join(root, 'contained-reviews'));
  fs.symlinkSync(path.join(root, 'contained-reviews'), path.join(root, 'reviews'), 'dir');
  accepts(storeCheck(root, true));
});

function messages(id, cwd = '/fixture') {
  return [{ type: 'session', version: 3, id, cwd }, { type: 'message', id: 'user', parentId: null, message: { role: 'user', content: [{ type: 'text', text: 'review' }] } }];
}
function appendTool(entries, tool, index) {
  const parent = entries[entries.length - 1].id;
  entries.push({ type: 'message', id: `assistant-${index}`, parentId: parent, message: { role: 'assistant', content: [{ type: 'toolCall', id: tool.id, name: tool.name, arguments: structuredClone(tool.args) }] } });
  if (tool.result !== null) entries.push({ type: 'message', id: `result-${index}`, parentId: `assistant-${index}`, message: { role: 'toolResult', toolCallId: tool.id, toolName: tool.name, isError: false, content: [{ type: 'text', text: 'native tool result' }], ...tool.result } });
}
function piProof() {
  const runDir = store(), parent = messages('parent-session'), children = [];
  const parentFile = fresh('parent.jsonl');
  reviewers.forEach((reviewer, index) => {
    const childFile = fresh('child.jsonl'), child = messages(`child-${index}`);
    child[0].parentSession = parentFile;
    const body = fs.readFileSync(path.join(runDir, 'reviews', `${reviewer}.md`), 'utf8');
    const saved = readJson(path.join(runDir, 'receipts', `${reviewer}.json`));
    const trace = [
      { id: `read-${index}`, name: 'read', args: { path: `/skills/${skills[index]}/SKILL.md` }, status: 'done' },
      { id: `save-${index}`, name: 'review_artifact', args: { artifact_id: reviewer, summary: saved.summary, content: body.trim() }, status: 'done' },
    ];
    appendTool(child, { ...trace[0], result: { content: [{ type: 'text', text: '# Skill\n\nEvidence requirements.' }] } }, 0);
    appendTool(child, { ...trace[1], result: { content: [{ type: 'text', text: JSON.stringify(saved) }], details: saved } }, 1);
    children.push({ file: childFile, entries: child });
    appendTool(parent, { id: `review-${index}`, name: 'subagent', args: { agent: reviewer, task: 'review' }, result: { details: { agent: reviewer, status: 'done', output: JSON.stringify(saved), tools: trace, session: { requested: 'fork', effective: 'fork', file: childFile } } } }, index);
  });
  return { runDir, parent, parentFile, children, write() { jsonl(parentFile, parent); for (const child of children) jsonl(child.file, child.entries); } };
}
const firstParentResult = (proof) => proof.parent[3].message;
const piCheck = (proof) => { proof.write(); return run('check-pi-session.js', ['--scope', 'session', proof.parentFile], { AGENTS_COOKBOOK_RUN_DIR: proof.runDir }); };
check('pi_session_native_child_outcomes', () => {
  accepts(piCheck(piProof()));
  const proof = piProof();
  Object.assign(firstParentResult(proof).details.tools[0].args, { offset: 1, limit: 100 });
  Object.assign(proof.children[0].entries[2].message.content[0].arguments, { offset: 1, limit: 100 });
  accepts(piCheck(proof));
});
check('pi_session_parent_trace_is_not_success_proof', () => {
  const proof = piProof();
  for (const entry of proof.parent) if (entry.message && entry.message.details) delete entry.message.details.session;
  const result = piCheck(proof);
  rejects(result, /skill_attempted=yes skill_completed=yes skill_loaded=unknown/);
  assert.match(result.stdout, /child_result_evidence_unavailable/);
});
check('pi_session_failed_and_unproved_child_results', () => {
  for (const target of ['read', 'save', 'read-unknown', 'save-mismatch', 'wrong-agent']) {
    const proof = piProof();
    if (target === 'read') proof.children[0].entries[3].message.isError = true;
    if (target === 'save') proof.children[0].entries[5].message.isError = true;
    if (target === 'read-unknown') delete proof.children[0].entries[3].message.isError;
    if (target === 'save-mismatch') proof.children[0].entries[5].message.details.sha256 = '0'.repeat(64);
    if (target === 'wrong-agent') firstParentResult(proof).details.agent = reviewers[1];
    rejects(piCheck(proof));
  }
});
check('pi_session_partial_skill_read_is_not_full_loading', () => {
  for (const mode of ['offset', 'limit', 'truncated']) {
    const proof = piProof(), trace = firstParentResult(proof).details.tools[0], child = proof.children[0].entries;
    if (mode === 'offset') { trace.args.offset = 2; child[2].message.content[0].arguments.offset = 2; }
    if (mode === 'limit') {
      trace.args.limit = 1; child[2].message.content[0].arguments.limit = 1;
      child[3].message.content = [{ type: 'text', text: '# Skill\n\n[44 more lines in file. Use offset=2 to continue.]' }];
    }
    if (mode === 'truncated') child[3].message.details = { truncation: { truncated: true } };
    rejects(piCheck(proof), /skill_loaded=unknown skill_evidence=skill_read_incomplete/);
  }
});
check('pi_session_first_read_failure_is_not_hidden_by_retry', () => {
  const proof = piProof(), child = proof.children[0].entries, first = firstParentResult(proof).details.tools[0];
  child[3].message.isError = true;
  const retry = { ...first, id: 'retry-read' };
  firstParentResult(proof).details.tools.push(retry);
  appendTool(child, { ...retry, result: { content: [{ type: 'text', text: 'Skill successfully read on retry.' }] } }, 2);
  rejects(piCheck(proof), /skill_loaded=no skill_evidence=child_tool_failed/);
});
check('pi_session_requires_selected_child_identity_and_boundary', () => {
  for (const mode of ['wrong-args', 'inactive-branch', 'unsafe-tool', 'untraced-tool', 'missing-save', 'invalid-tool-name']) {
    const proof = piProof(), trace = firstParentResult(proof).details.tools, child = proof.children[0].entries;
    if (mode === 'wrong-args') child[2].message.content[0].arguments.path = '/different/SKILL.md';
    if (mode === 'inactive-branch') child.push({ type: 'message', id: 'other-branch', parentId: 'user', message: { role: 'user', content: [{ type: 'text', text: 'Another branch.' }] } });
    if (mode === 'unsafe-tool' || mode === 'untraced-tool') {
      const tool = { id: 'unsafe', name: 'bash', args: { command: 'unused fixture command' }, status: 'done' };
      if (mode === 'unsafe-tool') trace.push(tool);
      appendTool(child, { ...tool, result: {} }, 2);
    }
    if (mode === 'missing-save') { trace.pop(); child.splice(4); }
    if (mode === 'invalid-tool-name') trace.push({ id: 'nameless', args: {}, status: 'done' });
    rejects(piCheck(proof));
  }
});

function piExport(specs) {
  const entries = messages('export-pi');
  specs.forEach((spec, index) => appendTool(entries, { id: spec.id || `call-${index}`, name: 'subagent', args: { agent: spec.reviewer || reviewers[index], task: 'review' }, result: spec.missing ? null : { details: { agent: spec.reviewer || reviewers[index], status: spec.status || 'done', output: spec.output === undefined ? `# Review ${index}\n\nMaterial finding ${index}.` : spec.output }, ...(spec.result || {}) } }, index));
  return entries;
}
function ocExport(specs) {
  return { info: { id: 'session-oc' }, messages: specs.map((spec, index) => ({ info: { id: `message-${index}`, sessionID: 'session-oc', role: 'assistant' }, parts: [{ id: `part-${index}`, messageID: `message-${index}`, sessionID: 'session-oc', type: 'tool', tool: 'task', callID: spec.id || `call-${index}`, state: { status: spec.status || 'completed', input: { subagent_type: spec.reviewer || reviewers[index] }, output: spec.output === undefined ? `# Review ${index}\n\nMaterial finding.` : spec.output, ...(spec.state || {}) } }] })) };
}
function exportRun(runtime, value, output = fresh('export'), extraEnv = {}) {
  const input = fresh(runtime === 'pi' ? 'trace.jsonl' : 'export.json');
  if (typeof value === 'string') fs.writeFileSync(input, value);
  else if (runtime === 'pi') jsonl(input, value);
  else json(input, value);
  return { input, output, result: run('export-review-artifacts.js', ['--runtime', runtime, '--input', input, '--out', output], extraEnv) };
}
function verifyExport(attempt) {
  accepts(attempt.result);
  const manifest = readJson(path.join(attempt.output, 'manifest.json'));
  assert.equal(manifest.source_sha256, hash(fs.readFileSync(attempt.input)));
  for (const entry of manifest.reviewers) {
    const body = fs.readFileSync(path.join(attempt.output, entry.artifact), 'utf8');
    const saved = readJson(path.join(attempt.output, entry.receipt));
    assert.equal(saved.output_sha256, hash(body)); assert.equal(saved.output_chars, body.length);
    assert.equal(entry.output_sha256, saved.output_sha256); assert.equal(entry.output_chars, saved.output_chars);
    assert.equal(saved.reviewer, entry.reviewer); assert.equal(saved.status, entry.status);
    assert.equal(saved.source_sha256, manifest.source_sha256); assert.equal(saved.session_id, manifest.session_id);
  }
  return manifest;
}
check('exporter_preserves_terminal_and_unknown_states', () => {
  const pi = piExport([{ status: 'done' }, { status: 'running' }, { status: 'future-state' }, { status: 'error' }, { missing: true }, { output: '' }, { status: 'cancelled' }]);
  assert.deepEqual(verifyExport(exportRun('pi', pi)).reviewers.map((entry) => entry.status), ['succeeded', 'incomplete', 'unknown', 'failed', 'missing', 'failed', 'failed']);
  const oc = ocExport([{ status: 'completed' }, { status: 'running' }, { status: 'future-state' }, { status: 'error' }, { output: '' }]);
  assert.deepEqual(verifyExport(exportRun('opencode', oc)).reviewers.map((entry) => entry.status), ['succeeded', 'incomplete', 'unknown', 'failed', 'failed']);
  const unknown = piExport([{}]); delete unknown[3].message.isError;
  assert.equal(verifyExport(exportRun('pi', unknown)).reviewers[0].status, 'unknown');
});
check('exporter_background_launch_is_not_completion', () => {
  const oc = ocExport([
    { state: { metadata: { background: true } } },
    { output: '<task id="child" state="running"><task_result>Partial.</task_result></task>' },
    { output: '<task id="child" state="error"><task_error>Failed.</task_error></task>' },
    { output: '<task id="child" state="completed"><task_result> </task_result></task>' },
    { output: '<task id="child" state="completed"><task_result># Review\n\nFinding.</task_result></task>' },
    { output: '<task id="child" state="running"><task_result>Truncated' },
    { output: 'task_id: child\n\n<task_result> </task_result>' },
    { output: 'task_id: child\n\n<task_result># Review\n\nFinding.</task_result>' },
    { output: '<task state="completed"><task_result>Missing child identity.</task_result></task>' },
  ]);
  assert.deepEqual(verifyExport(exportRun('opencode', oc)).reviewers.map((entry) => entry.status), ['incomplete', 'incomplete', 'failed', 'failed', 'succeeded', 'unknown', 'failed', 'succeeded', 'unknown']);
});
check('exporter_uses_active_branch_and_sequential_call_identity', () => {
  const entries = piExport([{ reviewer: reviewers[0] }]);
  entries.push({ type: 'message', id: 'selected-user', parentId: 'user', message: { role: 'user', content: [{ type: 'text', text: 'New selected branch.' }] } });
  appendTool(entries, { id: 'selected-call', name: 'subagent', args: { agent: reviewers[1], task: 'review' }, result: { details: { agent: reviewers[1], status: 'done', output: '# Selected review' } } }, 'selected');
  const manifest = verifyExport(exportRun('pi', entries));
  assert.equal(manifest.scope, 'active-branch'); assert.equal(manifest.counts.total, 1); assert.equal(manifest.reviewers[0].reviewer, reviewers[1]);
  const reused = verifyExport(exportRun('pi', piExport([{ id: 'provider-reuses-id' }, { id: 'provider-reuses-id' }])));
  assert.equal(reused.counts.succeeded, 2);
  assert.notEqual(reused.reviewers[0].output_sha256, reused.reviewers[1].output_sha256);
});
check('exporter_ignores_nested_task_shaped_data', () => {
  const value = ocExport([{}]);
  value.extra = { tool: 'task', state: { status: 'completed', input: { subagent_type: 'invented-reviewer' }, output: 'fake' } };
  value.messages[0].parts.push({ id: 'text-part', messageID: 'message-0', sessionID: 'session-oc', type: 'text', text: JSON.stringify(value.extra) });
  assert.equal(verifyExport(exportRun('opencode', value)).counts.total, 1);
});
check('exporter_rejects_malformed_evidence_before_output', () => {
  const malformed = [
    ['pi', '{invalid'], ['pi', '{}\n'], ['opencode', '{invalid'], ['opencode', { messages: [] }],
  ];
  const dangling = piExport([{}]); dangling[2].parentId = 'missing'; malformed.push(['pi', dangling]);
  const wrongAgent = piExport([{}]); wrongAgent[3].message.details.agent = reviewers[1]; malformed.push(['pi', wrongAgent]);
  const wrongResult = piExport([{}]); wrongResult[3].message.toolName = 'read'; malformed.push(['pi', wrongResult]);
  const duplicate = piExport([{}]); duplicate[3].id = duplicate[2].id; malformed.push(['pi', duplicate]);
  const wrongSession = ocExport([{}]); wrongSession.messages[0].parts[0].sessionID = 'foreign'; malformed.push(['opencode', wrongSession]);
  for (const [runtime, value] of malformed) {
    const attempt = exportRun(runtime, value); rejects(attempt.result); assert.equal(fs.existsSync(attempt.output), false);
  }
});
check('exporter_preserves_existing_outputs_and_outside_files', () => {
  const original = exportRun('pi', piExport([{}])); verifyExport(original);
  const before = fs.readFileSync(path.join(original.output, 'manifest.json'));
  rejects(exportRun('pi', piExport([{ output: '# Replacement' }]), original.output).result, /existing artifacts are not overwritten/);
  assert.deepEqual(fs.readFileSync(path.join(original.output, 'manifest.json')), before);
  const linked = fresh('linked-output'); fs.symlinkSync(original.output, linked, 'dir');
  rejects(exportRun('pi', piExport([{}]), linked).result); assert.deepEqual(fs.readFileSync(path.join(original.output, 'manifest.json')), before);
  const empty = fresh('empty-output'); fs.mkdirSync(empty); verifyExport(exportRun('pi', piExport([{}]), empty));
});
check('exporter_write_failure_does_not_publish_partial_run', () => {
  const preload = fresh('fault.cjs');
  fs.writeFileSync(preload, "const fs=require('fs'),path=require('path'),original=fs.writeFileSync;fs.writeFileSync=function(file,...args){if(String(file).includes('.cookbook-export-')&&String(file).includes(path.sep+'receipts'+path.sep)){const error=new Error('injected write failure');error.code='ENOSPC';throw error;}return original.call(this,file,...args);};\n");
  const attempt = exportRun('pi', piExport([{}]), fresh('unpublished'), { NODE_OPTIONS: `--require=${preload}` });
  rejects(attempt.result, /injected write failure/);
  assert.equal(fs.existsSync(attempt.output), false);
  assert.equal(fs.readdirSync(scratch).some((name) => name.startsWith('.cookbook-export-')), false);
});
process.stdout.write('SUMMARY status=pass\n');
