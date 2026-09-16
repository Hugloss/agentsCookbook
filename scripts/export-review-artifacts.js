#!/usr/bin/env node
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

function usage() {
  process.stdout.write(`Usage: scripts/export-review-artifacts.js --runtime opencode|pi --input FILE --out DIR [options]\n\n`);
  process.stdout.write('Materialize reviewer outputs from an existing runtime trace without granting reviewers write access.\n\n');
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

function parseMaybeJson(value) {
  if (value && typeof value === 'object') return value;
  if (typeof value !== 'string') return {};
  try { return JSON.parse(value); } catch { return {}; }
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
  const entries = raw.split(/\r?\n/).filter(Boolean).map((line, index) => {
    try { return JSON.parse(line); }
    catch (error) { throw new Error(`Invalid Pi JSONL at line ${index + 1}: ${error.message}`); }
  });

  const results = new Map();
  for (const entry of entries) {
    if (entry.type !== 'message' || !entry.message) continue;
    if (entry.message.role === 'toolResult' && entry.message.toolCallId) {
      results.set(entry.message.toolCallId, entry.message);
    }
    if (Array.isArray(entry.message.content)) {
      for (const part of entry.message.content) {
        if (part && part.type === 'toolResult' && part.toolCallId) results.set(part.toolCallId, part);
      }
    }
  }

  const calls = [];
  for (const entry of entries) {
    if (entry.type !== 'message' || !entry.message || !Array.isArray(entry.message.content)) continue;
    for (const part of entry.message.content) {
      if (!part || part.type !== 'toolCall' || part.name !== 'subagent') continue;
      const args = parseMaybeJson(part.arguments);
      const result = results.get(part.id);
      const details = result && result.details && typeof result.details === 'object' ? result.details : {};
      const output = normalizeOutput(details.output) || piTextContent(result);
      const errorText = result && result.isError ? (piTextContent(result) || normalizeOutput(details.output)) : '';
      const failed = Boolean(result && (result.isError || ['error', 'failed'].includes(String(details.status || '').toLowerCase())));
      calls.push({
        reviewer: String(args.agent || '<missing agent>'),
        runtimeStatus: String(details.status || (result ? 'unknown' : 'missing-result')),
        status: !result ? 'missing' : failed ? 'failed' : output ? 'succeeded' : 'failed',
        output,
        error: errorText,
        toolCallId: part.id || '',
      });
    }
  }
  return calls;
}

function readJsonObject(raw, label) {
  const start = raw.indexOf('{');
  if (start < 0) throw new Error(`${label}: missing JSON object.`);
  return JSON.parse(raw.slice(start));
}

function parseOpenCode(raw) {
  const root = readJsonObject(raw, 'OpenCode export');
  const calls = [];

  function visit(value) {
    if (!value || typeof value !== 'object') return;
    if (value.tool === 'task') {
      const state = value.state && typeof value.state === 'object' ? value.state : {};
      const input = parseMaybeJson(state.input ?? value.input ?? {});
      const output = normalizeOutput(state.output ?? value.output ?? '');
      const runtimeStatus = String(state.status || value.status || 'unknown');
      const failed = ['error', 'failed'].includes(runtimeStatus.toLowerCase());
      calls.push({
        reviewer: String(input.subagent_type || '<missing subagent_type>'),
        runtimeStatus,
        status: failed ? 'failed' : output ? 'succeeded' : 'failed',
        output,
        error: failed ? output : '',
        toolCallId: String(value.id || value.callID || value.callId || ''),
      });
    }
    if (Array.isArray(value)) {
      for (const child of value) visit(child);
    } else {
      for (const child of Object.values(value)) visit(child);
    }
  }

  visit(root);
  return calls;
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
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
  const raw = fs.readFileSync(inputPath, 'utf8');
  const calls = options.runtime === 'pi' ? parsePi(raw) : parseOpenCode(raw);
  const runId = options.runId || `run-${sha256(raw).slice(0, 16)}`;
  const subject = {
    id: options.subjectId || null,
    revision: options.subjectRevision || null,
    sha256: options.subjectSha256 || null,
  };

  const reviewsDir = path.join(outputDir, 'reviews');
  const receiptsDir = path.join(outputDir, 'receipts');
  ensureDir(reviewsDir);
  ensureDir(receiptsDir);

  const manifest = {
    schema_version: 1,
    run_id: runId,
    runtime: options.runtime,
    source_file: path.basename(inputPath),
    subject,
    reviewers: [],
  };

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
      subject,
      artifact: artifactRel,
      output_sha256: sha256(body),
      output_chars: body.length,
      headings: extractHeadings(body),
      summary_hint: firstSummaryLine(body),
    };

    fs.writeFileSync(path.join(outputDir, artifactRel), body, 'utf8');
    fs.writeFileSync(path.join(outputDir, receiptRel), `${JSON.stringify(receipt, null, 2)}\n`, 'utf8');
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
  };
  fs.writeFileSync(path.join(outputDir, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');

  process.stdout.write(`SUMMARY status=pass runtime=${options.runtime} run_id=${runId} reviewers=${manifest.counts.total} succeeded=${manifest.counts.succeeded} failed=${manifest.counts.failed} out=${outputDir}\n`);
}

try {
  main();
} catch (error) {
  process.stderr.write(`Error: ${error.message}\n`);
  process.exit(1);
}
