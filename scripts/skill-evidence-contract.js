'use strict';

// A model's nonempty explanation is not proof that a repository file supports it.
// This verifies a bounded, exact file/line/quote triple for fixture-positive cases.
const fs = require('fs');
const path = require('path');

function qualifyEvidence({ verdict, evidence, location, quote, fixture, expected }) {
  if (!evidence || typeof evidence !== 'string' || !evidence.trim()) {
    return { state: 'UNQUALIFIED', reason: 'missing-evidence-statement' };
  }
  if (!fixture) {
    return { state: 'SCENARIO_ONLY', reason: 'no-repository-evidence-fixture' };
  }
  if (expected !== 'FINDING' || verdict !== 'FINDING') {
    return { state: 'NOT_APPLICABLE', reason: 'no-positive-fixture-finding' };
  }
  if (typeof location !== 'string' || !location.trim() || typeof quote !== 'string' || !quote.trim()) {
    return { state: 'UNQUALIFIED', reason: 'missing-file-line-quote' };
  }
  const match = location.match(/^([^\r\n:]+):(\d{1,7})$/);
  if (!match || match[1].includes('\\') || match[1].startsWith('/') || match[1].includes('\0')) {
    return { state: 'UNQUALIFIED', reason: 'invalid-file-line-locator' };
  }
  const line = Number(match[2]);
  if (!Number.isSafeInteger(line) || line < 1) {
    return { state: 'UNQUALIFIED', reason: 'invalid-line-number' };
  }
  let root;
  let real;
  let stat;
  try {
    root = fs.realpathSync(fixture);
    if (!fs.statSync(root).isDirectory()) {
      return { state: 'UNQUALIFIED', reason: 'fixture-not-directory' };
    }
    const target = path.resolve(root, match[1]);
    if (!target.startsWith(root + path.sep)) {
      return { state: 'UNQUALIFIED', reason: 'path-escapes-fixture' };
    }
    real = fs.realpathSync(target);
    if (!real.startsWith(root + path.sep)) {
      return { state: 'UNQUALIFIED', reason: 'symlink-escapes-fixture' };
    }
    stat = fs.statSync(real);
    if (!stat.isFile() || stat.size > 1024 * 1024) {
      return { state: 'UNQUALIFIED', reason: 'invalid-or-oversized-evidence-file' };
    }
  } catch (_) {
    return { state: 'UNQUALIFIED', reason: 'evidence-file-unavailable' };
  }
  const lines = fs.readFileSync(real, 'utf8').split(/\r?\n/);
  if (line > lines.length) {
    return { state: 'UNQUALIFIED', reason: 'line-out-of-range' };
  }
  const exact = quote.trim();
  if (exact.length > 240 || exact.length < 3 || !lines[line - 1].includes(exact)) {
    return { state: 'UNQUALIFIED', reason: 'quote-not-on-cited-line' };
  }
  // Source citation is located, not semantically adjudicated. Gold oracle still
  // owns whether the evidence proves the particular invariant.
  return { state: 'LOCATED_NOT_ADJUDICATED', reason: null, location: match[1] + ':' + line };
}

module.exports = { qualifyEvidence };
