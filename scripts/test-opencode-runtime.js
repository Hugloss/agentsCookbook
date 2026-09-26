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

function merge(base, overlay) {
  const result = { ...base };
  for (const [key, value] of Object.entries(overlay)) {
    result[key] = value && typeof value === 'object' && !Array.isArray(value) &&
      result[key] && typeof result[key] === 'object' && !Array.isArray(result[key])
      ? merge(result[key], value) : value;
  }
  return result;
}

function config() {
  const servers = {
    hashmarks: {
      type: 'local',
      command: ['hashmarks', '--workspace', '.', 'mcp'],
      cwd: '.',
      enabled: true
    },
    enola: { type: 'local', command: ['enola'], enabled: true },
  };
  const base = {
    model: 'liteLLM/gemma4',
    provider: { liteLLM: { options: { apiKey: 'must-not-leak' } } },
    mcp: process.env.FAKE_MCP_SHAPE === 'nested'
      ? { servers } : servers,
  };
  if (process.env.FAKE_UNVERIFIED_COMMAND === '1') {
    servers.hashmarks.command = ['echo'];
  }
  const inline = process.env.OPENCODE_CONFIG_CONTENT
    ? JSON.parse(process.env.OPENCODE_CONFIG_CONTENT) : {};
  const resolved = merge(base, inline);
  if (process.env.FAKE_EFFECTIVE_MCP_DRIFT === '1' &&
      (inline.tools?.['hashmarks_*'] === true ||
       inline.mcp?.servers?.enola?.disabled === true)) {
    const selected = resolved.mcp.servers?.hashmarks || resolved.mcp.hashmarks;
    selected.command = ['hashmarks', '--workspace', '/outside', 'mcp'];
  }
  return resolved;
}

function value(flag) {
  const index = filtered.indexOf(flag);
  return index >= 0 ? filtered[index + 1] : '';
}

if (command === 'debug' && filtered[1] === 'config') {
  process.stdout.write(JSON.stringify(config()));
  process.exit(0);
}

if (command === 'mcp' && filtered[1] === 'list') {
  const resolved = config();
  const servers = resolved.mcp.servers || resolved.mcp;
  for (const [name, value] of Object.entries(servers)) {
    process.stdout.write(name + ': ' +
      (value.enabled === false || value.disabled === true || process.env.FAKE_MCP_DISCONNECTED === name
        ? (process.env.FAKE_MCP_STATUS || 'disabled') : 'connected') + '\\n');
  }
  if (process.env.FAKE_MCP_DISTRACTOR === '1') {
    process.stdout.write('backup_hashmarks: connected\\n');
  }
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
    const fake = [process.execPath, writeFakeOpenCode(root)];
    for (const name of ['hashmarks', 'enola']) {
      const executable = path.join(root, name);
      fs.writeFileSync(executable, '#!/bin/sh\nexit 0\n', 'utf8');
      fs.chmodSync(executable, 0o755);
    }
    const statePath = path.join(root, 'state.json');
    const env = {
      FAKE_OPENCODE_STATE: statePath,
      PATH: root + path.delimiter + (process.env.PATH || ''),
    };

    const resolved = runtime.resolveNativeConfig({
      opencodeBin: fake,
      repoDir: root,
      env,
    });
    assert.strictEqual(resolved.status, 'completed', JSON.stringify(resolved));
    assert.strictEqual(resolved.inspection.model, 'liteLLM/gemma4');
    assert.ok(!JSON.stringify(resolved).includes('must-not-leak'));

    for (const shape of ['flat', 'nested']) {
      const prepared = runtime.prepareBenchmarkConfig({
        opencodeBin: fake,
        repoDir: root,
        env: {
          ...env,
          FAKE_MCP_SHAPE: shape,
          OPENCODE_CONFIG_CONTENT: JSON.stringify({
            agent: { build: { model: 'liteLLM/gemma4' } },
            provider: { liteLLM: { options: { apiKey: 'inline-secret' } } },
            permission: { bash: 'deny' },
          }),
        },
        selectedSubject: 'hashmarks',
      });
      assert.strictEqual(prepared.status, 'completed', prepared.reason);
      assert.strictEqual(prepared.selected_server, 'hashmarks');
      assert.strictEqual(prepared.inspection.model, 'liteLLM/gemma4');
      assert.strictEqual(
        prepared.overlay_identity.native_server_reused,
        true,
      );
      const content = JSON.parse(prepared.environment.OPENCODE_CONFIG_CONTENT);
      const servers = shape === 'nested' ? content.mcp.servers : content.mcp;
      assert.strictEqual(content.provider.liteLLM.options.apiKey, 'inline-secret');
      assert.strictEqual(content.permission.bash, 'deny');
      assert.deepStrictEqual(
        servers.hashmarks.command,
        ['hashmarks', '--workspace', '.', 'mcp'],
      );
      assert.strictEqual(prepared.workspace_binding.verified, true);
      assert.strictEqual(
        prepared.native_subject_identity.verified,
        true,
      );
      assert.strictEqual(
        prepared.native_subject_identity.subject,
        'hashmarks',
      );
      assert.match(
        prepared.native_subject_identity.executable_sha256,
        /^[0-9a-f]{64}$/,
      );
      assert.strictEqual(
        prepared.workspace_binding.method,
        'hashmarks-explicit-workspace',
      );
      assert.ok(!Object.hasOwn(servers, 'benchmark_hashmarks'));
      if (shape === 'nested') {
        assert.notStrictEqual(servers.hashmarks.disabled, true);
        assert.strictEqual(servers.enola.disabled, true);
      } else {
        assert.notStrictEqual(servers.hashmarks.enabled, false);
        assert.strictEqual(servers.enola.enabled, false);
      }
      const { environment, ...safe } = prepared;
      assert.ok(!JSON.stringify(safe).includes('inline-secret'));
    }

    const firstHashmarksIdentity = runtime.prepareBenchmarkConfig({
      opencodeBin: fake,
      repoDir: root,
      env,
      selectedSubject: 'hashmarks',
    }).native_subject_identity;
    fs.appendFileSync(path.join(root, 'hashmarks'), '# changed\n', 'utf8');
    const secondHashmarksIdentity = runtime.prepareBenchmarkConfig({
      opencodeBin: fake,
      repoDir: root,
      env,
      selectedSubject: 'hashmarks',
    }).native_subject_identity;
    assert.strictEqual(firstHashmarksIdentity.verified, true);
    assert.strictEqual(secondHashmarksIdentity.verified, true);
    assert.notStrictEqual(
      firstHashmarksIdentity.executable_sha256,
      secondHashmarksIdentity.executable_sha256,
    );

    const enola = runtime.prepareBenchmarkConfig({
      opencodeBin: fake,
      repoDir: root,
      env,
      selectedSubject: 'enola',
    });
    assert.strictEqual(enola.status, 'completed', enola.reason);
    assert.strictEqual(enola.workspace_binding.verified, true);
    assert.strictEqual(enola.native_subject_identity.verified, true);
    assert.strictEqual(enola.native_subject_identity.subject, 'enola');
    assert.strictEqual(
      enola.workspace_binding.method,
      'enola-default-repository-from-mcp-cwd',
    );

    const outside = runtime.verifyWorkspaceBinding(
      {
        mcp: {
          hashmarks: {
            type: 'local',
            command: ['hashmarks', '--workspace', '/outside', 'mcp'],
            cwd: '.',
            enabled: true,
          },
          enola: {
            type: 'local',
            command: ['enola'],
            cwd: '/outside',
            enabled: true,
          },
        },
      },
      'flat',
      'hashmarks',
      root,
    );
    assert.strictEqual(outside.verified, false);
    assert.match(outside.reason, /outside trial workspace/);

    const enolaOutside = runtime.verifyWorkspaceBinding(
      {
        mcp: {
          enola: {
            type: 'local',
            command: ['enola'],
            cwd: '/outside',
            enabled: true,
          },
        },
      },
      'flat',
      'enola',
      root,
    );
    assert.strictEqual(enolaOutside.verified, false);
    assert.match(enolaOutside.reason, /outside trial workspace/);

    const enolaConfigArgument = runtime.verifyWorkspaceBinding(
      {
        mcp: {
          enola: {
            type: 'local',
            command: ['enola', '/outside/mcp-arch.yaml'],
            cwd: '.',
            enabled: true,
          },
        },
      },
      'flat',
      'enola',
      root,
    );
    assert.strictEqual(enolaConfigArgument.verified, false);
    assert.match(enolaConfigArgument.reason, /cannot be proven/);

    const bare = runtime.prepareBenchmarkConfig({
      opencodeBin: fake, repoDir: root, env,
    });
    assert.strictEqual(bare.status, 'completed', bare.reason);
    assert.strictEqual(bare.selected_server, null);
    assert.strictEqual(JSON.parse(bare.environment.OPENCODE_CONFIG_CONTENT).mcp.hashmarks.enabled, false);

    const disconnected = runtime.prepareBenchmarkConfig({
      opencodeBin: fake,
      repoDir: root,
      env: { ...env, FAKE_MCP_DISCONNECTED: 'hashmarks' },
      selectedSubject: 'hashmarks',
    });
    assert.strictEqual(disconnected.status, 'failed');
    assert.match(disconnected.reason, /is not connected/);

    for (const status of ['disconnected', 'not connected']) {
      const misleading = runtime.prepareBenchmarkConfig({
        opencodeBin: fake,
        repoDir: root,
        env: {
          ...env,
          FAKE_MCP_DISCONNECTED: 'hashmarks',
          FAKE_MCP_STATUS: status,
          FAKE_MCP_DISTRACTOR: '1',
        },
        selectedSubject: 'hashmarks',
      });
      assert.strictEqual(misleading.status, 'failed');
    }

    const drifted = runtime.prepareBenchmarkConfig({
      opencodeBin: fake,
      repoDir: root,
      env: { ...env, FAKE_EFFECTIVE_MCP_DRIFT: '1' },
      selectedSubject: 'hashmarks',
    });
    assert.strictEqual(drifted.status, 'failed');
    assert.match(drifted.reason, /effective native MCP definition changed/);

    for (const command of [
      ['hashmarks', '--workspace', '.', '--workspace', '/outside', 'mcp'],
      ['bash', '--workspace', '.', 'mcp'],
      ['hashmarks', '--workspace', '.', 'serve'],
    ]) {
      const binding = runtime.verifyWorkspaceBinding(
        { mcp: { hashmarks: { type: 'local', command } } },
        'flat', 'hashmarks', root,
      );
      assert.strictEqual(binding.verified, false, JSON.stringify(command));
    }
    assert.strictEqual(runtime.verifyWorkspaceBinding(
      { mcp: { enola: { type: 'local', command: ['echo'] } } },
      'flat', 'enola', root,
    ).verified, false);

    const unverifiedEnv = { ...env, FAKE_UNVERIFIED_COMMAND: '1' };
    const unverified = runtime.prepareBenchmarkConfig({
      opencodeBin: fake,
      repoDir: root,
      env: unverifiedEnv,
      selectedSubject: 'hashmarks',
    });
    assert.strictEqual(unverified.status, 'completed');
    assert.strictEqual(unverified.workspace_binding.verified, false);
    const promptFile = path.join(root, 'prompt.txt');
    fs.writeFileSync(promptFile, 'hello');
    const blockedRun = require('child_process').spawnSync(
      process.execPath,
      [path.join(__dirname, 'opencode-runtime.js'), 'run-export',
        '--repo', root, '--title', 'blocked', '--prompt-file', promptFile,
        '--benchmark-subject', 'hashmarks', '--native-config-sha256',
        unverified.inspection.config_sha256],
      { encoding: 'utf8', env: { ...process.env, ...unverifiedEnv, OPENCODE_BIN: fake[1] } },
    );
    assert.strictEqual(blockedRun.status, 0, blockedRun.stderr);
    assert.strictEqual(JSON.parse(blockedRun.stdout).run.status, 1);
    assert.strictEqual(fs.existsSync(statePath), false);

    const missing = runtime.prepareBenchmarkConfig({
      opencodeBin: fake,
      repoDir: root,
      env,
      selectedSubject: 'missing-subject',
    });
    assert.strictEqual(missing.status, 'failed');
    assert.match(missing.reason, /does not define MCP server/);

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
