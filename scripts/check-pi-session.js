#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { isDeepStrictEqual } = require('util');
const { parsePiSession, collectPiTools, toolArguments, object } = require('./lib-pi-session');

const required = [
  ['plan-improver-model2', 'plan-gap-scout'],
  ['plan-improver-model3', 'alternative-route-challenge'],
  ['plan-validation-designer', 'validation-gap-finder'],
  ['plan-coverage-reviewer', 'coverage-design-review'],
  ['plan-red-team-gate', 'red-team-leftover-gate'],
  ['plan-implementation-simulator', 'implementation-dry-run'],
  ['plan-fact-auditor', 'fact-grounding-auditor'],
  ['code-performance-optimization-auditor', 'code-performance-optimization-audit'],
  ['plan-contract-checker', 'plan-contract-guard'],
];
const requiredNames = new Set(required.map(([name]) => name));
const artifactMode = Boolean(process.env.AGENTS_COOKBOOK_RUN_DIR);
const allowedReviewerTools = new Set(['read', 'grep', 'find', 'ls', ...(artifactMode ? ['review_artifact'] : [])]);

function usage() {
  process.stdout.write('Usage: scripts/check-pi-session.js [--scope latest-turn|session] [session-file-or-id]\n');
  process.stdout.write('Audits native Pi reviewer calls, successful skill loading, finite child tool use, and artifact writes.\n');
  process.stdout.write('A completed child-tool trace alone is insufficient: successful outcomes require linked native child-session results.\n');
}

function parseArgs(argv) {
  let scope = 'latest-turn';
  let target = '';
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '-h' || arg === '--help') { usage(); process.exit(0); }
    if (arg === '--scope') { i += 1; scope = argv[i] || ''; continue; }
    if (arg.startsWith('--')) throw new Error(`Unknown option: ${arg}`);
    if (target) throw new Error('Only one session file or ID may be supplied.');
    target = arg;
  }
  if (!['latest-turn', 'session'].includes(scope)) throw new Error(`Invalid --scope value: ${scope}`);
  return { scope, target };
}

function walkJsonlFiles(root) {
  const files = [];
  if (!fs.existsSync(root)) return files;
  const pending = [root];
  while (pending.length > 0) {
    const current = pending.pop();
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) pending.push(full);
      else if (entry.isFile() && entry.name.endsWith('.jsonl')) files.push(full);
    }
  }
  return files;
}

function readSession(file) {
  return parsePiSession(fs.readFileSync(file, 'utf8'), file);
}

function sessionCwd(file) {
  try {
    const firstLine = fs.readFileSync(file, 'utf8').split(/\r?\n/, 1)[0];
    const header = JSON.parse(firstLine);
    return header && header.type === 'session' ? header.cwd : '';
  } catch { return ''; }
}

function sessionId(file) {
  try {
    const header = JSON.parse(fs.readFileSync(file, 'utf8').split(/\r?\n/, 1)[0]);
    return header && header.type === 'session' && typeof header.id === 'string' ? header.id : '';
  } catch { return ''; }
}

function resolveSession(target) {
  if (target && fs.existsSync(target)) return path.resolve(target);
  const agentDir = process.env.PI_CODING_AGENT_DIR ? path.resolve(process.env.PI_CODING_AGENT_DIR) : path.join(process.env.HOME || '', '.pi', 'agent');
  const files = walkJsonlFiles(path.join(agentDir, 'sessions'));
  let candidates = files;
  if (target) {
    const exact = files.filter((file) => sessionId(file) === target);
    candidates = exact.length ? exact : files.filter((file) => sessionId(file).startsWith(target));
    if (candidates.length > 1) throw new Error(`Pi session ID is ambiguous: ${target}; supply the exact session file.`);
  }
  else {
    const cwd = fs.realpathSync(process.cwd());
    candidates = files.filter((file) => {
      const candidate = sessionCwd(file); if (!candidate) return false;
      try { return fs.realpathSync(candidate) === cwd; } catch { return path.resolve(candidate) === cwd; }
    });
  }
  candidates.sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
  if (candidates.length === 0) throw new Error(target ? `Pi session not found: ${target}` : 'No Pi session found for the current directory.');
  return candidates[0];
}

function scopedEntries(entries, scope) {
  if (scope === 'session') return entries;
  let start = 0;
  for (let i = 0; i < entries.length; i += 1) if (entries[i].type === 'message' && entries[i].message.role === 'user') start = i;
  return entries.slice(start);
}

function childTools(result) {
  return result && result.details && Array.isArray(result.details.tools) ? result.details.tools : [];
}

function traceArgs(entry) {
  try { return toolArguments(entry && (entry.args || entry.arguments), 'child tool trace'); }
  catch { return {}; }
}

function childEvidence(result, cache, parentFile) {
  const sessionInfo = result && result.details && result.details.session;
  const file = sessionInfo && sessionInfo.file;
  if (typeof file !== 'string' || !file) return { reason: 'child_result_evidence_unavailable' };
  if (!path.isAbsolute(file)) return { reason: 'child_session_path_not_absolute' };
  if (sessionInfo.effective !== 'fork') return { reason: 'child_session_link_not_supported' };
  if (!cache.has(file)) {
    try {
      const session = readSession(file);
      if (typeof session.header.parentSession !== 'string'
          || fs.realpathSync(session.header.parentSession) !== fs.realpathSync(parentFile)) {
        cache.set(file, { reason: 'child_session_parent_mismatch' });
      } else {
        // The native one-task print child appends its task as a user message.
        // Forked history precedes this boundary; every new tool must be present.
        cache.set(file, { calls: collectPiTools(scopedEntries(session.entries, 'latest-turn'), file) });
      }
    } catch (error) { cache.set(file, { reason: 'child_session_invalid_or_unavailable', detail: error.message }); }
  }
  const evidence = cache.get(file);
  if (!evidence.calls) return evidence;
  const trace = childTools(result);
  const complete = trace.length > 0 && trace.length === evidence.calls.length && trace.every((entry, index) => object(entry)
    && typeof entry.id === 'string' && entry.id && evidence.calls[index].id === entry.id && evidence.calls[index].name === entry.name
    && isDeepStrictEqual(evidence.calls[index].args, traceArgs(entry)));
  if (!complete) return { reason: 'child_tool_sequence_incomplete_or_mismatched' };
  return { matched: new Map(trace.map((entry, index) => [entry, evidence.calls[index]])) };
}

function toolOutcome(entry, evidence) {
  if (!object(entry)) return { status: 'unknown', reason: 'invalid_tool_trace' };
  if (entry.isError === true || ['error', 'failed', 'cancelled', 'aborted'].includes(entry.status)) {
    return { status: 'failed', reason: 'child_tool_failed' };
  }
  // pi-open-agents currently writes status=done even for failed native tools.
  // Match the selected child's actual tool result before asserting success.
  if (!evidence.matched) return { status: 'unknown', reason: entry.status === 'done' ? evidence.reason : 'child_tool_not_completed', detail: evidence.detail };
  const call = evidence.matched.get(entry);
  if (!call) return { status: 'unknown', reason: 'child_tool_identity_or_arguments_mismatch' };
  if (!call.result) return { status: 'unknown', reason: 'child_tool_result_missing' };
  if (call.result.isError === true) return { status: 'failed', reason: 'child_tool_failed' };
  if (call.result.isError !== false) return { status: 'unknown', reason: 'child_tool_outcome_missing' };
  return { status: 'succeeded', reason: 'native_child_tool_result', result: call.result };
}

function skillEvidence(result, skill, evidence) {
  const first = childTools(result)[0];
  const args = traceArgs(first);
  const candidate = String(args.path || args.file_path || args.filePath || '');
  const attempted = Boolean(first && first.name === 'read' && candidate.replaceAll('\\', '/').endsWith(`/${skill}/SKILL.md`));
  if (!attempted) return { status: 'failed', reason: 'required_skill_not_first_tool', attempted: false, completed: false };
  const outcome = toolOutcome(first, evidence);
  const completed = first.status === 'done' || outcome.status === 'succeeded' || outcome.status === 'failed';
  if (outcome.status === 'succeeded') {
    const text = Array.isArray(outcome.result.content) ? outcome.result.content
      .filter((part) => part && part.type === 'text' && typeof part.text === 'string').map((part) => part.text).join('\n') : '';
    const truncation = outcome.result.details && outcome.result.details.truncation;
    if (!text.trim()) {
      outcome.status = 'unknown';
      outcome.reason = 'skill_read_content_unavailable';
    } else if (Number(args.offset || 1) > 1 || (truncation && (truncation.truncated || truncation.firstLineExceedsLimit))
        || /\[\d+ more lines in file\. Use offset=\d+ to continue\.\]\s*$/.test(text)) {
      outcome.status = 'unknown';
      outcome.reason = 'skill_read_incomplete';
    }
  }
  return { ...outcome, attempted, completed };
}

function artifactEvidence(result, reviewer, evidence) {
  if (!artifactMode) return { status: 'disabled', reason: 'artifact_mode_disabled' };
  const saves = childTools(result).filter((entry) => entry && entry.name === 'review_artifact' && traceArgs(entry).artifact_id === reviewer);
  if (saves.length === 0) return { status: 'failed', reason: 'artifact_call_missing' };
  const outcomes = saves.map((entry) => {
    const outcome = toolOutcome(entry, evidence);
    if (outcome.status !== 'succeeded') return outcome;
    const args = traceArgs(entry);
    const body = `${String(args.content || '').trim()}\n`;
    const receipt = outcome.result.details;
    if (!object(receipt) || receipt.schema_version !== 1 || receipt.runtime !== 'pi'
        || receipt.reviewer !== reviewer || receipt.artifact_id !== reviewer || receipt.artifact !== `reviews/${reviewer}.md`
        || receipt.sha256 !== crypto.createHash('sha256').update(body).digest('hex') || receipt.chars !== body.length
        || receipt.summary !== String(args.summary || '').trim()) {
      return { status: 'failed', reason: 'artifact_result_receipt_mismatch' };
    }
    return outcome;
  });
  return outcomes.find((outcome) => outcome.status === 'succeeded')
    || outcomes.find((outcome) => outcome.status === 'unknown') || outcomes[0];
}

function invocationOutcome(call) {
  if (!call || !call.result) return 'missing';
  const { result } = call;
  if (result.isError === true || (result.details && ['error', 'failed', 'cancelled', 'aborted'].includes(result.details.status))) return 'failed';
  if (!object(result.details) || result.details.agent !== call.agent) return 'unknown';
  if (result.details.status !== 'done') return ['running', 'pending'].includes(result.details.status) ? 'incomplete' : 'unknown';
  if (result.isError !== false) return 'unknown';
  return typeof result.details.output === 'string' && result.details.output.trim() ? 'succeeded' : 'failed';
}

function audit(entries, scope, label) {
  const scoped = scopedEntries(entries, scope);
  const calls = collectPiTools(scoped, label).filter((call) => call.name === 'subagent')
    .map((call) => ({ ...call, agent: typeof call.args.agent === 'string' && call.args.agent ? call.args.agent : '<missing agent>' }));
  const cache = new Map();

  const rows = required.map(([name, skill]) => {
    const matching = calls.filter((call) => call.agent === name);
    const call = matching[0];
    const invocation = matching.length > 1 ? 'duplicate' : invocationOutcome(call);
    const succeeded = invocation === 'succeeded';
    const tools = call ? childTools(call.result) : [];
    const unexpectedTools = tools.map((entry) => object(entry) && typeof entry.name === 'string' && entry.name ? entry.name : '<invalid-tool-trace>')
      .filter((name) => !allowedReviewerTools.has(name));
    const evidence = succeeded ? childEvidence(call.result, cache, label) : {};
    return {
      name, skill, count: matching.length,
      invocation,
      skillEvidence: succeeded ? skillEvidence(call.result, skill, evidence) : { status: 'unknown', reason: 'reviewer_not_successful', attempted: false, completed: false },
      artifactEvidence: succeeded ? artifactEvidence(call.result, name, evidence) : { status: 'unknown', reason: 'reviewer_not_successful' },
      unexpectedTools,
      toolBoundary: unexpectedTools.length > 0 ? 'fail' : succeeded && evidence.matched ? 'pass' : 'unknown',
    };
  });
  const unexpected = calls.filter((call) => !requiredNames.has(call.agent));
  const expectedOrder = required.map(([name]) => name);
  const orderPass = calls.length === expectedOrder.length && calls.every((call, index) => call.agent === expectedOrder[index]);
  const pass = rows.every((row) => row.invocation === 'succeeded' && row.skillEvidence.status === 'succeeded'
    && (!artifactMode || row.artifactEvidence.status === 'succeeded') && row.toolBoundary === 'pass') && unexpected.length === 0 && orderPass;
  const violation = rows.some((row) => ['failed', 'duplicate'].includes(row.invocation) || row.skillEvidence.status === 'failed'
    || (artifactMode && row.artifactEvidence.status === 'failed') || row.toolBoundary === 'fail')
    || unexpected.length > 0 || (!orderPass && calls.length === required.length);
  return { rows, calls, unexpected, orderPass, pass, status: pass ? 'pass' : violation ? 'fail' : 'incomplete' };
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  const file = resolveSession(options.target);
  const report = audit(readSession(file).entries, options.scope, file);

  process.stdout.write(`PI_SESSION=${file}\nSCOPE=${options.scope}\nARTIFACT_MODE=${artifactMode ? 'enabled' : 'disabled'}\n`);
  for (const row of report.rows) {
    const loaded = row.skillEvidence.status === 'succeeded' ? 'yes' : row.skillEvidence.status === 'unknown' ? 'unknown' : 'no';
    const saved = !artifactMode ? 'disabled' : row.artifactEvidence.status === 'succeeded' ? 'yes' : row.artifactEvidence.status === 'unknown' ? 'unknown' : 'no';
    process.stdout.write(`REVIEWER name=${row.name} invocation=${row.invocation} count=${row.count} skill=${row.skill} skill_attempted=${row.skillEvidence.attempted ? 'yes' : 'no'} skill_completed=${row.skillEvidence.completed ? 'yes' : 'no'} skill_loaded=${loaded} skill_evidence=${row.skillEvidence.reason} artifact_saved=${saved} artifact_evidence=${row.artifactEvidence.reason} tool_boundary=${row.toolBoundary} unexpected_tools=${row.unexpectedTools.join(',') || 'none'}\n`);
    if (row.skillEvidence.detail) process.stdout.write(`EVIDENCE reviewer=${row.name} detail=${JSON.stringify(row.skillEvidence.detail)}\n`);
  }
  for (const call of report.unexpected) process.stdout.write(`UNEXPECTED_REVIEWER name=${call.agent}\n`);
  process.stdout.write(`ORDER status=${report.orderPass ? 'pass' : 'fail'} actual=${report.calls.map((call) => call.agent).join(',') || 'none'}\n`);
  process.stdout.write(`SUMMARY status=${report.status} required=${required.length} calls=${report.calls.length} unexpected=${report.unexpected.length} artifact_mode=${artifactMode ? 'enabled' : 'disabled'}\n`);
  if (!report.pass) process.exitCode = 1;
}

try { main(); }
catch (error) { process.stderr.write(`Error: ${error.message}\n`); process.exit(2); }
