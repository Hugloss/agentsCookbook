#!/usr/bin/env node
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { pathToFileURL } = require('url');

const repoRoot = path.resolve(__dirname, '..');
const expectedReviewers = JSON.parse(fs.readFileSync(path.join(repoRoot, 'reviewers.json'), 'utf8'));
const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'cookbook-opencode-boundary-'));
const originalCwd = process.cwd();

async function main() {
  if (expectedReviewers.length !== 9 || new Set(expectedReviewers).size !== 9) throw new Error('invalid reviewer catalog');
  const adapterDir = path.join(scratch, 'adapters', 'opencode');
  const pluginDir = path.join(adapterDir, 'node_modules', '@opencode-ai', 'plugin');
  const foreignCwd = path.join(scratch, 'target-repo');
  fs.mkdirSync(pluginDir, { recursive: true });
  fs.mkdirSync(foreignCwd);
  fs.copyFileSync(path.join(repoRoot, 'reviewers.json'), path.join(scratch, 'reviewers.json'));
  fs.copyFileSync(path.join(repoRoot, 'adapters', 'opencode', 'review-artifact.js'), path.join(adapterDir, 'review-artifact.js'));
  fs.writeFileSync(path.join(pluginDir, 'package.json'), '{"type":"module","exports":"./index.js"}\n');
  fs.writeFileSync(path.join(pluginDir, 'index.js'), 'const schema = { describe() { return this }, optional() { return this } }; export const tool = Object.assign(value => value, { schema: { string: () => schema } });\n');
  fs.writeFileSync(path.join(foreignCwd, 'reviewers.json'), '["unknown-agent"]\n');

  process.chdir(foreignCwd);
  process.env.AGENTS_COOKBOOK_RUN_DIR = path.join(scratch, 'run');
  const adapter = await import(pathToFileURL(path.join(adapterDir, 'review-artifact.js')).href);
  const registered = await adapter.AgentsCookbookReviewArtifacts();
  const write = registered.tool.review_artifact.execute;
  const read = registered.tool.review_artifact_read.execute;
  const reviewer = expectedReviewers[0];
  const args = { artifact_id: reviewer, summary: 'review complete', content: '# Review' };

  await expectRejection(() => write({ ...args, artifact_id: 'unknown-agent' }, { agent: 'unknown-agent' }), 'unknown reviewer artifact_id');
  await expectRejection(() => write(args, { agent: 'unknown-agent' }), 'review_artifact is reviewer-only');
  const receipt = JSON.parse(await write(args, { agent: reviewer, sessionID: 'session-1' }));
  if (receipt.reviewer !== reviewer || receipt.artifact_id !== reviewer) throw new Error('known reviewer write failed');
  await expectRejection(() => read({ artifact_id: reviewer }, { agent: 'unknown-agent' }), 'review_artifact_read is primary-only');
  const body = await read({ artifact_id: reviewer }, { agent: 'ping-pong-plan' });
  if (body !== '# Review\n') throw new Error('primary artifact read failed');
  process.stdout.write('CHECK name=opencode_reviewer_runtime_boundary status=pass reviewers=9 foreign_cwd_ignored=true role_bound=true\n');
}

async function expectRejection(action, fragment) {
  try { await action(); } catch (error) {
    if (String(error.message || error).includes(fragment)) return;
    throw error;
  }
  throw new Error(`expected rejection: ${fragment}`);
}

main().catch((error) => {
  process.stderr.write(`CHECK name=opencode_reviewer_runtime_boundary status=fail error=${JSON.stringify(String(error.message || error))}\n`);
  process.exitCode = 1;
}).finally(() => {
  process.chdir(originalCwd);
  fs.rmSync(scratch, { recursive: true, force: true });
});
