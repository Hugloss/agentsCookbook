#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const required = [
  ['plan-improver-model2', 'plan-improvement-scout'],
  ['plan-improver-model3', 'plan-improvement-scout'],
  ['plan-validation-designer', 'validation-gap-finder'],
  ['plan-coverage-reviewer', 'coverage-design-review'],
  ['plan-red-team-gate', 'red-team-leftover-gate'],
  ['plan-implementation-simulator', 'implementation-dry-run'],
  ['plan-fact-auditor', 'fact-grounding-auditor'],
  ['plan-contract-checker', 'plan-contract-guard'],
];
const requiredNames = new Set(required.map(([name]) => name));
const artifactMode = Boolean(process.env.AGENTS_COOKBOOK_RUN_DIR);

function usage() {
  process.stdout.write('Usage: scripts/check-pi-session.js [--scope latest-turn|session] [session-file-or-id]\n');
  process.stdout.write('Audits real Pi reviewer calls, first skill load, and live artifact writes when AGENTS_COOKBOOK_RUN_DIR is enabled.\n');
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

function readEntries(file) {
  return fs.readFileSync(file, 'utf8').split(/\r?\n/).filter(Boolean).map((line, index) => {
    try { return JSON.parse(line); }
    catch (error) { throw new Error(`${file}:${index + 1}: invalid JSON: ${error.message}`); }
  });
}

function sessionCwd(file) {
  try {
    const firstLine = fs.readFileSync(file, 'utf8').split(/\r?\n/, 1)[0];
    const header = JSON.parse(firstLine);
    return header && header.type === 'session' ? header.cwd : '';
  } catch { return ''; }
}

function resolveSession(target) {
  if (target && fs.existsSync(target)) return path.resolve(target);
  const agentDir = process.env.PI_CODING_AGENT_DIR ? path.resolve(process.env.PI_CODING_AGENT_DIR) : path.join(process.env.HOME || '', '.pi', 'agent');
  const files = walkJsonlFiles(path.join(agentDir, 'sessions'));
  let candidates = files;
  if (target) candidates = files.filter((file) => path.basename(file).includes(target) || fs.readFileSync(file, 'utf8').split(/\r?\n/, 1)[0].includes(target));
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

function activeBranch(entries) {
  const byId = new Map(entries.filter((entry) => entry.id).map((entry) => [entry.id, entry]));
  let current = [...entries].reverse().find((entry) => entry.id);
  const branchIds = new Set();
  while (current && current.id && !branchIds.has(current.id)) { branchIds.add(current.id); current = current.parentId ? byId.get(current.parentId) : undefined; }
  return entries.filter((entry) => !entry.id || branchIds.has(entry.id));
}

function scopedEntries(entries, scope) {
  const branch = activeBranch(entries);
  if (scope === 'session') return branch;
  let start = 0;
  for (let i = 0; i < branch.length; i += 1) if (branch[i].type === 'message' && branch[i].message && branch[i].message.role === 'user') start = i;
  return branch.slice(start);
}

function objectArgs(value) {
  if (value && typeof value === 'object') return value;
  if (typeof value !== 'string') return {};
  try { return JSON.parse(value); } catch { return {}; }
}

function childTools(result) {
  return result && result.details && Array.isArray(result.details.tools) ? result.details.tools : [];
}

function skillWasLoaded(result, skill) {
  const tools = childTools(result);
  if (tools.length === 0) return false;
  const first = tools[0];
  const args = objectArgs(first.args || first.arguments);
  if (first.name === 'skill') return Object.values(args).some((value) => String(value).includes(skill));
  if (first.name !== 'read') return false;
  const candidate = String(args.path || args.file_path || args.filePath || '');
  return candidate.replaceAll('\\', '/').endsWith(`/${skill}/SKILL.md`);
}

function artifactWasSaved(result, reviewer) {
  if (!artifactMode) return true;
  return childTools(result).some((entry) => {
    if (!entry || entry.name !== 'review_artifact') return false;
    const args = objectArgs(entry.args || entry.arguments);
    const status = String(entry.status || '').toLowerCase();
    return args.artifact_id === reviewer && (!status || status === 'done' || status === 'completed' || status === 'success');
  });
}

function audit(entries, scope) {
  const scoped = scopedEntries(entries, scope);
  const results = new Map();
  for (const entry of scoped) {
    if (entry.type !== 'message' || !entry.message) continue;
    if (entry.message.role === 'toolResult' && entry.message.toolCallId) results.set(entry.message.toolCallId, entry.message);
    if (Array.isArray(entry.message.content)) for (const part of entry.message.content) if (part.type === 'toolResult' && part.toolCallId) results.set(part.toolCallId, part);
  }

  const calls = [];
  for (const entry of scoped) {
    if (entry.type !== 'message' || !entry.message || !Array.isArray(entry.message.content)) continue;
    for (const part of entry.message.content) {
      if (part.type !== 'toolCall' || part.name !== 'subagent') continue;
      const args = objectArgs(part.arguments);
      calls.push({ id: part.id || '', agent: args.agent || '<missing agent>', result: results.get(part.id) });
    }
  }

  const rows = required.map(([name, skill]) => {
    const matching = calls.filter((call) => call.agent === name);
    const call = matching[0];
    const output = call && call.result && call.result.details && typeof call.result.details.output === 'string' ? call.result.details.output.trim() : '';
    const succeeded = Boolean(call && call.result && !call.result.isError && call.result.details && call.result.details.status === 'done' && output);
    return {
      name, skill, count: matching.length,
      invocation: matching.length === 0 ? 'missing' : matching.length === 1 ? (succeeded ? 'succeeded' : 'failed') : 'duplicate',
      skillLoaded: succeeded && skillWasLoaded(call.result, skill),
      artifactSaved: succeeded && artifactWasSaved(call.result, name),
    };
  });
  const unexpected = calls.filter((call) => !requiredNames.has(call.agent));
  const expectedOrder = required.map(([name]) => name);
  const orderPass = calls.length === expectedOrder.length && calls.every((call, index) => call.agent === expectedOrder[index]);
  const pass = rows.every((row) => row.invocation === 'succeeded' && row.skillLoaded && row.artifactSaved) && unexpected.length === 0 && orderPass;
  return { rows, calls, unexpected, orderPass, pass };
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  const file = resolveSession(options.target);
  const report = audit(readEntries(file), options.scope);

  process.stdout.write(`PI_SESSION=${file}\nSCOPE=${options.scope}\nARTIFACT_MODE=${artifactMode ? 'enabled' : 'disabled'}\n`);
  for (const row of report.rows) {
    process.stdout.write(`REVIEWER name=${row.name} invocation=${row.invocation} count=${row.count} skill=${row.skill} skill_loaded=${row.skillLoaded ? 'yes' : 'no'} artifact_saved=${artifactMode ? (row.artifactSaved ? 'yes' : 'no') : 'disabled'}\n`);
  }
  for (const call of report.unexpected) process.stdout.write(`UNEXPECTED_REVIEWER name=${call.agent}\n`);
  process.stdout.write(`ORDER status=${report.orderPass ? 'pass' : 'fail'} actual=${report.calls.map((call) => call.agent).join(',') || 'none'}\n`);
  process.stdout.write(`SUMMARY status=${report.pass ? 'pass' : 'fail'} required=${required.length} calls=${report.calls.length} unexpected=${report.unexpected.length} artifact_mode=${artifactMode ? 'enabled' : 'disabled'}\n`);
  if (!report.pass) process.exitCode = 1;
}

try { main(); }
catch (error) { process.stderr.write(`Error: ${error.message}\n`); process.exit(2); }
