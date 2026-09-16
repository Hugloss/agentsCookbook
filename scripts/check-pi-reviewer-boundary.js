#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');

const repoRoot = path.resolve(__dirname, '..');
const corePath = path.join(repoRoot, 'adapters', 'pi', 'reviewer-tool-boundary.js');
const adapterPath = path.join(repoRoot, 'adapters', 'pi', 'review-artifact.js');

const expectedReviewers = [
  'plan-improver-model2',
  'plan-improver-model3',
  'plan-validation-designer',
  'plan-coverage-reviewer',
  'plan-red-team-gate',
  'plan-implementation-simulator',
  'plan-fact-auditor',
  'plan-contract-checker',
  'code-performance-optimization-auditor',
];
const expectedBaseTools = ['read', 'grep', 'find', 'ls'];

function same(actual, expected) {
  return JSON.stringify(actual) === JSON.stringify(expected);
}

function fail(message) {
  process.stderr.write(`CHECK name=pi_reviewer_runtime_boundary status=fail ${message}\n`);
  process.exit(1);
}

async function main() {
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

  const adapter = fs.readFileSync(adapterPath, 'utf8');
  const requiredFragments = [
    'if (artifactEnabled && reviewerName)',
    'if (artifactEnabled && !reviewerName)',
    'review_artifact is available only to a delegated reviewer child',
    'unknown reviewer artifact_id',
    'pi.setActiveTools(allowedTools)',
    'pi.on("session_start"',
    'pi.on("tool_call"',
    'reviewerToolAllowed(event.toolName',
    'artifact_id must equal current reviewer name',
  ];
  for (const fragment of requiredFragments) {
    if (!adapter.includes(fragment)) fail(`adapter_missing=${JSON.stringify(fragment)}`);
  }

  process.stdout.write('CHECK name=pi_reviewer_runtime_boundary status=pass reviewers=9 normal_tools=4 artifact_tools=5 role_separated_artifacts=true known_ids_only=true session_start=true defense_in_depth=true\n');
}

main().catch((error) => {
  fail(`error=${JSON.stringify(error && error.message ? error.message : String(error))}`);
});
