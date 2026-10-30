#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { test } = require('node:test');
const { pathToFileURL } = require('node:url');

const sourceRoot = path.resolve(__dirname, '..');

function fixture(t, checkoutName = 'checkout') {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'cookbook-install-lifecycle-'));
  t.after(() => fs.rmSync(temp, { recursive: true, force: true }));
  const checkout = path.join(temp, checkoutName);
  fs.mkdirSync(checkout);
  for (const name of ['scripts', 'agents', 'skills', 'adapters', 'reviewers.json']) {
    fs.cpSync(path.join(sourceRoot, name), path.join(checkout, name), { recursive: true });
  }
  const destinations = { global: path.join(temp, 'opencode'), pi: path.join(temp, 'pi'), skills: path.join(temp, 'skills') };
  function run(script, extra = [], expected = 0) {
    const result = spawnSync('bash', [path.join(checkout, 'scripts', script),
      '--global-dir', destinations.global, '--pi-agent-dir', destinations.pi,
      '--shared-skill-dir', destinations.skills, ...extra], {
      cwd: checkout, encoding: 'utf8', timeout: 30000, maxBuffer: 4 * 1024 * 1024,
    });
    assert.ifError(result.error);
    if (expected === 0) assert.equal(result.status, 0, result.stdout + result.stderr);
    else assert.notEqual(result.status, 0, result.stdout + result.stderr);
    return result;
  }
  return { temp, checkout, destinations, run };
}

function isLink(file) {
  try { return fs.lstatSync(file).isSymbolicLink(); }
  catch (error) { if (error.code === 'ENOENT') return false; throw error; }
}

test('installation discovers every canonical skill from a checkout with spaces', (t) => {
  const f = fixture(t, 'checkout with spaces');
  f.run('link-opencode-local.sh');
  const skills = fs.readdirSync(path.join(f.checkout, 'skills')).filter((name) =>
    fs.existsSync(path.join(f.checkout, 'skills', name, 'SKILL.md')));
  assert.ok(skills.length > 0);
  for (const name of skills) {
    assert.equal(fs.realpathSync(path.join(f.destinations.skills, name)), path.join(f.checkout, 'skills', name));
  }
  f.run('unlink-opencode-local.sh');
  assert.equal(fs.existsSync(f.destinations.skills), false);
});

test('update reconciles removed skills and uninstall removes retired owned links only', (t) => {
  const f = fixture(t);
  f.run('link-opencode-local.sh');
  const removed = 'sensitive-data-masking';
  fs.rmSync(path.join(f.checkout, 'skills', removed), { recursive: true });
  const added = path.join(f.checkout, 'skills', 'new-install-example');
  fs.mkdirSync(added);
  fs.writeFileSync(path.join(added, 'SKILL.md'), '---\nname: new-install-example\ndescription: Example skill for installation discovery.\n---\n');
  const foreign = path.join(f.destinations.skills, 'foreign-skill');
  const alias = path.join(f.destinations.skills, 'custom-alias');
  const userFile = path.join(f.destinations.skills, 'user-notes');
  fs.symlinkSync(path.join(f.temp, 'another-checkout', 'skills', 'foreign-skill'), foreign);
  fs.symlinkSync(path.join(f.checkout, 'skills', removed), alias);
  fs.writeFileSync(userFile, 'preserve user content');

  f.run('link-opencode-local.sh', ['--dry-run']);
  assert.equal(isLink(path.join(f.destinations.skills, removed)), true);
  f.run('link-opencode-local.sh');
  assert.equal(isLink(path.join(f.destinations.skills, removed)), false);
  assert.equal(fs.realpathSync(path.join(f.destinations.skills, 'new-install-example')), added);

  // Retire another source after installation, without a reconciliation run.
  fs.rmSync(added, { recursive: true });
  const retiredAgent = path.join(f.destinations.global, 'agents', 'retired-example.md');
  fs.symlinkSync(path.join(f.checkout, 'agents', 'retired-example.md'), retiredAgent);
  f.run('unlink-opencode-local.sh', ['--dry-run']);
  assert.equal(isLink(retiredAgent), true);
  f.run('unlink-opencode-local.sh');
  assert.equal(isLink(retiredAgent), false);
  assert.equal(isLink(path.join(f.destinations.skills, 'new-install-example')), false);
  assert.equal(isLink(foreign), true);
  assert.equal(isLink(alias), true);
  assert.equal(fs.readFileSync(userFile, 'utf8'), 'preserve user content');
});

test('a missing required source is rejected before destination writes', (t) => {
  for (const source of ['agents/plan-contract-checker.md', 'reviewers.json']) {
    const f = fixture(t);
    fs.rmSync(path.join(f.checkout, source));
    f.run('link-opencode-local.sh', [], 1);
    for (const destination of Object.values(f.destinations)) assert.equal(fs.existsSync(destination), false);
  }
});

test('a malformed or inconsistent adapter reviewer catalog is rejected before writes', (t) => {
  for (const catalog of ['{', '["unknown-agent"]']) {
    const f = fixture(t);
    fs.writeFileSync(path.join(f.checkout, 'reviewers.json'), catalog);
    f.run('link-opencode-local.sh', [], 1);
    for (const destination of Object.values(f.destinations)) assert.equal(fs.existsSync(destination), false);
  }
});

test('installed OpenCode entry resolves the SDK from the host and canonical behavior from a spaced checkout', async (t) => {
  const f = fixture(t, 'checkout with spaces');
  f.run('link-opencode-local.sh');
  const entry = path.join(f.destinations.global, 'plugins', 'agents-cookbook-review-artifact.js');
  assert.equal(fs.lstatSync(entry).isFile(), true);
  const sdk = path.join(f.destinations.global, 'node_modules', '@opencode-ai', 'plugin');
  fs.mkdirSync(sdk, { recursive: true });
  fs.writeFileSync(path.join(sdk, 'package.json'), '{"type":"module","exports":"./index.js"}\n');
  fs.writeFileSync(path.join(sdk, 'index.js'), 'const schema={describe(){return this},optional(){return this}};export const tool=Object.assign(value=>value,{schema:{string:()=>schema}});\n');
  assert.equal(fs.existsSync(path.join(f.checkout, 'node_modules')), false);
  const previousRunDir = process.env.AGENTS_COOKBOOK_RUN_DIR;
  process.env.AGENTS_COOKBOOK_RUN_DIR = path.join(f.temp, 'run');
  try {
    const loaded = await import(pathToFileURL(entry).href);
    assert.deepEqual(Object.keys(loaded), ['AgentsCookbookReviewArtifacts']);
    const { tool } = await loaded.AgentsCookbookReviewArtifacts();
    const reviewer = 'plan-coverage-reviewer';
    await tool.review_artifact.execute({ artifact_id: reviewer, summary: 'Entry check.', content: '# Entry check' }, { agent: reviewer, sessionID: 'entry-test' });
    assert.equal(await tool.review_artifact_read.execute({ artifact_id: reviewer }, { agent: 'ping-pong-plan' }), '# Entry check\n');
  } finally {
    if (previousRunDir === undefined) delete process.env.AGENTS_COOKBOOK_RUN_DIR;
    else process.env.AGENTS_COOKBOOK_RUN_DIR = previousRunDir;
  }
});

test('modified OpenCode entries require backup for replacement and survive uninstall', (t) => {
  const f = fixture(t);
  f.run('link-opencode-local.sh');
  const entry = path.join(f.destinations.global, 'plugins', 'agents-cookbook-review-artifact.js');
  const canonical = fs.readFileSync(entry, 'utf8');
  const modified = `${canonical}// user change\n`;
  fs.writeFileSync(entry, modified);
  f.run('link-opencode-local.sh', [], 1);
  assert.equal(fs.readFileSync(entry, 'utf8'), modified);
  f.run('link-opencode-local.sh', ['--force']);
  assert.equal(fs.readFileSync(entry, 'utf8'), canonical);
  const backups = fs.readdirSync(path.dirname(entry)).filter(name => name.startsWith(`${path.basename(entry)}.agents-cookbook-backup-`));
  assert.equal(backups.length, 1);
  assert.equal(fs.readFileSync(path.join(path.dirname(entry), backups[0]), 'utf8'), modified);
  fs.writeFileSync(entry, modified);
  f.run('unlink-opencode-local.sh');
  assert.equal(fs.readFileSync(entry, 'utf8'), modified);
  assert.equal(fs.readFileSync(path.join(path.dirname(entry), backups[0]), 'utf8'), modified);
});
