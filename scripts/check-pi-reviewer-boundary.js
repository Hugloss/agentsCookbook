#!/usr/bin/env node
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const assert = require('assert/strict');
const { pathToFileURL } = require('url');

const repoRoot = path.resolve(__dirname, '..');
const reviewers = JSON.parse(fs.readFileSync(path.join(repoRoot, 'reviewers.json'), 'utf8'));
const corePath = path.join(repoRoot, 'adapters', 'pi', 'reviewer-tool-boundary.js');
const adapterPath = path.join(repoRoot, 'adapters', 'pi', 'review-artifact.js');

const expectedReviewers = reviewers;
const expectedBaseTools = ['read', 'grep', 'find', 'ls'];

function same(actual, expected) {
  return JSON.stringify(actual) === JSON.stringify(expected);
}

function fail(message) {
  process.stderr.write(`CHECK name=pi_reviewer_runtime_boundary status=fail ${message}\n`);
  process.exit(1);
}

async function main() {
  if (expectedReviewers.length !== 9 || new Set(expectedReviewers).size !== 9) fail('invalid_reviewer_catalog');
  const core = await import(pathToFileURL(corePath).href);

  if (!same(core.PI_REVIEWER_AGENTS, expectedReviewers)) fail(`reviewers=${JSON.stringify(core.PI_REVIEWER_AGENTS)}`);
  if (!same(core.PI_REVIEWER_BASE_TOOLS, expectedBaseTools)) fail(`base_tools=${JSON.stringify(core.PI_REVIEWER_BASE_TOOLS)}`);
  if (!same(core.reviewerAllowedTools(), expectedBaseTools)) fail('normal_mode_tool_boundary_mismatch');
  if (!same(core.reviewerAllowedTools({ artifactEnabled: true }), [...expectedBaseTools, 'review_artifact'])) fail('artifact_mode_tool_boundary_mismatch');

  for (const denied of ['bash', 'powershell', 'edit', 'write', 'subagent', 'task', 'review_artifact_read']) {
    if (core.reviewerToolAllowed(denied, { artifactEnabled: true })) fail(`dangerous_tool_allowed=${denied}`);
  }
  if (core.reviewerToolAllowed('review_artifact')) fail('artifact_write_allowed_without_artifact_mode');
  if (!core.reviewerToolAllowed('review_artifact', { artifactEnabled: true })) fail('artifact_write_missing_in_artifact_mode');

  for (const reviewer of expectedReviewers) {
    const env = { PI_OPEN_AGENTS_DEPTH: '1', PI_OPEN_AGENTS_NAME: reviewer };
    if (core.activeReviewerName(env) !== reviewer) fail(`reviewer_identity_rejected=${reviewer}`);
  }
  if (core.activeReviewerName({ PI_OPEN_AGENTS_DEPTH: '0', PI_OPEN_AGENTS_NAME: expectedReviewers[0] })) fail('primary_process_misclassified_as_reviewer_child');
  if (core.activeReviewerName({ PI_OPEN_AGENTS_DEPTH: '1', PI_OPEN_AGENTS_NAME: 'unknown-agent' })) fail('unknown_agent_misclassified_as_reviewer');

  const foreignCwd = fs.mkdtempSync(path.join(os.tmpdir(), 'cookbook-reviewer-boundary-'));
  const originalCwd = process.cwd();
  try {
    fs.writeFileSync(path.join(foreignCwd, 'reviewers.json'), '["unknown-agent"]\n');
    process.chdir(foreignCwd);
    const foreignCore = await import(`${pathToFileURL(corePath).href}?foreign-cwd`);
    if (!same(foreignCore.PI_REVIEWER_AGENTS, expectedReviewers)) fail('foreign_working_directory_changed_reviewer_authority');
  } finally {
    process.chdir(originalCwd);
    fs.rmSync(foreignCwd, { recursive: true, force: true });
  }

  await exerciseAdapter();
  process.stdout.write('CHECK name=pi_reviewer_runtime_boundary status=pass evidence=adapter_with_lifecycle_stub reviewers=9 normal_tools=4 artifact_tools=5 role_separated_artifacts=true receipt_integrity=true session_start=true defense_in_depth=true\n');
}

async function exerciseAdapter() {
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'cookbook-pi-adapter-'));
  const adapterDir = path.join(scratch, 'adapters', 'pi');
  const typeboxDir = path.join(adapterDir, 'node_modules', 'typebox');
  const originalCwd = process.cwd();
  const envKeys = ['PI_OPEN_AGENTS_DEPTH', 'PI_OPEN_AGENTS_NAME', 'AGENTS_COOKBOOK_RUN_DIR'];
  const savedEnv = Object.fromEntries(envKeys.map((key) => [key, process.env[key]]));
  try {
    fs.mkdirSync(typeboxDir, { recursive: true });
    fs.copyFileSync(path.join(repoRoot, 'reviewers.json'), path.join(scratch, 'reviewers.json'));
    fs.copyFileSync(corePath, path.join(adapterDir, 'reviewer-tool-boundary.js'));
    fs.copyFileSync(adapterPath, path.join(adapterDir, 'review-artifact.js'));
    fs.writeFileSync(path.join(adapterDir, 'package.json'), '{"type":"module"}\n');
    fs.writeFileSync(path.join(typeboxDir, 'package.json'), '{"type":"module","exports":"./index.js"}\n');
    // Schema construction is a test double. The adapter and its storage code
    // execute unchanged; native SDK loading has a separate optional check.
    fs.writeFileSync(path.join(typeboxDir, 'index.js'), 'export const Type = { Object: value => value, String: value => value, Optional: value => value };\n');
    const foreign = path.join(scratch, 'foreign');
    fs.mkdirSync(foreign);
    fs.writeFileSync(path.join(foreign, 'reviewers.json'), '["unknown-agent"]\n');
    process.chdir(foreign);
    const register = (await import(pathToFileURL(path.join(adapterDir, 'review-artifact.js')).href)).default;

    function load(name, artifactEnabled) {
      process.env.PI_OPEN_AGENTS_DEPTH = name ? '1' : '0';
      process.env.PI_OPEN_AGENTS_NAME = name || '';
      if (artifactEnabled) process.env.AGENTS_COOKBOOK_RUN_DIR = path.join(scratch, 'run');
      else delete process.env.AGENTS_COOKBOOK_RUN_DIR;
      let bound = false;
      let active = [];
      const handlers = new Map();
      const tools = new Map();
      register({
        registerTool(tool) { tools.set(tool.name, tool); },
        on(event, handler) {
          if (!handlers.has(event)) handlers.set(event, []);
          handlers.get(event).push(handler);
        },
        setActiveTools(names) {
          if (!bound) throw new Error('Extension runtime not initialized. Action methods cannot be called during extension loading.');
          active = [...names];
        },
      });
      assert.deepEqual(active, [], 'factory must only register, not call bound runtime actions');
      bound = true;
      return {
        tools,
        get active() { return active; },
        replaceActive(names) { active = [...names]; },
        async emit(event, data = {}) {
          let result;
          for (const handler of handlers.get(event) || []) result = await handler({ type: event, ...data }, {});
          return result;
        },
      };
    }

    for (const name of expectedReviewers) {
      for (const artifactEnabled of [false, true]) {
        const host = load(name, artifactEnabled);
        assert.deepEqual([...host.tools.keys()], artifactEnabled ? ['review_artifact'] : []);
        const allowed = [...expectedBaseTools, ...(artifactEnabled ? ['review_artifact'] : [])];
        await host.emit('session_start', { reason: 'new' });
        assert.deepEqual(host.active, allowed);
        host.replaceActive(['read', 'bash', 'write']);
        await host.emit('session_start', { reason: 'reload' });
        assert.deepEqual(host.active, allowed);
        for (const toolName of allowed) assert.equal(await host.emit('tool_call', { toolName }), undefined);
        for (const toolName of ['bash', 'edit', 'write', 'subagent', 'task', 'review_artifact_read', 'unknown']) {
          assert.equal((await host.emit('tool_call', { toolName })).block, true);
        }
      }
    }

    const reviewer = expectedReviewers[0];
    const child = load(reviewer, true);
    const writer = child.tools.get('review_artifact').execute;
    const args = { artifact_id: reviewer, summary: 'One material finding.', content: '# Review\n\nOne finding.' };
    await assert.rejects(() => writer('bad', { ...args, artifact_id: 'unknown-agent' }), /unknown reviewer artifact_id/);
    await assert.rejects(() => writer('wrong', { ...args, artifact_id: expectedReviewers[1] }), /must equal current reviewer/);
    const written = await writer('write', args);
    assert.equal(written.details.reviewer, reviewer);
    await assert.rejects(() => writer('repeat', args), /already exists/);

    const primary = load('', true);
    assert.deepEqual([...primary.tools.keys()], ['review_artifact_read']);
    await primary.emit('session_start');
    assert.deepEqual(primary.active, [], 'primary authority stays with its native agent');
    const read = () => primary.tools.get('review_artifact_read').execute('read', { artifact_id: reviewer });
    assert.equal((await read()).content[0].text, `${args.content}\n`);
    const reportPath = path.join(scratch, 'run', 'reviews', `${reviewer}.md`);
    const receiptPath = path.join(scratch, 'run', 'receipts', `${reviewer}.json`);
    const receiptText = fs.readFileSync(receiptPath, 'utf8');
    fs.writeFileSync(reportPath, 'Tampered report.\n');
    await assert.rejects(read, /does not match its receipt/);
    fs.writeFileSync(reportPath, `${args.content}\n`);
    for (const patch of [{ runtime: 'opencode' }, { run_id: 'different-run' }, { reviewer: expectedReviewers[1] }, { chars: 1 }, { summary: ' ' }]) {
      fs.writeFileSync(receiptPath, JSON.stringify({ ...JSON.parse(receiptText), ...patch }));
      await assert.rejects(read);
    }
    fs.unlinkSync(receiptPath);
    await assert.rejects(read, /ENOENT/);
    const externalReceipt = path.join(scratch, 'external-receipt.json');
    fs.writeFileSync(externalReceipt, receiptText);
    fs.symlinkSync(externalReceipt, receiptPath);
    await assert.rejects(read, /receipt escapes/);
    fs.unlinkSync(receiptPath);
    fs.writeFileSync(receiptPath, receiptText);
    fs.unlinkSync(reportPath);
    const externalReport = path.join(scratch, 'external-report.md');
    fs.writeFileSync(externalReport, `${args.content}\n`);
    fs.symlinkSync(externalReport, reportPath);
    await assert.rejects(read, /artifact escapes/);

    assert.deepEqual([...load('', false).tools.keys()], []);
  } finally {
    process.chdir(originalCwd);
    for (const [key, value] of Object.entries(savedEnv)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    fs.rmSync(scratch, { recursive: true, force: true });
  }
}

main().catch((error) => {
  fail(`error=${JSON.stringify(error && error.message ? error.message : String(error))}`);
});
