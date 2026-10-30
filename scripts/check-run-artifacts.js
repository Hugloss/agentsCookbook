#!/usr/bin/env node
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const FULL_REVIEWERS = [
  'plan-improver-model2',
  'plan-improver-model3',
  'plan-validation-designer',
  'plan-coverage-reviewer',
  'plan-red-team-gate',
  'plan-implementation-simulator',
  'plan-fact-auditor',
  'code-performance-optimization-auditor',
  'plan-contract-checker',
];
const MAX_REPORT_CHARS = 65536;
const MAX_SUMMARY_CHARS = 1200;

function usage() {
  process.stdout.write(`Usage: scripts/check-run-artifacts.js --run-dir DIR [--reviewer NAME ...]\n\n`);
  process.stdout.write('Validate live artifact-backed reviewer reports and receipts.\n');
  process.stdout.write('Without --reviewer, requires exactly the nine mandatory full-flow reviewers.\n');
}

function parseArgs(argv) {
  const options = { runDir: '', reviewers: [], help: false };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--help' || arg === '-h') options.help = true;
    else if (arg === '--run-dir') options.runDir = argv[++i] || '';
    else if (arg === '--reviewer') options.reviewers.push(argv[++i] || '');
    else throw new Error(`Unknown option: ${arg}`);
  }
  if (!options.help && !options.runDir) throw new Error('--run-dir is required.');
  if (options.reviewers.some((value) => !value)) throw new Error('--reviewer requires a non-empty name.');
  if (options.reviewers.some((value) => !FULL_REVIEWERS.includes(value))) throw new Error('--reviewer must name a canonical cookbook reviewer.');
  if (new Set(options.reviewers).size !== options.reviewers.length) throw new Error('--reviewer must not be repeated.');
  return options;
}

function sha256(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function readJson(file) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); }
  catch (error) { throw new Error(`${file}: invalid receipt JSON: ${error.message}`); }
}

function listBaseNames(dir, suffix) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir, { withFileTypes: true })
    .filter((entry) => entry.name.endsWith(suffix))
    .map((entry) => entry.name.slice(0, -suffix.length))
    .sort();
}

function isWithin(parent, candidate) {
  const relative = path.relative(parent, candidate);
  return relative !== '' && relative !== '..' && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative);
}

function confinedDirectory(root, name) {
  const candidate = path.join(root, name);
  if (!fs.existsSync(candidate)) return candidate;
  const resolved = fs.realpathSync(candidate);
  if (!isWithin(root, resolved)) throw new Error(`${name} escapes configured run root.`);
  if (!fs.statSync(resolved).isDirectory()) throw new Error(`${name} is not a directory.`);
  return resolved;
}

function sameSet(actual, expected) {
  return actual.length === expected.length && actual.every((value, index) => value === expected[index]);
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

  const runDir = fs.realpathSync(path.resolve(options.runDir));
  if (!fs.statSync(runDir).isDirectory()) throw new Error('--run-dir is not a directory.');
  const reviewsDir = confinedDirectory(runDir, 'reviews');
  const receiptsDir = confinedDirectory(runDir, 'receipts');
  const expected = [...(options.reviewers.length ? options.reviewers : FULL_REVIEWERS)].sort();
  const reviewNames = listBaseNames(reviewsDir, '.md');
  const receiptNames = listBaseNames(receiptsDir, '.json');

  let failures = 0;
  function pass(name, detail = '') { process.stdout.write(`CHECK name=${name} status=pass${detail ? ` ${detail}` : ''}\n`); }
  function fail(name, detail = '') { failures += 1; process.stdout.write(`CHECK name=${name} status=fail${detail ? ` ${detail}` : ''}\n`); }

  if (sameSet(reviewNames, expected)) pass('review_file_set', `count=${reviewNames.length}`);
  else fail('review_file_set', `actual=${reviewNames.join(',') || 'none'} expected=${expected.join(',')}`);
  if (sameSet(receiptNames, expected)) pass('receipt_file_set', `count=${receiptNames.length}`);
  else fail('receipt_file_set', `actual=${receiptNames.join(',') || 'none'} expected=${expected.join(',')}`);

  for (const reviewer of expected) {
    const artifactFile = path.join(reviewsDir, `${reviewer}.md`);
    const receiptFile = path.join(receiptsDir, `${reviewer}.json`);
    if (!fs.existsSync(artifactFile) || !fs.existsSync(receiptFile)) {
      fail(`artifact_pair_${reviewer}`, 'missing_report_or_receipt');
      continue;
    }

    const artifactReal = fs.realpathSync(artifactFile);
    const receiptReal = fs.realpathSync(receiptFile);
    if (!isWithin(reviewsDir, artifactReal) || !fs.statSync(artifactReal).isFile()) {
      fail(`artifact_path_${reviewer}`, 'escapes_reviews_dir');
      continue;
    }
    if (!isWithin(receiptsDir, receiptReal) || !fs.statSync(receiptReal).isFile()) {
      fail(`receipt_path_${reviewer}`, 'escapes_receipts_dir');
      continue;
    }

    if (fs.statSync(artifactReal).size > (MAX_REPORT_CHARS + 1) * 4) {
      fail(`artifact_budget_${reviewer}`, `bytes_exceed_report_limit`);
      continue;
    }
    const body = fs.readFileSync(artifactReal, 'utf8');
    const receipt = readJson(receiptReal);
    const expectedHash = sha256(body);
    const identityOkay = receipt && typeof receipt === 'object' && !Array.isArray(receipt)
      && receipt.schema_version === 1
      && receipt.run_id === path.basename(runDir)
      && receipt.reviewer === reviewer
      && receipt.artifact_id === reviewer
      && receipt.artifact === `reviews/${reviewer}.md`;
    identityOkay ? pass(`receipt_identity_${reviewer}`) : fail(`receipt_identity_${reviewer}`, 'identity_mismatch');
    if (!identityOkay) continue;
    receipt.sha256 === expectedHash ? pass(`artifact_sha256_${reviewer}`) : fail(`artifact_sha256_${reviewer}`, 'hash_mismatch');
    Number.isInteger(receipt.chars) && receipt.chars === body.length ? pass(`artifact_chars_${reviewer}`, `chars=${body.length}`) : fail(`artifact_chars_${reviewer}`, `receipt=${receipt.chars} actual=${body.length}`);

    if (body.trim() && body.length <= MAX_REPORT_CHARS + 1) pass(`artifact_budget_${reviewer}`, `chars=${body.length}`);
    else fail(`artifact_budget_${reviewer}`, `chars=${body.length} max=${MAX_REPORT_CHARS + 1}`);

    const summary = typeof receipt.summary === 'string' ? receipt.summary : '';
    if (summary.trim() && summary.length <= MAX_SUMMARY_CHARS) pass(`summary_budget_${reviewer}`, `chars=${summary.length}`);
    else fail(`summary_budget_${reviewer}`, `chars=${summary.length} max=${MAX_SUMMARY_CHARS}`);

    if (['opencode', 'pi'].includes(receipt.runtime)) pass(`runtime_${reviewer}`, `runtime=${receipt.runtime}`);
    else fail(`runtime_${reviewer}`, `runtime=${String(receipt.runtime)}`);
  }

  const status = failures === 0 ? 'pass' : 'fail';
  process.stdout.write(`SUMMARY status=${status} expected_reviewers=${expected.length} failures=${failures} run_dir=${runDir}\n`);
  if (failures) process.exit(1);
}

try { main(); }
catch (error) {
  process.stderr.write(`Error: ${error.message}\n`);
  process.exit(2);
}
