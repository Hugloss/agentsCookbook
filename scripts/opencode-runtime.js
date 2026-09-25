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
  const result = spawnSync(command, args, {
    cwd: options.cwd || process.cwd(),
    env: { ...process.env, ...(options.env || {}) },
    encoding: 'utf8',
    maxBuffer: options.maxBuffer || 50 * 1024 * 1024,
  });

  return {
    status: typeof result.status === 'number' ? result.status : 1,
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
}) {
  const commandEnv = effectiveEnv({ homeDir, env });
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    const sessionList = runCommand(
      opencodeBin,
      ['--pure', 'session', 'list', '--format', 'json', '--max-count', '20'],
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
}) {
  return runCommand(
    opencodeBin,
    ['--pure', 'export', sessionId],
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
}) {
  return runCommand(
    opencodeBin,
    ['--pure', 'session', 'delete', sessionId],
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
}) {
  const command = runCommand(
    opencodeBin,
    ['--pure', 'debug', 'config'],
    { cwd: repoDir, env },
  );
  if (command.status !== 0) {
    return {
      status: 'failed',
      command,
      inspection: null,
    };
  }
  try {
    const config = readJsonText(
      command.stdout,
      'opencode debug config',
    );
    return {
      status: 'completed',
      command,
      inspection: inspectConfig(config),
    };
  } catch (error) {
    return {
      status: 'failed',
      command,
      inspection: null,
      parse_error: String(error.message || error),
    };
  }
}

async function runSessionAndExport({
  opencodeBin = process.env.OPENCODE_BIN || 'opencode',
  repoDir,
  agent = 'build',
  title,
  prompt,
  env = {},
  deleteAfterExport = true,
}) {
  const startedAt = Date.now();
  const run = runCommand(
    opencodeBin,
    [
      '--pure',
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
    { cwd: repoDir, env },
  );

  const sessionId = await findSessionId({
    opencodeBin,
    repoDir,
    title,
    startedAt,
    env,
  });
  let exported = null;
  let deleted = null;
  if (sessionId) {
    exported = exportSession({
      opencodeBin,
      repoDir,
      sessionId,
      env,
    });
    if (deleteAfterExport) {
      deleted = deleteSession({
        opencodeBin,
        repoDir,
        sessionId,
        env,
      });
    }
  }

  return {
    schema: RUNTIME_SCHEMA,
    run,
    session_id: sessionId || null,
    export: exported,
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
  if (command === 'inspect-config') {
    const result = resolveNativeConfig({ repoDir, env: process.env });
    process.stdout.write(`${JSON.stringify({
      schema: RUNTIME_SCHEMA,
      ...result,
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
    const result = await runSessionAndExport({
      repoDir,
      title: options.title,
      agent: options.agent || 'build',
      prompt,
      env: process.env,
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
  providerFromModel,
  readJsonText,
  resolveNativeConfig,
  runCommand,
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
