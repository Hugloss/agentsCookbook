#!/usr/bin/env node
'use strict';

// Installation regression, not a model-configuration resolver or runtime gate.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { test } = require('node:test');

const root = path.resolve(__dirname, '..');
const files = fs.readdirSync(path.join(root, 'agents')).filter((name) => name.endsWith('.md'));
const inferenceKey = /^\s*["']?(?:model|provider|temperature|top_p|top_k|thinking|reasoningEffort|model_reasoning_effort|max_tokens|maxTokens|contextWindow|compaction)["']?\s*:/m;
function assertRoleOnly(text, label) {
  const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/);
  assert.ok(match, `${label}: frontmatter missing`);
  assert.doesNotMatch(match[1], inferenceKey, `${label}: inference settings belong to the native host`);
  assert.match(match[1], /^mode: (primary|subagent)$/m);
  assert.match(match[1], /^permission:\n  "\*": deny$/m);
}

test('canonical agents contain role contracts but no inference defaults', () => {
  assert.ok(files.length > 0);
  for (const name of files) assertRoleOnly(fs.readFileSync(path.join(root, 'agents', name), 'utf8'), name);
  for (const setting of ['model: other/model', 'temperature: 0', 'thinking: medium']) {
    assert.throws(() => assertRoleOnly(`---\nmode: subagent\n${setting}\npermission:\n  "*": deny\n---\n`, 'mutation'), /inference settings/);
  }
  assert.match(fs.readFileSync(path.join(root, 'agents/ping-pong-plan.md'), 'utf8'), /^systemPrompt: replace$/m);
});

for (const configured of [false, true]) {
  test(`installer preserves ${configured ? 'custom' : 'absent'} native inference settings`, (t) => {
    const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'cookbook-native-config-'));
    t.after(() => fs.rmSync(temp, { recursive: true, force: true }));
    const globalDir = path.join(temp, 'config', 'opencode');
    const piDir = path.join(temp, 'pi');
    const skillsDir = path.join(temp, 'skills');
    fs.mkdirSync(globalDir, { recursive: true });
    fs.mkdirSync(piDir, { recursive: true });
    const nativeFiles = new Map([
      [path.join(globalDir, 'opencode.jsonc'), '// operator-owned comments\n{"model":"local/org/custom","compaction":{"auto":false,"reserved":0},"agent":{"plan-fact-auditor":{"temperature":0,"reasoningEffort":"low"}}}\n'],
      [path.join(piDir, 'settings.json'), '{"defaultProvider":"local","defaultModel":"custom","defaultThinkingLevel":"off","compaction":{"enabled":false}}\n'],
    ]);
    if (configured) for (const [file, bytes] of nativeFiles) fs.writeFileSync(file, bytes);
    const argv = ['scripts/link-opencode-local.sh', '--global-dir', globalDir, '--pi-agent-dir', piDir, '--shared-skill-dir', skillsDir];
    for (const dryRun of [true, false, false]) {
      const result = spawnSync('bash', [...argv, ...(dryRun ? ['--dry-run'] : [])], {
        cwd: root,
        env: { ...process.env, HOME: temp, XDG_CONFIG_HOME: path.join(temp, 'config') },
        encoding: 'utf8', timeout: 30000, maxBuffer: 4 * 1024 * 1024,
      });
      assert.ifError(result.error);
      assert.equal(result.status, 0, result.stdout + result.stderr);
      for (const [file, bytes] of nativeFiles) {
        if (configured) assert.equal(fs.readFileSync(file, 'utf8'), bytes);
        else assert.equal(fs.existsSync(file), false, `installer synthesized ${file}`);
      }
    }
    for (const dir of [globalDir, piDir]) for (const name of files) {
      const installed = path.join(dir, 'agents', name);
      assert.equal(fs.realpathSync(installed), fs.realpathSync(path.join(root, 'agents', name)));
      assertRoleOnly(fs.readFileSync(installed, 'utf8'), installed);
    }
  });
}
