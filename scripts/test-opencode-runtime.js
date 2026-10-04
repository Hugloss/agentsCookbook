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

  first.agent = { reviewer: { model: 'liteLLM/reviewer-model' } };
  second.agent = { reviewer: { model: 'liteLLM/reviewer-model' } };
  const left = runtime.inspectConfig(first);
  const right = runtime.inspectConfig(second);
  const reviewer = runtime.inspectConfig(first, 'reviewer');
  assert.strictEqual(left.model, 'liteLLM/gemma4');
  assert.strictEqual(left.provider, 'liteLLM');
  assert.strictEqual(reviewer.model, 'liteLLM/reviewer-model');
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
      command: [
        'uv', 'run', '--frozen', '--no-sync', 'hashmarks',
        '--workspace', '.', 'mcp'
      ],
      cwd: '.',
      enabled: process.env.FAKE_HASHMARKS_ENABLED === '1',
      disabled: process.env.FAKE_HASHMARKS_ENABLED !== '1'
    },
    enola: {
      type: 'local',
      command: ['enola'],
      enabled: false,
      disabled: true
    },
  };
  if (process.env.FAKE_NO_HASHMARKS === '1') delete servers.hashmarks;
  const base = {
    model: 'liteLLM/gemma4',
    provider: { liteLLM: { options: { apiKey: 'must-not-leak' } } },
    mcp: process.env.FAKE_MCP_SHAPE === 'nested'
      ? { servers } : servers,
  };
  const inline = process.env.OPENCODE_CONFIG_CONTENT
    ? JSON.parse(process.env.OPENCODE_CONFIG_CONTENT) : {};
  const resolved = merge(base, inline);
  if (process.env.FAKE_EFFECTIVE_MCP_DRIFT === '1') {
    const selected = resolved.mcp.servers?.hashmarks || resolved.mcp.hashmarks;
    if (selected) {
      selected.command = ['hashmarks', '--workspace', '/outside', 'mcp'];
    }
  }
  return resolved;
}

function value(flag) {
  const index = filtered.indexOf(flag);
  return index >= 0 ? filtered[index + 1] : '';
}

if (command === 'debug' && filtered[1] === 'config') {
  if (
    process.env.FAKE_FAIL_BASE_CONFIG === '1' &&
    !process.env.OPENCODE_CONFIG_CONTENT
  ) {
    process.stderr.write('unexpected base config resolution\\n');
    process.exit(17);
  }
  process.stdout.write(JSON.stringify(config()));
  process.exit(0);
}

if (command === 'mcp' && filtered[1] === 'list') {
  const resolved = config();
  const servers = resolved.mcp.servers || resolved.mcp;
  for (const [name, value] of Object.entries(servers)) {
    const status = value.enabled === false || value.disabled === true ||
      process.env.FAKE_MCP_DISCONNECTED === name
      ? (process.env.FAKE_MCP_STATUS || 'disabled') : 'connected';
    process.stdout.write(process.env.FAKE_MCP_TREE === '1'
      ? '●  ' + (status === 'connected' ? '✓' : '✗') + ' ' + name + ' ' + status + '\\n'
      : name + ': ' + status + '\\n');
    if (
      process.env.FAKE_MCP_TREE === '1' &&
      process.env.FAKE_MCP_DISCONNECTED === name &&
      process.env.FAKE_MCP_DETAIL
    ) {
      for (const line of process.env.FAKE_MCP_DETAIL.split('\\n')) {
        process.stdout.write('│      ' + line + '\\n');
      }
    }
  }
  if (process.env.FAKE_MCP_DISTRACTOR === '1') {
    process.stdout.write('backup_hashmarks: connected\\n');
  }
  if (process.env.FAKE_MCP_STDERR) {
    process.stderr.write(process.env.FAKE_MCP_STDERR + '\\n');
  }
  process.exit(Number(process.env.FAKE_MCP_EXIT || '0'));
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
  let delayedFinal = false;
  if (process.env.FAKE_EXPORT_DELAYED_FINAL === '1') {
    const countPath = statePath + '.exports';
    const count = fs.existsSync(countPath)
      ? Number(fs.readFileSync(countPath, 'utf8')) + 1
      : 1;
    fs.writeFileSync(countPath, String(count));
    delayedFinal = count === 1;
  }
  const text = process.env.FAKE_EXPORT_LARGE === '1'
    ? 'x'.repeat(180000)
    : 'done';
  const payload = JSON.stringify({
    messages: [{
      info: {
        role: 'assistant',
        providerID: 'liteLLM',
        modelID: 'gemma4'
      },
      parts: delayedFinal ? [] : [{ type: 'text', text }]
    }]
  });
  const stdoutIsRegularFile = fs.fstatSync(1).isFile();
  process.stdout.write(
    process.env.FAKE_EXPORT_TRUNCATE_PIPE === '1' && !stdoutIsRegularFile
      ? payload.slice(0, 131072)
      : payload
  );
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

function subjectExposure(root, name) {
  if (name === 'hashmarks') {
    return {
      name,
      command: [
        path.join(root, 'hashmarks'),
        '--workspace',
        '.',
        '--state-dir',
        path.join(root, 'hashmarks-state'),
        'mcp',
      ],
      cwd: root,
      environment: {},
      semantic_identity: {
        name,
        transport: 'stdio',
        workspace: 'trial-workspace',
      },
    };
  }
  if (name === 'enola') {
    const configPath = path.join(root, 'enola-benchmark.yaml');
    fs.writeFileSync(
      configPath,
      JSON.stringify({ repo: root, output: { dir: '.benchmark-enola' } }),
      'utf8',
    );
    return {
      name,
      command: [path.join(root, 'enola'), configPath],
      cwd: root,
      environment: {},
      semantic_identity: {
        name,
        transport: 'stdio',
        workspace: 'trial-workspace',
      },
    };
  }
  throw new Error(`unsupported test subject: ${name}`);
}

function testSelectedMcpFailureBlock() {
  const output = [
    '●  ✗ hashmarks failed',
    '│      MCP error -32000: Connection closed',
    '│      /work/Hashmarks/.venv/bin/hashmarks --workspace . mcp',
    '│      Traceback (most recent call last):',
    '│      ModuleNotFoundError: No module named \'mcp\'',
    '●  ✓ enola connected',
    '│      /home/user/.local/bin/enola',
  ].join('\n');

  const selected = runtime.selectedMcpLines(output, 'hashmarks');
  assert.match(selected, /ModuleNotFoundError: No module named 'mcp'/);
  assert.doesNotMatch(selected, /enola connected/);
  assert.doesNotMatch(selected, /\.local\/bin\/enola/);
}

function testExportUsesRegularFileCapture() {
  const root = fs.mkdtempSync(
    path.join(os.tmpdir(), 'agents-cookbook-opencode-export-'),
  );
  try {
    const fake = [process.execPath, writeFakeOpenCode(root)];
    const result = runtime.exportSession({
      opencodeBin: fake,
      repoDir: root,
      sessionId: 'ses_test',
      env: {
        FAKE_EXPORT_LARGE: '1',
        FAKE_EXPORT_TRUNCATE_PIPE: '1',
      },
    });
    assert.strictEqual(result.status, 0, result.stderr);
    const parsed = JSON.parse(result.stdout);
    assert.strictEqual(
      parsed.messages[0].parts[0].text.length,
      180000,
    );
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
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
    const projectConfigPath = path.join(root, 'opencode.json');
    const projectConfigText =
      '{"mcp":{"hashmarks":{"command":["ambient-hashmarks"]}}}\n';
    fs.writeFileSync(projectConfigPath, projectConfigText, 'utf8');

    const resolved = runtime.resolveNativeConfig({
      opencodeBin: fake,
      repoDir: root,
      env,
    });
    assert.strictEqual(resolved.status, 'completed', JSON.stringify(resolved));
    assert.strictEqual(resolved.inspection.model, 'liteLLM/gemma4');
    assert.ok(!JSON.stringify(resolved).includes('must-not-leak'));

    const cachedBase = {
      model: 'liteLLM/gemma4',
      provider: { liteLLM: { options: { apiKey: 'cached-secret' } } },
      mcp: {
        hashmarks: {
          type: 'local',
          command: ['ambient-hashmarks'],
          cwd: '.',
          enabled: false,
          disabled: true,
        },
        enola: {
          type: 'local',
          command: ['enola'],
          enabled: false,
          disabled: true,
        },
      },
    };
    const cachedExposure = subjectExposure(root, 'hashmarks');
    const cachedPrepared = runtime.prepareBenchmarkConfig({
      opencodeBin: fake,
      repoDir: root,
      agentName: 'build',
      env: { ...env, FAKE_FAIL_BASE_CONFIG: '1' },
      selectedSubject: 'hashmarks',
      subjectExposure: cachedExposure,
      baseConfig: cachedBase,
    });
    assert.strictEqual(
      cachedPrepared.status,
      'completed',
      cachedPrepared.reason,
    );
    assert.strictEqual(cachedPrepared.base_config_source, 'task-cache');
    assert.strictEqual(cachedPrepared.inspection.model, 'liteLLM/gemma4');

    const cachedDrift = runtime.prepareBenchmarkConfig({
      opencodeBin: fake,
      repoDir: root,
      agentName: 'build',
      env: {
        ...env,
        FAKE_FAIL_BASE_CONFIG: '1',
        FAKE_EFFECTIVE_MCP_DRIFT: '1',
      },
      selectedSubject: 'hashmarks',
      subjectExposure: cachedExposure,
      baseConfig: cachedBase,
    });
    assert.strictEqual(cachedDrift.status, 'failed');
    assert.match(
      cachedDrift.reason,
      /effective benchmark MCP definition changed/,
    );

    const nativeConflict = runtime.prepareBenchmarkConfig({
      opencodeBin: fake,
      repoDir: root,
      agentName: 'build',
      env: { ...env, FAKE_HASHMARKS_ENABLED: '1' },
      selectedSubject: 'hashmarks',
      subjectExposure: cachedExposure,
    });
    assert.strictEqual(nativeConflict.status, 'failed');
    assert.strictEqual(
      nativeConflict.failure_stage,
      'runtime-authority-conflict',
    );
    assert.match(nativeConflict.reason, /already enabled/);
    assert.match(nativeConflict.reason, /disable that native registration/);
    assert.strictEqual(
      nativeConflict.overlay_identity.native_server_conflict,
      true,
    );

    for (const shape of ['flat', 'nested']) {
      const exposure = subjectExposure(root, 'hashmarks');
      const prepared = runtime.prepareBenchmarkConfig({
        opencodeBin: fake,
        repoDir: root,
        agentName: 'build',
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
        subjectExposure: exposure,
      });
      assert.strictEqual(prepared.status, 'completed', prepared.reason);
      assert.strictEqual(prepared.selected_server, 'hashmarks');
      assert.strictEqual(prepared.inspection.model, 'liteLLM/gemma4');
      assert.strictEqual(
        prepared.overlay_identity.subject_definition_source,
        'benchmark-subject-exposure',
      );
      assert.strictEqual(prepared.overlay_identity.native_server_shadowed, true);
      assert.strictEqual(prepared.overlay_identity.native_server_conflict, false);
      assert.match(
        prepared.overlay_identity.subject_exposure_sha256,
        /^[0-9a-f]{64}$/,
      );
      const content = JSON.parse(prepared.environment.OPENCODE_CONFIG_CONTENT);
      const servers = shape === 'nested' ? content.mcp.servers : content.mcp;
      assert.strictEqual(content.provider.liteLLM.options.apiKey, 'inline-secret');
      assert.strictEqual(content.permission.bash, 'deny');
      assert.deepStrictEqual(servers.hashmarks.command, exposure.command);
      assert.notStrictEqual(servers.hashmarks.command[0], 'uv');
      assert.strictEqual(prepared.workspace_binding.verified, true);
      assert.strictEqual(prepared.native_subject_identity.verified, true);
      assert.strictEqual(
        fs.readFileSync(projectConfigPath, 'utf8'),
        projectConfigText,
      );
      assert.strictEqual(
        prepared.native_subject_identity.executable_path,
        fs.realpathSync(path.join(root, 'hashmarks')),
      );
      assert.match(
        prepared.native_subject_identity.executable_sha256,
        /^[0-9a-f]{64}$/,
      );
      assert.strictEqual(
        prepared.workspace_binding.method,
        'hashmarks-explicit-workspace',
      );
      if (shape === 'nested') {
        assert.strictEqual(servers.enola.disabled, true);
      } else {
        assert.strictEqual(servers.enola.enabled, false);
      }
      const { environment, ...safe } = prepared;
      assert.ok(!JSON.stringify(safe).includes('inline-secret'));
    }

    const exposure = subjectExposure(root, 'hashmarks');
    const firstHashmarksIdentity = runtime.prepareBenchmarkConfig({
      opencodeBin: fake,
      repoDir: root,
      agentName: 'build',
      env,
      selectedSubject: 'hashmarks',
      subjectExposure: exposure,
    }).native_subject_identity;
    fs.appendFileSync(path.join(root, 'hashmarks'), '# changed\n', 'utf8');
    const secondHashmarksIdentity = runtime.prepareBenchmarkConfig({
      opencodeBin: fake,
      repoDir: root,
      agentName: 'build',
      env,
      selectedSubject: 'hashmarks',
      subjectExposure: exposure,
    }).native_subject_identity;
    assert.strictEqual(firstHashmarksIdentity.verified, true);
    assert.strictEqual(secondHashmarksIdentity.verified, true);
    assert.notStrictEqual(
      firstHashmarksIdentity.executable_sha256,
      secondHashmarksIdentity.executable_sha256,
    );

    const withoutProjectRegistration = runtime.prepareBenchmarkConfig({
      opencodeBin: fake,
      repoDir: root,
      agentName: 'build',
      env: { ...env, FAKE_NO_HASHMARKS: '1' },
      selectedSubject: 'hashmarks',
      subjectExposure: exposure,
    });
    assert.strictEqual(
      withoutProjectRegistration.status,
      'completed',
      withoutProjectRegistration.reason,
    );
    assert.strictEqual(
      withoutProjectRegistration.overlay_identity.native_server_shadowed,
      false,
    );

    const enolaExposure = subjectExposure(root, 'enola');
    const enola = runtime.prepareBenchmarkConfig({
      opencodeBin: fake,
      repoDir: root,
      agentName: 'build',
      env,
      selectedSubject: 'enola',
      subjectExposure: enolaExposure,
    });
    assert.strictEqual(enola.status, 'completed', enola.reason);
    assert.strictEqual(enola.workspace_binding.verified, true);
    assert.strictEqual(enola.native_subject_identity.verified, true);
    assert.strictEqual(enola.native_subject_identity.subject, 'enola');
    assert.strictEqual(
      enola.workspace_binding.method,
      'enola-explicit-config-repository',
    );

    const bare = runtime.prepareBenchmarkConfig({
      opencodeBin: fake,
      repoDir: root,
      agentName: 'build',
      env,
    });
    assert.strictEqual(bare.status, 'completed', bare.reason);
    assert.strictEqual(bare.selected_server, null);
    assert.strictEqual(
      JSON.parse(bare.environment.OPENCODE_CONFIG_CONTENT).mcp.hashmarks.enabled,
      false,
    );

    const disconnected = runtime.prepareBenchmarkConfig({
      opencodeBin: fake,
      repoDir: root,
      agentName: 'build',
      env: {
        ...env,
        FAKE_MCP_DISCONNECTED: 'hashmarks',
        FAKE_MCP_STATUS: 'failed',
        FAKE_MCP_TREE: '1',
        FAKE_MCP_DETAIL: [
          'MCP error -32000: Connection closed',
          '/work/Hashmarks/.venv/bin/hashmarks --workspace . mcp',
          'Traceback (most recent call last):',
          "ModuleNotFoundError: No module named 'mcp'",
        ].join('\\n'),
        FAKE_MCP_STDERR:
          'Hashmarks MCP support requires the optional extra: install hashmarks[mcp]',
        FAKE_MCP_EXIT: '7',
      },
      selectedSubject: 'hashmarks',
      subjectExposure: exposure,
    });
    assert.strictEqual(disconnected.status, 'failed');
    assert.strictEqual(disconnected.failure_stage, 'mcp-connection');
    assert.match(disconnected.reason, /is not connected/);
    assert.match(disconnected.reason, /exit=7/);
    assert.match(disconnected.reason, /hashmarks failed/);
    assert.match(
      disconnected.reason,
      /ModuleNotFoundError: No module named 'mcp'/,
    );
    assert.doesNotMatch(disconnected.reason, /enola connected/);
    assert.match(
      disconnected.reason,
      /Hashmarks MCP support requires the optional extra/,
    );

    const nativeTree = runtime.prepareBenchmarkConfig({
      opencodeBin: fake,
      repoDir: root,
      agentName: 'build',
      env: { ...env, FAKE_MCP_TREE: '1' },
      selectedSubject: 'hashmarks',
      subjectExposure: exposure,
    });
    assert.strictEqual(nativeTree.status, 'completed', nativeTree.reason);

    for (const status of ['disconnected', 'not connected']) {
      const misleading = runtime.prepareBenchmarkConfig({
        opencodeBin: fake,
        repoDir: root,
        agentName: 'build',
        env: {
          ...env,
          FAKE_MCP_DISCONNECTED: 'hashmarks',
          FAKE_MCP_STATUS: status,
          FAKE_MCP_DISTRACTOR: '1',
        },
        selectedSubject: 'hashmarks',
        subjectExposure: exposure,
      });
      assert.strictEqual(misleading.status, 'failed');
    }

    const drifted = runtime.prepareBenchmarkConfig({
      opencodeBin: fake,
      repoDir: root,
      agentName: 'build',
      env: { ...env, FAKE_EFFECTIVE_MCP_DRIFT: '1' },
      selectedSubject: 'hashmarks',
      subjectExposure: exposure,
    });
    assert.strictEqual(drifted.status, 'failed');
    assert.strictEqual(drifted.failure_stage, undefined);
    assert.match(drifted.reason, /effective benchmark MCP definition changed/);

    const wrongExecutable = runtime.prepareBenchmarkConfig({
      opencodeBin: fake,
      repoDir: root,
      agentName: 'build',
      env,
      selectedSubject: 'hashmarks',
      subjectExposure: {
        ...exposure,
        command: ['bash', '--workspace', '.', 'mcp'],
      },
      probe: false,
    });
    assert.strictEqual(wrongExecutable.status, 'completed');
    assert.strictEqual(wrongExecutable.workspace_binding.verified, false);
    assert.match(
      wrongExecutable.workspace_binding.reason,
      /command form is unverified/,
    );

    const exposurePath = path.join(root, 'benchmark-exposure.json');
    fs.writeFileSync(exposurePath, JSON.stringify(exposure), 'utf8');
    const promptFile = path.join(root, 'prompt.txt');
    fs.writeFileSync(promptFile, 'hello', 'utf8');
    const admitted = runtime.prepareBenchmarkConfig({
      opencodeBin: fake,
      repoDir: root,
      agentName: 'build',
      env,
      selectedSubject: 'hashmarks',
      subjectExposure: exposure,
    });
    const changedAuthorityRun = require('child_process').spawnSync(
      process.execPath,
      [
        path.join(__dirname, 'opencode-runtime.js'),
        'run-export',
        '--repo',
        root,
        '--agent',
        'build',
        '--title',
        'blocked',
        '--prompt-file',
        promptFile,
        '--benchmark-subject',
        'hashmarks',
        '--benchmark-exposure-file',
        exposurePath,
        '--subject-exposure-sha256',
        '0'.repeat(64),
        '--subject-executable-sha256',
        admitted.native_subject_identity.executable_sha256,
        '--native-config-sha256',
        admitted.inspection.config_sha256,
      ],
      {
        encoding: 'utf8',
        env: { ...process.env, ...env, OPENCODE_BIN: fake[1] },
      },
    );
    assert.strictEqual(changedAuthorityRun.status, 0, changedAuthorityRun.stderr);
    assert.strictEqual(JSON.parse(changedAuthorityRun.stdout).run.status, 1);

    fs.appendFileSync(path.join(root, 'hashmarks'), '# replaced-after-admission\n', 'utf8');
    const replacedExecutableRun = require('child_process').spawnSync(
      process.execPath,
      [
        path.join(__dirname, 'opencode-runtime.js'),
        'run-export',
        '--repo',
        root,
        '--agent',
        'build',
        '--title',
        'blocked-replaced-executable',
        '--prompt-file',
        promptFile,
        '--benchmark-subject',
        'hashmarks',
        '--benchmark-exposure-file',
        exposurePath,
        '--subject-exposure-sha256',
        admitted.overlay_identity.subject_exposure_sha256,
        '--subject-executable-sha256',
        admitted.native_subject_identity.executable_sha256,
        '--native-config-sha256',
        admitted.inspection.config_sha256,
      ],
      {
        encoding: 'utf8',
        env: { ...process.env, ...env, OPENCODE_BIN: fake[1] },
      },
    );
    assert.strictEqual(
      replacedExecutableRun.status,
      0,
      replacedExecutableRun.stderr,
    );
    const replacedExecutableEnvelope = JSON.parse(replacedExecutableRun.stdout);
    assert.strictEqual(replacedExecutableEnvelope.run.status, 1);
    assert.match(
      replacedExecutableEnvelope.error,
      /authority changed after admission/,
    );

    const result = await runtime.runSessionAndExport({
      opencodeBin: fake,
      repoDir: root,
      title: 'runtime-test',
      prompt: 'hello',
      env,
      deleteAfterExport: true,
    });
    assert.strictEqual(result.schema, 'agents-cookbook-opencode-runtime/v2');
    assert.strictEqual(result.run.status, 0);
    assert.strictEqual(result.session_id, 'ses_test');
    assert.strictEqual(result.export.status, 0);
    assert.strictEqual(result.export_attempts, 1);
    assert.strictEqual(result.final_text, 'done');
    assert.strictEqual(result.export_parse_error, null);
    assert.strictEqual(result.delete.status, 0);

    const exportCountPath = statePath + '.exports';
    fs.rmSync(exportCountPath, { force: true });
    const delayed = await runtime.runSessionAndExport({
      opencodeBin: fake,
      repoDir: root,
      title: 'runtime-delayed-final',
      prompt: 'hello',
      env: { ...env, FAKE_EXPORT_DELAYED_FINAL: '1' },
      deleteAfterExport: true,
      exportAttempts: 3,
      exportDelayMs: 1,
    });
    assert.strictEqual(delayed.run.status, 0);
    assert.strictEqual(delayed.session_id, 'ses_test');
    assert.strictEqual(delayed.export.status, 0);
    assert.strictEqual(delayed.export_attempts, 2);
    assert.strictEqual(delayed.final_text, 'done');
    assert.strictEqual(delayed.export_parse_error, null);
    assert.strictEqual(
      fs.readFileSync(exportCountPath, 'utf8'),
      '2',
      'successful run should reread the same session until final text is persisted',
    );

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
  testExportUsesRegularFileCapture();
  testSelectedMcpFailureBlock();
  const parsed = runtime.extractFinalAnswer(
    JSON.stringify({
      messages: [{
        info: { role: 'assistant' },
        parts: [{ type: 'text', text: 'final' }],
      }],
    }),
  );
  assert.strictEqual(parsed.text, 'final');
  assert.throws(() => runtime.extractFinalAnswer(JSON.stringify({
    messages: [{ info: { role: 'assistant' }, parts: [{ type: 'tool' }] }],
  })), /no final text/);
  assert.throws(() => runtime.extractFinalAnswer(JSON.stringify({
    messages: [{ info: { role: 'assistant' }, parts: [
      { type: 'text', text: 'earlier answer' }, { type: 'tool' },
    ] }],
  })), /no final text/);
  assert.throws(() => runtime.extractFinalAnswer('banner\n{"messages":[]}'), /Unexpected token|not valid JSON/);
  assert.throws(() => runtime.extractFinalAnswer(JSON.stringify({
    messages: [
      { info: { role: 'assistant' }, parts: [{ type: 'text', text: 'old' }] },
      { info: { role: 'assistant' }, parts: [] },
    ],
  })), /no final text/);
  await testSharedLifecycle();
  process.stdout.write('opencode-runtime tests: PASS\n');
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exit(1);
});
