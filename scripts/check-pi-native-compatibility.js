#!/usr/bin/env node
'use strict';

// Optional model-free check against explicitly supplied, locally installed host
// packages. It never downloads packages, launches a child Pi, or calls a model.
const assert = require('assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { pathToFileURL } = require('url');

const repoRoot = path.resolve(__dirname, '..');

function optionsFrom(argv) {
  const options = {};
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === '--help' || argv[i] === '-h') return { help: true };
    if (!['--pi-package', '--open-agents-package'].includes(argv[i]) || !argv[i + 1] || argv[i + 1].startsWith('--')) {
      throw new Error('Expected --pi-package DIR --open-agents-package DIR');
    }
    options[argv[i].slice(2)] = path.resolve(argv[++i]);
  }
  if (!options['pi-package'] || !options['open-agents-package']) throw new Error('Both package directories are required');
  return options;
}

async function main() {
  const options = optionsFrom(process.argv.slice(2));
  if (options.help) {
    process.stdout.write('Usage: scripts/check-pi-native-compatibility.js --pi-package DIR --open-agents-package DIR\n\nRun model-free loading, native permission/delegation, and skill-read checks against installed packages.\nNo install, user configuration changes, subprocesses, or model requests.\n');
    return;
  }
  const piRoot = options['pi-package'];
  const agentsRoot = options['open-agents-package'];
  const piPackage = JSON.parse(fs.readFileSync(path.join(piRoot, 'package.json'), 'utf8'));
  const agentsPackage = JSON.parse(fs.readFileSync(path.join(agentsRoot, 'package.json'), 'utf8'));
  assert.equal(piPackage.name, '@earendil-works/pi-coding-agent', 'expected the current Pi npm package identity');
  assert.equal(agentsPackage.name, 'pi-open-agents');
  const { loadExtensions } = await import(pathToFileURL(path.join(piRoot, 'dist/core/extensions/loader.js')).href);
  const { createReadTool, SessionManager } = await import(pathToFileURL(path.join(piRoot, 'dist/index.js')).href);
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'cookbook-pi-native-'));
  const envKeys = ['PI_OPEN_AGENTS_DEPTH', 'PI_OPEN_AGENTS_NAME', 'AGENTS_COOKBOOK_RUN_DIR'];
  const savedEnv = Object.fromEntries(envKeys.map((key) => [key, process.env[key]]));
  let failures = 0;
  async function check(name, action) {
    try {
      await action();
      process.stdout.write(`CHECK name=${name} status=pass\n`);
    } catch (error) {
      failures += 1;
      process.stdout.write(`CHECK name=${name} status=fail reason=${JSON.stringify(error.message || String(error))}\n`);
    }
  }
  try {
    // Import actual extension source through Pi's own loader and peer aliases.
    // A command closure exposes helpers only to this in-process test harness.
    const imports = {
      schema: 'config/schema.ts', parser: 'permission/parser.ts', gate: 'permission/gate.ts',
      subagent: 'subagent/tool.ts', env: 'subagent/env.ts', executor: 'subagent/executor.ts',
      discovery: 'discovery/loader.ts',
    };
    const probePath = path.join(scratch, 'probe.ts');
    const source = Object.entries(imports).map(([name, relative]) =>
      `import * as ${name} from ${JSON.stringify(pathToFileURL(path.join(agentsRoot, 'src', relative)).href)};`).join('\n');
    fs.writeFileSync(probePath, `${source}\nexport default function(pi) { pi.registerCommand('cookbook-native-probe', { handler: async () => ({ ${Object.keys(imports).join(', ')} }) }); }\n`);
    const probe = await loadExtensions([probePath, path.join(agentsRoot, 'index.ts')], scratch);
    assert.deepEqual(probe.errors, [], 'native source or extension factory could not load');
    const native = await probe.extensions[0].commands.get('cookbook-native-probe').handler();
    const reviewerNames = JSON.parse(fs.readFileSync(path.join(repoRoot, 'reviewers.json'), 'utf8'));
    const agents = fs.readdirSync(path.join(repoRoot, 'agents')).filter((file) => file.endsWith('.md')).map((file) => {
      const absolute = path.join(repoRoot, 'agents', file);
      return native.schema.parseAgentDefinition(fs.readFileSync(absolute, 'utf8'), absolute, 'global');
    });
    const reviewers = agents.filter((agent) => reviewerNames.includes(agent.name));
    const primaries = agents.filter((agent) => agent.mode === 'primary');
    assert.equal(reviewers.length, 9);
    assert.equal(primaries.length, 3);
    const baseTools = ['read', 'grep', 'find', 'ls'];
    const runRoot = path.join(scratch, 'run');

    async function loadAdapter(reviewer) {
      process.env.PI_OPEN_AGENTS_DEPTH = reviewer ? '1' : '0';
      process.env.PI_OPEN_AGENTS_NAME = reviewer || '';
      process.env.AGENTS_COOKBOOK_RUN_DIR = runRoot;
      const loaded = await loadExtensions([path.join(repoRoot, 'adapters/pi/index.js')], scratch);
      assert.deepEqual(loaded.errors, []);
      assert.equal(loaded.extensions.length, 1);
      let active = [];
      // Bind only after the actual loader has completed factory registration.
      loaded.runtime.setActiveTools = (names) => { active = [...names]; };
      const extension = loaded.extensions[0];
      for (const handler of extension.handlers.get('session_start') || []) await handler({ type: 'session_start', reason: 'new' }, {});
      assert.deepEqual(active, reviewer ? [...baseTools, 'review_artifact'] : []);
      return extension;
    }

    await check('pi_native_extension_lifecycle', async () => {
      const child = await loadAdapter(reviewers[0].name);
      assert.deepEqual([...child.tools.keys()], ['review_artifact']);
      const gate = child.handlers.get('tool_call')[0];
      assert.equal((await gate({ toolName: 'bash' }, {})).block, true);
      assert.equal(await gate({ toolName: 'read' }, {}), undefined);
    });

    await check('pi_native_fork_link', async () => {
      const cwd = process.cwd();
      const parent = SessionManager.create(cwd, path.join(scratch, 'parent-sessions'));
      const leaf = parent.appendMessage({ role: 'user', content: 'Model-free parent fixture.', timestamp: Date.now() });
      const parentFile = parent.getSessionFile();
      const fork = native.executor.resolveSubagentSession('fork', cwd, parentFile, leaf, path.join(scratch, 'agent'));
      assert.equal(fork.effective, 'fork', fork.warning);
      assert.ok(path.isAbsolute(fork.file) && fs.existsSync(fork.file));
      assert.equal(SessionManager.open(fork.file).getHeader().parentSession, parentFile);
    });

    for (const parent of primaries) {
      await check(`pi_native_delegation_${parent.name}`, async () => {
        assert.deepEqual([...parent.allowedAgents].sort(), [...reviewerNames].sort());
        assert.equal(parent.maxDepth, 1);
        const parentRules = native.parser.parsePermissionRules(parent.permission);
        assert.equal(native.gate.decideToolCall('subagent', { agent: reviewers[0].name }, parentRules).action, 'allow', 'native subagent permission is missing');
        const tools = new Map();
        let invocation;
        const foreignAgent = { ...reviewers[0], name: 'outside-cookbook-allowlist' };
        native.subagent.registerSubagentTool({
          registerTool(tool) { tools.set(tool.name, tool); },
          getActiveTools() { return [...baseTools, 'subagent', 'review_artifact_read']; },
        }, {
          agents: [...reviewers, foreignAgent],
          getActiveAgent: () => parent,
          env: {}, agentDir: path.join(scratch, 'agent'),
          // Native dependency injection replaces only child process execution.
          run: async (options) => {
            invocation = options;
            return { agent: options.agent.name, status: 'done', output: 'harness only', tools: [], isError: false };
          },
        });
        const delegate = tools.get('subagent').execute;
        const ctx = { cwd: scratch, hasUI: false };
        await assert.rejects(() => delegate('bad', { agent: foreignAgent.name, task: 'review' }, undefined, undefined, ctx), /can only delegate/);
        for (const reviewer of reviewers) {
          await delegate('allowed', { agent: reviewer.name, task: 'review' }, undefined, undefined, ctx);
          assert.equal(invocation.agent.name, reviewer.name);
          assert.equal(invocation.depth, 1);
          if (invocation.parentCeiling !== undefined) {
            assert.ok(invocation.parentCeiling.includes('read'), 'native parent ceiling removed explicitly allowed read');
            assert.ok(invocation.parentCeiling.includes('review_artifact'), 'native parent ceiling excludes the child-only artifact sink');
          }
          const handlers = new Map();
          native.gate.registerPermissionGate({ on(event, handler) { handlers.set(event, handler); } }, {
            resolveAgent: () => reviewer,
            inheritedRules: () => invocation.parentRules || [],
          });
          const skillPath = path.join(repoRoot, 'skills', reviewer.skills[0], 'SKILL.md');
          const readGate = await handlers.get('tool_call')({ toolName: 'read', input: { path: skillPath } }, ctx);
          assert.equal(readGate, undefined, 'native permission inheritance blocked the declared skill read');
          assert.equal(await handlers.get('tool_call')({ toolName: 'review_artifact', input: { artifact_id: reviewer.name } }, ctx), undefined);
          assert.equal((await handlers.get('tool_call')({ toolName: 'bash', input: { command: 'false' } }, ctx)).block, true);
          const childTools = new Map();
          native.subagent.registerSubagentTool({ registerTool(tool) { childTools.set(tool.name, tool); } }, {
            agents: reviewers,
            env: { PI_OPEN_AGENTS_DEPTH: '1', PI_OPEN_AGENTS_MAX_DEPTH: String(reviewer.maxDepth) },
          });
          assert.equal(reviewer.maxDepth, 0);
          assert.equal(childTools.has('subagent'), false, 'native reviewer depth cap must prevent delegation');
        }
      });
    }

    await check('pi_native_skill_read_and_artifact', async () => {
      const reviewer = reviewers[0];
      const skillPath = path.join(repoRoot, 'skills', reviewer.skills[0], 'SKILL.md');
      const readResult = await createReadTool(repoRoot).execute('skill', { path: skillPath }, undefined, undefined);
      assert.ok(readResult.content.some((item) => item.type === 'text' && item.text.includes(`name: ${reviewer.skills[0]}`)));
      const child = await loadAdapter(reviewer.name);
      const write = child.tools.get('review_artifact').definition.execute;
      const saved = await write('artifact', { artifact_id: reviewer.name, summary: 'Native adapter check.', content: '# Native adapter check' });
      assert.equal(saved.details.reviewer, reviewer.name);
      const primary = await loadAdapter('');
      const read = primary.tools.get('review_artifact_read').definition.execute;
      assert.equal((await read('read', { artifact_id: reviewer.name })).content[0].text, '# Native adapter check\n');
    });
    process.stdout.write(`SUMMARY status=${failures ? 'fail' : 'pass'} pi=${piPackage.version} pi_open_agents=${agentsPackage.version} evidence=native_loader_and_helpers child_execution=capture_function model_calls=0 child_processes=0 failures=${failures}\n`);
    if (failures) process.exitCode = 1;
  } finally {
    for (const [key, value] of Object.entries(savedEnv)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    fs.rmSync(scratch, { recursive: true, force: true });
  }
}

main().catch((error) => {
  process.stderr.write(`CHECK name=pi_native_compatibility status=fail error=${JSON.stringify(error.message || String(error))}\n`);
  process.exitCode = 1;
});
