#!/usr/bin/env node
'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');

const runtime = require('./opencode-runtime.js');

function testConfigInspection() {
  const first = {
    model: 'liteLLM/gemma4',
    provider: {
      liteLLM: {
        options: {
          apiKey: 'secret-one',
          baseURL: 'http://127.0.0.1:4000/v1',
        },
      },
    },
    mcp: {
      hashmarks: { type: 'local', enabled: true },
      enola: { type: 'local', disabled: true },
    },
  };
  const second = JSON.parse(JSON.stringify(first));
  second.provider.liteLLM.options.apiKey = 'secret-two';

  const left = runtime.inspectConfig(first);
  const right = runtime.inspectConfig(second);
  assert.strictEqual(left.model, 'liteLLM/gemma4');
  assert.strictEqual(left.provider, 'liteLLM');
  assert.strictEqual(left.config_sha256, right.config_sha256);
  assert.deepStrictEqual(left.mcp_servers, [
    { name: 'enola', enabled: false },
    { name: 'hashmarks', enabled: true },
  ]);

  second.model = 'liteLLM/other';
  assert.notStrictEqual(
    left.config_sha256,
    runtime.inspectConfig(second).config_sha256,
  );
}

function writeFakeOpenCode(root) {
  const script = path.join(root, 'fake-opencode');
  fs.writeFileSync(
    script,
    `#!/usr/bin/env node
'use strict';
const fs = require('fs');
const args = process.argv.slice(2);
const filtered = args[0] === '--pure' ? args.slice(1) : args;
const command = filtered[0];
const statePath = process.env.FAKE_OPENCODE_STATE;

function value(flag) {
  const index = filtered.indexOf(flag);
  return index >= 0 ? filtered[index + 1] : '';
}

if (command === 'debug' && filtered[1] === 'config') {
  process.stdout.write(JSON.stringify({
    model: 'liteLLM/gemma4',
    provider: {
      liteLLM: {
        options: {
          apiKey: 'must-not-leak',
          baseURL: 'http://127.0.0.1:4000/v1'
        }
      }
    },
    mcp: {
      hashmarks: { type: 'local', enabled: true }
    }
  }));
  process.exit(0);
}

if (command === 'run') {
  const state = {
    id: 'ses_test',
    title: value('--title'),
    directory: value('--dir'),
    updated: Date.now(),
    pure: args[0] === '--pure'
  };
  fs.writeFileSync(statePath, JSON.stringify(state));
  process.stdout.write('{"type":"run"}\\n');
  process.exit(0);
}

if (command === 'session' && filtered[1] === 'list') {
  const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));
  process.stdout.write(JSON.stringify([state]));
  process.exit(0);
}

if (command === 'export') {
  process.stdout.write(JSON.stringify({
    messages: [{
      info: {
        role: 'assistant',
        providerID: 'liteLLM',
        modelID: 'gemma4'
      },
      parts: [{ type: 'text', text: 'done' }]
    }]
  }));
  process.exit(0);
}

if (command === 'session' && filtered[1] === 'delete') {
  process.stdout.write('deleted\\n');
  process.exit(0);
}

process.stderr.write('unexpected fake opencode args: ' + JSON.stringify(args) + '\\n');
process.exit(9);
`,
    'utf8',
  );
  fs.chmodSync(script, 0o755);
  return script;
}

async function testSharedLifecycle() {
  const root = fs.mkdtempSync(
    path.join(os.tmpdir(), 'agents-cookbook-opencode-runtime-'),
  );
  try {
    const fake = writeFakeOpenCode(root);
    const statePath = path.join(root, 'state.json');
    const env = { FAKE_OPENCODE_STATE: statePath };

    const resolved = runtime.resolveNativeConfig({
      opencodeBin: fake,
      repoDir: root,
      env,
    });
    assert.strictEqual(resolved.status, 'completed');
    assert.strictEqual(resolved.inspection.model, 'liteLLM/gemma4');
    assert.ok(!JSON.stringify(resolved).includes('must-not-leak'));

    const result = await runtime.runSessionAndExport({
      opencodeBin: fake,
      repoDir: root,
      title: 'runtime-test',
      prompt: 'hello',
      env,
      deleteAfterExport: true,
    });
    assert.strictEqual(result.run.status, 0);
    assert.strictEqual(result.session_id, 'ses_test');
    assert.strictEqual(result.export.status, 0);
    assert.strictEqual(result.final_text, 'done');
    assert.strictEqual(result.export_parse_error, null);
    assert.strictEqual(result.delete.status, 0);

    const legacy = runtime.runSession({
      opencodeBin: fake,
      repoDir: root,
      title: 'legacy-mode',
      prompt: 'legacy',
      env,
      pure: false,
    });
    assert.strictEqual(legacy.command.status, 0);
    const legacyState = JSON.parse(
      fs.readFileSync(statePath, 'utf8'),
    );
    assert.strictEqual(legacyState.pure, false);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

async function main() {
  testConfigInspection();
  const parsed = runtime.extractFinalAnswer(
    JSON.stringify({
      messages: [{
        info: { role: 'assistant' },
        parts: [{ type: 'text', text: 'final' }],
      }],
    }),
  );
  assert.strictEqual(parsed.text, 'final');
  await testSharedLifecycle();
  process.stdout.write('opencode-runtime tests: PASS\n');
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exit(1);
});
