#!/usr/bin/env node
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const RUNTIME_SCHEMA = 'agents-cookbook-opencode-runtime/v1';
const SECRET_KEYS = new Set([
  'api_key',
  'apikey',
  'authorization',
  'cookie',
  'credential',
  'credentials',
  'password',
  'secret',
  'token',
]);

function runCommand(command, args, options = {}) {
  const executable = Array.isArray(command) ? command[0] : command;
  const argv = Array.isArray(command) ? [...command.slice(1), ...args] : args;
  const result = spawnSync(executable, argv, {
    cwd: options.cwd || process.cwd(),
    env: { ...process.env, ...(options.env || {}) },
    encoding: 'utf8',
    maxBuffer: options.maxBuffer || 50 * 1024 * 1024,
  });

  return {
    status: result.error ? 1 : typeof result.status === 'number' ? result.status : 1,
    stdout: result.stdout || '',
    stderr: result.stderr || '',
    error: result.error ? String(result.error.message || result.error) : null,
    signal: result.signal || null,
  };
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function readJsonText(raw, label) {
  const jsonStart = raw.indexOf('{');
  if (jsonStart === -1) {
    throw new Error(`${label}: missing JSON object`);
  }
  return JSON.parse(raw.slice(jsonStart));
}

function extractFinalAnswer(exportOutput) {
  const data = readJsonText(exportOutput, 'opencode export');
  const messages = Array.isArray(data.messages) ? data.messages : [];
  const assistantMessages = messages.filter(
    (message) =>
      message &&
      message.info &&
      message.info.role === 'assistant',
  );
  if (assistantMessages.length === 0) {
    throw new Error('opencode export: no assistant messages found');
  }

  const finalMessage = assistantMessages[assistantMessages.length - 1];
  const parts = Array.isArray(finalMessage.parts) ? finalMessage.parts : [];
  const text = parts
    .filter(
      (part) =>
        part &&
        part.type === 'text' &&
        typeof part.text === 'string',
    )
    .map((part) => part.text)
    .join('\n')
    .trim();

  return { data, text };
}

function normalizeKey(key) {
  return String(key).toLowerCase().replaceAll('-', '_');
}

function isSecretKey(key) {
  const normalized = normalizeKey(key);
  return (
    SECRET_KEYS.has(normalized) ||
    normalized.endsWith('_api_key') ||
    normalized.endsWith('_token') ||
    normalized.endsWith('_secret') ||
    normalized.endsWith('_password')
  );
}

function sanitize(value, key = '') {
  if (isSecretKey(key)) {
    return '<redacted>';
  }
  if (Array.isArray(value)) {
    return value.map((item) => sanitize(item));
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([childKey, child]) => [
          childKey,
          sanitize(child, childKey),
        ]),
    );
  }
  return value;
}

function sortValue(value) {
  if (Array.isArray(value)) {
    return value.map(sortValue);
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, child]) => [key, sortValue(child)]),
    );
  }
  return value;
}

function canonicalJson(value) {
  return `${JSON.stringify(sortValue(value))}\n`;
}

function sha256Text(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function configuredModel(config) {
  const build =
    config &&
    config.agent &&
    typeof config.agent === 'object' &&
    config.agent.build &&
    typeof config.agent.build === 'object'
      ? config.agent.build
      : null;
  if (build && typeof build.model === 'string' && build.model) {
    return build.model;
  }
  return typeof config.model === 'string' && config.model
    ? config.model
    : null;
}

function providerFromModel(model) {
  if (typeof model !== 'string' || !model.includes('/')) {
    return null;
  }
  return model.split('/', 1)[0];
}

function inspectMcp(config) {
  const mcp =
    config && config.mcp && typeof config.mcp === 'object'
      ? config.mcp
      : {};
  const nested =
    mcp.servers && typeof mcp.servers === 'object'
      ? mcp.servers
      : null;
  const servers = nested || mcp;
  const entries = Object.entries(servers)
    .filter(([, value]) => value && typeof value === 'object')
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([name, value]) => ({
      name,
      enabled:
        value.enabled !== false &&
        value.disabled !== true,
    }));
  return {
    shape: nested ? 'nested-servers' : 'flat',
    servers: entries,
  };
}

function inspectConfig(config) {
  const model = configuredModel(config);
  const mcp = inspectMcp(config);
  return {
    model,
    provider: providerFromModel(model),
    config_sha256: sha256Text(canonicalJson(sanitize(config))),
    mcp_shape: mcp.shape,
    mcp_servers: mcp.servers,
  };
}

function mergeObjects(base, overlay) {
  const result = { ...base };
  for (const [key, value] of Object.entries(overlay)) {
    if (
      value && typeof value === 'object' && !Array.isArray(value) &&
      result[key] && typeof result[key] === 'object' && !Array.isArray(result[key])
    ) {
      result[key] = mergeObjects(result[key], value);
    } else {
      result[key] = value;
    }
  }
  return result;
}

function inlineConfig(env) {
  const raw = env.OPENCODE_CONFIG_CONTENT;
  if (!raw) return {};
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error('OPENCODE_CONFIG_CONTENT is not valid JSON');
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('OPENCODE_CONFIG_CONTENT must be a JSON object');
  }
  return parsed;
}

function mcpEntries(config, shape) {
  const mcp = config.mcp || {};
  return shape === 'nested-servers' ? (mcp.servers || {}) : mcp;
}

function benchmarkOverlay(config, selectedSubject) {
  const inspected = inspectMcp(config);
  const nested = inspected.shape === 'nested-servers';
  const source = mcpEntries(config, inspected.shape);
  const servers = {};
  const tools = {};

  if (selectedSubject && !Object.hasOwn(source, selectedSubject)) {
    throw new Error(
      `native OpenCode config does not define MCP server ${selectedSubject}`,
    );
  }

  for (const [name, value] of Object.entries(source)) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) continue;
    const selected = selectedSubject === name;
    const nativeEnabled =
      value.enabled !== false && value.disabled !== true;
    if (selected && !nativeEnabled) {
      throw new Error(
        `native OpenCode MCP server ${name} is disabled`,
      );
    }
    servers[name] = selected
      ? { ...value }
      : nested
        ? { ...value, disabled: true }
        : { ...value, enabled: false };
    tools[`${name}_*`] = selected;
  }

  return {
    selected: selectedSubject || null,
    shape: inspected.shape,
    config: {
      mcp: nested ? { servers } : servers,
      ...(nested ? {} : {
        tools,
        agent: { build: { tools } },
      }),
    },
  };
}

function verifyBenchmarkConfig(base, effective, overlay, selectedSubject) {
  const original = inspectConfig(base);
  const resolved = inspectConfig(effective);
  if (original.model !== resolved.model || original.provider !== resolved.provider) {
    throw new Error('benchmark overlay changed native OpenCode model/provider');
  }

  const baseServers = mcpEntries(base, overlay.shape);
  const servers = mcpEntries(effective, overlay.shape);
  for (const name of Object.keys(baseServers)) {
    const value = servers[name];
    const selected = name === selectedSubject;
    if (!value) {
      throw new Error(`benchmark overlay removed native MCP server ${name}`);
    }
    if (
      selected
        ? (overlay.shape === 'nested-servers'
          ? value.disabled === true
          : value.enabled === false)
        : (overlay.shape === 'nested-servers'
          ? value.disabled !== true
          : value.enabled !== false)
    ) {
      throw new Error(
        `benchmark overlay resolved unexpected MCP state for ${name}`,
      );
    }
  }

  if (overlay.shape === 'flat') {
    const tools = effective.tools || {};
    const buildTools = ((effective.agent || {}).build || {}).tools || {};
    for (const [name, expected] of Object.entries(overlay.config.tools)) {
      if (tools[name] !== expected || buildTools[name] !== expected) {
        throw new Error(`benchmark MCP tool gate did not resolve for ${name}`);
      }
    }
  }
  return resolved;
}

function commandPrefix(pure) {
  return pure ? ['--pure'] : [];
}

function effectiveEnv({ homeDir, env }) {
  const result = { ...(env || {}) };
  if (homeDir) {
    result.HOME = homeDir;
  }
  return result;
}

async function findSessionId({
  opencodeBin = process.env.OPENCODE_BIN || 'opencode',
  repoDir,
  title,
  startedAt = 0,
  homeDir = '',
  env = {},
  attempts = 12,
  delayMs = 500,
  pure = true,
}) {
  const commandEnv = effectiveEnv({ homeDir, env });
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    const sessionList = runCommand(
      opencodeBin,
      [
        ...commandPrefix(pure),
        'session',
        'list',
        '--format',
        'json',
        '--max-count',
        '20',
      ],
      { cwd: repoDir, env: commandEnv },
    );

    if (sessionList.status === 0) {
      try {
        const sessions = JSON.parse(sessionList.stdout);
        if (Array.isArray(sessions) && sessions.length > 0) {
          const exactMatch = sessions.find(
            (session) =>
              session &&
              session.title === title &&
              session.directory === repoDir,
          );
          if (exactMatch && exactMatch.id) {
            return exactMatch.id;
          }

          const timeMatch = sessions
            .filter(
              (session) =>
                session &&
                session.directory === repoDir &&
                typeof session.updated === 'number' &&
                session.updated >= startedAt,
            )
            .sort((left, right) => right.updated - left.updated)[0];
          if (timeMatch && timeMatch.id) {
            return timeMatch.id;
          }
        }
      } catch {
        // Retry until OpenCode persists a readable session list.
      }
    }

    if (attempt < attempts - 1) {
      await sleep(delayMs);
    }
  }
  return '';
}

function exportSession({
  opencodeBin = process.env.OPENCODE_BIN || 'opencode',
  repoDir,
  sessionId,
  homeDir = '',
  env = {},
  pure = true,
}) {
  return runCommand(
    opencodeBin,
    [...commandPrefix(pure), 'export', sessionId],
    {
      cwd: repoDir,
      env: effectiveEnv({ homeDir, env }),
    },
  );
}

function deleteSession({
  opencodeBin = process.env.OPENCODE_BIN || 'opencode',
  repoDir,
  sessionId,
  homeDir = '',
  env = {},
  pure = true,
}) {
  return runCommand(
    opencodeBin,
    [...commandPrefix(pure), 'session', 'delete', sessionId],
    {
      cwd: repoDir,
      env: effectiveEnv({ homeDir, env }),
      maxBuffer: 2 * 1024 * 1024,
    },
  );
}

function resolveNativeConfig({
  opencodeBin = process.env.OPENCODE_BIN || 'opencode',
  repoDir,
  env = {},
  pure = true,
}) {
  const resolved = readNativeConfig({ opencodeBin, repoDir, env, pure });
  const { config, ...safe } = resolved;
  return safe;
}

function readNativeConfig({
  opencodeBin = process.env.OPENCODE_BIN || 'opencode',
  repoDir,
  env = {},
  pure = true,
}) {
  const command = runCommand(
    opencodeBin,
    [...commandPrefix(pure), 'debug', 'config'],
    { cwd: repoDir, env },
  );
  const commandEvidence = {
    status: command.status,
    stderr: command.stderr,
    error: command.error,
    signal: command.signal,
  };
  if (command.status !== 0) {
    return {
      status: 'failed',
      command: commandEvidence,
      inspection: null,
      config: null,
    };
  }
  try {
    const config = readJsonText(
      command.stdout,
      'opencode debug config',
    );
    return {
      status: 'completed',
      command: commandEvidence,
      inspection: inspectConfig(config),
      config,
    };
  } catch (error) {
    return {
      status: 'failed',
      command: commandEvidence,
      inspection: null,
      config: null,
      parse_error: String(error.message || error),
    };
  }
}

function prepareBenchmarkConfig({
  opencodeBin = process.env.OPENCODE_BIN || 'opencode',
  repoDir,
  env = process.env,
  selectedSubject = null,
  pure = true,
  probe = true,
}) {
  const base = readNativeConfig({ opencodeBin, repoDir, env, pure });
  if (base.status !== 'completed') {
    return {
      status: 'failed',
      reason: 'native OpenCode config could not be resolved',
      inspection: base.inspection,
    };
  }
  try {
    const overlay = benchmarkOverlay(base.config, selectedSubject);
    const content = mergeObjects(inlineConfig(env), overlay.config);
    const commandEnv = {
      ...env,
      OPENCODE_CONFIG_CONTENT: JSON.stringify(content),
    };
    const effective = readNativeConfig({
      opencodeBin,
      repoDir,
      env: commandEnv,
      pure,
    });
    if (effective.status !== 'completed') {
      throw new Error('OpenCode rejected the composed benchmark configuration');
    }
    const effectiveInspection = verifyBenchmarkConfig(
      base.config,
      effective.config,
      overlay,
      selectedSubject,
    );
    if (probe && selectedSubject) {
      const connection = runCommand(
        opencodeBin,
        [...commandPrefix(pure), 'mcp', 'list'],
        { cwd: repoDir, env: commandEnv },
      );
      const connected = connection.stdout.split(/\r?\n/).some(
        (line) =>
          line.includes(selectedSubject) &&
          /connected/i.test(line),
      );
      if (connection.status !== 0 || !connected) {
        throw new Error(
          `native OpenCode MCP connection ${selectedSubject} is not connected`,
        );
      }
    }
    return {
      status: 'completed',
      inspection: base.inspection,
      effective_inspection: effectiveInspection,
      selected_server: overlay.selected,
      overlay_identity: {
        shape: overlay.shape,
        selected_subject: selectedSubject,
        native_server_reused: selectedSubject !== null,
      },
      environment: commandEnv,
    };
  } catch (error) {
    return {
      status: 'failed',
      reason: String(error.message || error),
      inspection: base.inspection,
    };
  }
}

function runSession({
  opencodeBin = process.env.OPENCODE_BIN || 'opencode',
  repoDir,
  agent = 'build',
  title,
  prompt,
  homeDir = '',
  env = {},
  pure = true,
}) {
  const startedAt = Date.now();
  const command = runCommand(
    opencodeBin,
    [
      ...commandPrefix(pure),
      'run',
      '--dir',
      repoDir,
      '--agent',
      agent,
      '--title',
      title,
      '--format',
      'json',
      prompt,
    ],
    {
      cwd: repoDir,
      env: effectiveEnv({ homeDir, env }),
    },
  );
  return { startedAt, command };
}

async function runSessionAndExport({
  opencodeBin = process.env.OPENCODE_BIN || 'opencode',
  repoDir,
  agent = 'build',
  title,
  prompt,
  env = {},
  deleteAfterExport = true,
  pure = true,
}) {
  const started = runSession({
    opencodeBin,
    repoDir,
    agent,
    title,
    prompt,
    env,
    pure,
  });
  const run = started.command;

  const sessionId = await findSessionId({
    opencodeBin,
    repoDir,
    title,
    startedAt: started.startedAt,
    env,
    pure,
  });
  let exported = null;
  let deleted = null;
  let finalText = null;
  let exportParseError = null;
  if (sessionId) {
    exported = exportSession({
      opencodeBin,
      repoDir,
      sessionId,
      env,
      pure,
    });
    if (exported.status === 0) {
      try {
        finalText = extractFinalAnswer(exported.stdout).text;
      } catch (error) {
        exportParseError = String(error.message || error);
      }
    }
    if (deleteAfterExport) {
      deleted = deleteSession({
        opencodeBin,
        repoDir,
        sessionId,
        env,
        pure,
      });
    }
  }

  return {
    schema: RUNTIME_SCHEMA,
    run,
    session_id: sessionId || null,
    export: exported,
    final_text: finalText,
    export_parse_error: exportParseError,
    delete: deleted,
  };
}

function parseCli(argv) {
  if (argv.length === 0) {
    throw new Error(
      'usage: opencode-runtime.js inspect-config|run-export ...',
    );
  }
  const command = argv[0];
  const options = {};
  for (let index = 1; index < argv.length; index += 1) {
    const arg = argv[index];
    if (!arg.startsWith('--')) {
      throw new Error(`unexpected positional argument: ${arg}`);
    }
    const key = arg.slice(2);
    index += 1;
    if (index >= argv.length) {
      throw new Error(`${arg} requires a value`);
    }
    options[key] = argv[index];
  }
  return { command, options };
}

async function main(argv) {
  const { command, options } = parseCli(argv);
  const repoDir = path.resolve(options.repo || process.cwd());
  const benchmarkMode = Object.hasOwn(options, 'benchmark-subject');
  const selectedSubject = benchmarkMode && options['benchmark-subject'] !== 'none'
    ? options['benchmark-subject']
    : null;
  if (command === 'inspect-config') {
    const result = benchmarkMode
      ? prepareBenchmarkConfig({
        repoDir,
        env: process.env,
        selectedSubject,
      })
      : resolveNativeConfig({ repoDir, env: process.env });
    const { environment, ...safe } = result;
    process.stdout.write(`${JSON.stringify({
      schema: RUNTIME_SCHEMA,
      ...safe,
    })}\n`);
    return;
  }

  if (command === 'run-export') {
    if (!options.title || !options['prompt-file']) {
      throw new Error(
        'run-export requires --title and --prompt-file',
      );
    }
    const prompt = fs.readFileSync(
      path.resolve(options['prompt-file']),
      'utf8',
    );
    let env = process.env;
    if (benchmarkMode) {
      const prepared = prepareBenchmarkConfig({
        repoDir,
        env: process.env,
        selectedSubject,
      });
      if (
        prepared.status !== 'completed' ||
        prepared.inspection.config_sha256 !==
          options['native-config-sha256']
      ) {
        process.stdout.write(`${JSON.stringify({
          schema: RUNTIME_SCHEMA,
          run: { status: 1 },
          error: prepared.reason || 'native OpenCode config changed after admission',
        })}\n`);
        return;
      }
      env = prepared.environment;
    }
    const result = await runSessionAndExport({
      repoDir,
      title: options.title,
      agent: options.agent || 'build',
      prompt,
      env,
      deleteAfterExport: options['keep-session'] !== 'true',
    });
    process.stdout.write(`${JSON.stringify(result)}\n`);
    return;
  }

  throw new Error(`unknown command: ${command}`);
}

module.exports = {
  RUNTIME_SCHEMA,
  canonicalJson,
  configuredModel,
  deleteSession,
  exportSession,
  extractFinalAnswer,
  findSessionId,
  inspectConfig,
  inlineConfig,
  mergeObjects,
  benchmarkOverlay,
  prepareBenchmarkConfig,
  providerFromModel,
  readJsonText,
  resolveNativeConfig,
  runCommand,
  runSession,
  runSessionAndExport,
  sanitize,
};

if (require.main === module) {
  main(process.argv.slice(2)).catch((error) => {
    process.stderr.write(
      `Error: ${error.stack || error.message || error}\n`,
    );
    process.exit(2);
  });
}
