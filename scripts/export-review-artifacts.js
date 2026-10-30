#!/usr/bin/env node
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { parsePiSession, collectPiTools, object } = require('./lib-pi-session');

function usage() {
  process.stdout.write(`Usage: scripts/export-review-artifacts.js --runtime opencode|pi --input FILE --out DIR [options]\n\n`);
  process.stdout.write('Materialize reviewer outputs from an existing runtime trace without granting reviewers write access.\n\n');
  process.stdout.write('Pi exports use the active branch. The output directory must be absent or empty.\n\n');
  process.stdout.write('Options:\n');
  process.stdout.write('  --run-id ID              Stable run identifier (default: derived from input bytes).\n');
  process.stdout.write('  --subject-id ID          Optional reviewed subject identifier.\n');
  process.stdout.write('  --subject-revision VALUE Optional reviewed subject revision.\n');
  process.stdout.write('  --subject-sha256 HEX     Optional reviewed subject SHA-256.\n');
  process.stdout.write('  --help                   Show this help.\n');
}

function parseArgs(argv) {
  const out = {
    runtime: '', input: '', outputDir: '', runId: '',
    subjectId: '', subjectRevision: '', subjectSha256: '', help: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--help' || arg === '-h') out.help = true;
    else if (arg === '--runtime') out.runtime = argv[++i] || '';
    else if (arg === '--input') out.input = argv[++i] || '';
    else if (arg === '--out') out.outputDir = argv[++i] || '';
    else if (arg === '--run-id') out.runId = argv[++i] || '';
    else if (arg === '--subject-id') out.subjectId = argv[++i] || '';
    else if (arg === '--subject-revision') out.subjectRevision = argv[++i] || '';
    else if (arg === '--subject-sha256') out.subjectSha256 = argv[++i] || '';
    else throw new Error(`Unknown option: ${arg}`);
  }
  if (out.help) return out;
  if (!['opencode', 'pi'].includes(out.runtime)) throw new Error('--runtime must be opencode or pi.');
  if (!out.input) throw new Error('--input is required.');
  if (!out.outputDir) throw new Error('--out is required.');
  return out;
}

function sha256(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function safeName(value) {
  const normalized = String(value || 'unknown')
    .normalize('NFKC')
    .replace(/[^A-Za-z0-9._-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 96);
  return normalized || 'unknown';
}

function normalizeOutput(value) {
  return typeof value === 'string' ? value.trim() : '';
}

function extractHeadings(markdown) {
  return markdown
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => /^#{1,4}\s+\S/.test(line))
    .slice(0, 12)
    .map((line) => line.replace(/^#{1,4}\s+/, '').slice(0, 160));
}

function firstSummaryLine(markdown) {
  for (const raw of markdown.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith('#') || line.startsWith('```')) continue;
    return line.slice(0, 240);
  }
  return '';
}

function piTextContent(result) {
  const content = result && result.message && Array.isArray(result.message.content)
    ? result.message.content
    : result && Array.isArray(result.content)
      ? result.content
      : [];
  return content
    .filter((part) => part && part.type === 'text' && typeof part.text === 'string')
    .map((part) => part.text)
    .join('\n')
    .trim();
}

function parsePi(raw) {
  const session = parsePiSession(raw, 'Pi export');
  const calls = collectPiTools(session.entries, 'Pi export').filter((call) => call.name === 'subagent').map((call) => {
    if (typeof call.args.agent !== 'string' || !call.args.agent) throw new Error('Pi export: subagent call is missing its reviewer identity.');
    const { result } = call;
    const details = result && object(result.details) ? result.details : {};
    if (result && details.agent !== call.args.agent) throw new Error('Pi export: subagent result reviewer identity does not match its call.');
    const output = normalizeOutput(details.output);
    const runtimeStatus = String(details.status || (result ? 'unknown' : 'missing-result'));
    let status = 'unknown';
    if (!result) status = 'missing';
    else if (result.isError === true || ['error', 'failed', 'cancelled', 'canceled', 'aborted'].includes(runtimeStatus)) status = 'failed';
    else if (['running', 'pending', 'queued'].includes(runtimeStatus)) status = 'incomplete';
    else if (runtimeStatus === 'done' && result.isError === false) status = output ? 'succeeded' : 'failed';
    return {
      reviewer: call.args.agent, runtimeStatus, status, output,
      error: status === 'failed' ? (piTextContent(result) || output || 'Reviewer returned no usable output.') : '',
      toolCallId: call.id,
    };
  });
  return { calls, sessionId: session.header.id, scope: 'active-branch' };
}

function parseOpenCode(raw) {
  const root = JSON.parse(raw);
  if (!object(root) || !object(root.info) || typeof root.info.id !== 'string' || !root.info.id || !Array.isArray(root.messages)) {
    throw new Error('OpenCode export: expected a native session info object and messages array.');
  }
  const calls = [];
  const messageIds = new Set();
  const partIds = new Set();
  for (const message of root.messages) {
    const info = message && message.info;
    if (!object(info) || typeof info.id !== 'string' || !info.id || messageIds.has(info.id)
        || info.sessionID !== root.info.id || !['user', 'assistant'].includes(info.role) || !Array.isArray(message.parts)) {
      throw new Error('OpenCode export: invalid or duplicate message identity.');
    }
    messageIds.add(info.id);
    const callIds = new Set();
    for (const part of message.parts) {
      if (!object(part) || typeof part.id !== 'string' || !part.id || partIds.has(part.id)
          || part.sessionID !== root.info.id || part.messageID !== info.id || typeof part.type !== 'string') {
        throw new Error('OpenCode export: invalid or duplicate part identity.');
      }
      partIds.add(part.id);
      if (part.type !== 'tool') continue;
      if (info.role !== 'assistant' || typeof part.callID !== 'string' || !part.callID || callIds.has(part.callID)) {
        throw new Error('OpenCode export: invalid or duplicate tool-call identity.');
      }
      callIds.add(part.callID);
      if (part.tool !== 'task') continue;
      const state = part.state;
      if (!object(state) || !object(state.input) || typeof state.input.subagent_type !== 'string' || !state.input.subagent_type) {
        throw new Error('OpenCode export: task is missing structured state or reviewer identity.');
      }
      const output = normalizeOutput(state.output);
      const runtimeStatus = typeof state.status === 'string' && state.status ? state.status : 'unknown';
      const wrapper = output.match(/^<task\b([^>]*)>[\s\S]*<\/task>$/);
      const taskState = wrapper && (wrapper[1].match(/\bstate=["']([^"']+)["']/) || [])[1];
      const nativeWrapper = output.match(/^<task id="[^"]+" state="([^"]+)">\s*(?:<summary>[\s\S]*?<\/summary>\s*)?<task_result>([\s\S]*)<\/task_result>\s*<\/task>$/);
      const resultEnvelope = output.match(/<task_result>([\s\S]*?)<\/task_result>\s*(?:<\/task>)?$/);
      const recognizableEnvelope = /^<task(?:\s|>)/.test(output) || /^<task_result>/.test(output) || /^task_id:/.test(output);
      let status = 'unknown';
      if (['error', 'failed', 'cancelled', 'canceled', 'aborted'].includes(runtimeStatus) || taskState === 'error') status = 'failed';
      else if (['running', 'pending'].includes(runtimeStatus) || (state.metadata && state.metadata.background === true) || taskState === 'running') status = 'incomplete';
      else if (runtimeStatus === 'completed') {
        if (!output || (resultEnvelope && !normalizeOutput(resultEnvelope[1]))) status = 'failed';
        else if (recognizableEnvelope && !resultEnvelope) status = 'unknown';
        else if (/^<task(?:\s|>)/.test(output) && !nativeWrapper) status = 'unknown';
        else if (wrapper && taskState !== 'completed') status = 'unknown';
        else status = 'succeeded';
      }
      calls.push({
        reviewer: state.input.subagent_type, runtimeStatus, status, output,
        error: status === 'failed' ? (normalizeOutput(state.error) || output || 'Reviewer returned no usable output.') : '',
        toolCallId: part.callID,
      });
    }
  }
  return { calls, sessionId: root.info.id, scope: 'session' };
}

function artifactBody(call) {
  if (call.status === 'succeeded' && call.output) return `${call.output.trim()}\n`;
  const reason = call.error || `Runtime status: ${call.runtimeStatus}`;
  return `# Reviewer Artifact Unavailable\n\nReviewer: \`${call.reviewer}\`\n\nStatus: \`${call.status}\`\n\n${reason.trim()}\n`;
}

function main() {
  let options;
  try { options = parseArgs(process.argv.slice(2)); }
  catch (error) {
    process.stderr.write(`Error: ${error.message}\n`);
    usage();
    process.exit(2);
  }
  if (options.help) { usage(); return; }

  const inputPath = path.resolve(options.input);
  const outputDir = path.resolve(options.outputDir);
  const source = fs.readFileSync(inputPath);
  const raw = source.toString('utf8');
  const parsed = options.runtime === 'pi' ? parsePi(raw) : parseOpenCode(raw);
  const { calls } = parsed;
  const sourceHash = sha256(source);
  const runId = options.runId || `run-${sourceHash.slice(0, 16)}`;
  const subject = {
    id: options.subjectId || null,
    revision: options.subjectRevision || null,
    sha256: options.subjectSha256 || null,
  };

  let existing;
  try { existing = fs.lstatSync(outputDir); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  if (existing && (!existing.isDirectory() || existing.isSymbolicLink() || fs.readdirSync(outputDir).length)) {
    throw new Error('--out must be an absent or empty directory; existing artifacts are not overwritten.');
  }

  const manifest = {
    schema_version: 1,
    run_id: runId,
    runtime: options.runtime,
    source_file: path.basename(inputPath),
    source_sha256: sourceHash,
    session_id: parsed.sessionId,
    scope: parsed.scope,
    subject,
    reviewers: [],
  };

  const files = [];
  calls.forEach((call, index) => {
    const sequence = index + 1;
    const prefix = String(sequence).padStart(2, '0');
    const reviewerSafe = safeName(call.reviewer);
    const artifactRel = `reviews/${prefix}-${reviewerSafe}.md`;
    const receiptRel = `receipts/${prefix}-${reviewerSafe}.json`;
    const body = artifactBody(call);
    const receipt = {
      schema_version: 1,
      run_id: runId,
      runtime: options.runtime,
      sequence,
      reviewer: call.reviewer,
      status: call.status,
      runtime_status: call.runtimeStatus,
      tool_call_id: call.toolCallId || null,
      source_sha256: sourceHash,
      session_id: parsed.sessionId,
      scope: parsed.scope,
      subject,
      artifact: artifactRel,
      output_sha256: sha256(body),
      output_chars: body.length,
      headings: extractHeadings(body),
      summary_hint: firstSummaryLine(body),
    };

    files.push([artifactRel, body], [receiptRel, `${JSON.stringify(receipt, null, 2)}\n`]);
    manifest.reviewers.push({
      sequence,
      reviewer: call.reviewer,
      status: call.status,
      artifact: artifactRel,
      receipt: receiptRel,
      output_sha256: receipt.output_sha256,
      output_chars: receipt.output_chars,
    });
  });

  manifest.counts = {
    total: manifest.reviewers.length,
    succeeded: manifest.reviewers.filter((item) => item.status === 'succeeded').length,
    failed: manifest.reviewers.filter((item) => item.status === 'failed').length,
    missing: manifest.reviewers.filter((item) => item.status === 'missing').length,
    incomplete: manifest.reviewers.filter((item) => item.status === 'incomplete').length,
    unknown: manifest.reviewers.filter((item) => item.status === 'unknown').length,
  };
  files.push(['manifest.json', `${JSON.stringify(manifest, null, 2)}\n`]);

  const parent = path.dirname(outputDir);
  fs.mkdirSync(parent, { recursive: true });
  const staging = fs.mkdtempSync(path.join(parent, '.cookbook-export-'));
  try {
    fs.mkdirSync(path.join(staging, 'reviews'));
    fs.mkdirSync(path.join(staging, 'receipts'));
    for (const [relative, content] of files) fs.writeFileSync(path.join(staging, relative), content, { encoding: 'utf8', flag: 'wx' });
    fs.renameSync(staging, outputDir);
  } finally {
    fs.rmSync(staging, { recursive: true, force: true });
  }

  process.stdout.write(`SUMMARY status=pass operation=export runtime=${options.runtime} run_id=${runId} reviewers=${manifest.counts.total} succeeded=${manifest.counts.succeeded} failed=${manifest.counts.failed} missing=${manifest.counts.missing} incomplete=${manifest.counts.incomplete} unknown=${manifest.counts.unknown} out=${outputDir}\n`);
}

try {
  main();
} catch (error) {
  process.stderr.write(`Error: ${error.message}\n`);
  process.exit(1);
}
