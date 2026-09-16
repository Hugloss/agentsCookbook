#!/usr/bin/env node
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const repoRoot = path.resolve(path.dirname(fs.realpathSync(__filename)), '..');
const defaultCorpus = path.join(repoRoot, 'evals', 'sharp-skill-cases.json');
const specialistSections = new Set([
  'Concurrency',
  'Semantic authority',
  'Structural simplicity',
  'Test-derived architecture',
  'Discovery',
]);

function usage() {
  process.stdout.write(`Usage:
  scripts/run-skill-benchmarks.js --validate-corpus
  scripts/run-skill-benchmarks.js --list
  scripts/run-skill-benchmarks.js --runtime opencode|pi (--all | --skill NAME | --case ID) [options]

Options:
  --corpus FILE        Alternate corpus JSON.
  --repo DIR           Working repository for prompt-only cases.
  --artifacts-dir DIR  Persist output and result JSON per case.
  --model ID           Model override; defaults to SKILL_EVAL_MODEL.
  --skill NAME         Run every case for one skill; repeatable.
  --case ID            Run one case; repeatable.
  --all                Run every corpus case.
  --list               List cases without model execution.
  --validate-corpus    Validate ids, coverage, fixtures, and skill references.
`);
}

function parseArgs(argv) {
  const out = {
    runtime: '', all: false, skills: [], cases: [], repoDir: repoRoot,
    corpus: defaultCorpus, artifactsDir: '', model: process.env.SKILL_EVAL_MODEL || '',
    list: false, validateCorpus: false,
  };
  const take = (argvRef, indexRef, name) => {
    indexRef.value += 1;
    if (indexRef.value >= argvRef.length) throw new Error(`${name} requires a value`);
    return argvRef[indexRef.value];
  };
  const indexRef = { value: 0 };
  for (; indexRef.value < argv.length; indexRef.value += 1) {
    const arg = argv[indexRef.value];
    if (arg === '--runtime') out.runtime = take(argv, indexRef, arg);
    else if (arg === '--all') out.all = true;
    else if (arg === '--skill') out.skills.push(take(argv, indexRef, arg));
    else if (arg === '--case') out.cases.push(take(argv, indexRef, arg));
    else if (arg === '--repo') out.repoDir = path.resolve(take(argv, indexRef, arg));
    else if (arg === '--corpus') out.corpus = path.resolve(take(argv, indexRef, arg));
    else if (arg === '--artifacts-dir') out.artifactsDir = path.resolve(take(argv, indexRef, arg));
    else if (arg === '--model') out.model = take(argv, indexRef, arg);
    else if (arg === '--list') out.list = true;
    else if (arg === '--validate-corpus') out.validateCorpus = true;
    else if (arg === '--help' || arg === '-h') { usage(); process.exit(0); }
    else throw new Error(`Unknown option: ${arg}`);
  }
  return out;
}

function catalogSpecialists() {
  const lines = fs.readFileSync(path.join(repoRoot, 'skills', 'README.md'), 'utf8').split(/\r?\n/);
  const names = [];
  let active = false;
  for (const line of lines) {
    const heading = line.match(/^## (.+)$/);
    if (heading) { active = specialistSections.has(heading[1]); continue; }
    if (!active) continue;
    const bullet = line.match(/^- `([^`]+)` — /);
    if (bullet) names.push(bullet[1]);
  }
  return names;
}

function validateCorpus(corpus) {
  const errors = [];
  if (!corpus || corpus.schema_version !== 1 || !Array.isArray(corpus.cases)) {
    return ['corpus must contain schema_version=1 and a cases array'];
  }
  const specialists = new Set(catalogSpecialists());
  const ids = new Set();
  const coverage = new Map();
  for (const item of corpus.cases) {
    if (!item || typeof item !== 'object') { errors.push('case entry must be an object'); continue; }
    if (!item.id || typeof item.id !== 'string') errors.push('case missing string id');
    else if (ids.has(item.id)) errors.push(`duplicate case id: ${item.id}`);
    else ids.add(item.id);
    if (!item.skill || !specialists.has(item.skill)) errors.push(`${item.id || '<unknown>'}: unknown specialist ${item.skill || '<missing>'}`);
    else {
      const file = path.join(repoRoot, 'skills', item.skill, 'SKILL.md');
      if (!fs.existsSync(file)) errors.push(`${item.id}: missing ${file}`);
      const kinds = coverage.get(item.skill) || new Set();
      kinds.add(item.kind); coverage.set(item.skill, kinds);
    }
    if (!['positive', 'control', 'confusion'].includes(item.kind)) errors.push(`${item.id}: invalid kind ${item.kind}`);
    if (!['FINDING', 'CLEAN'].includes(item.expected)) errors.push(`${item.id}: expected must be FINDING or CLEAN`);
    if (!item.scenario || typeof item.scenario !== 'string') errors.push(`${item.id}: missing scenario`);
    if (item.fixture) {
      const fixture = path.resolve(repoRoot, item.fixture);
      if (!fixture.startsWith(`${repoRoot}${path.sep}`) || !fs.existsSync(fixture)) errors.push(`${item.id}: invalid fixture ${item.fixture}`);
    }
  }
  for (const skill of specialists) {
    const kinds = coverage.get(skill) || new Set();
    if (!kinds.has('positive')) errors.push(`${skill}: missing positive case`);
    if (!kinds.has('control')) errors.push(`${skill}: missing control case`);
  }
  return errors;
}

function selectedCases(corpus, options) {
  if (options.all) return corpus.cases;
  const skills = new Set(options.skills), cases = new Set(options.cases);
  if (skills.size === 0 && cases.size === 0) throw new Error('Choose --all, --skill NAME, or --case ID.');
  for (const skill of skills) if (!corpus.cases.some((x) => x.skill === skill)) throw new Error(`Unknown skill in corpus: ${skill}`);
  for (const id of cases) if (!corpus.cases.some((x) => x.id === id)) throw new Error(`Unknown case id: ${id}`);
  return corpus.cases.filter((x) => skills.has(x.skill) || cases.has(x.id));
}

function ensureDir(dir) { fs.mkdirSync(dir, { recursive: true }); }

function evaluatorSystem(skillText, skillName) {
  return `${skillText}\n\n# Behavioral evaluation overlay\n\nApply only the invariant owned by \`${skillName}\`.\nDo not manufacture a finding because this is an evaluation.\nDo not claim a neighboring specialist's defect as this skill's finding.\nUse repository evidence when a fixture is supplied.\nAfter the normal skill-defined review append exactly:\n\nEVAL_VERDICT: FINDING|CLEAN\nEVAL_SCOPE: ${skillName}|NONE\nEVAL_EVIDENCE: <one concise evidence statement>\n\nUse FINDING only when this skill's own invariant is violated. Use CLEAN when the scenario is safe or belongs to another specialist.`;
}

function casePrompt(item) {
  const source = item.fixture
    ? 'Inspect the files in the current working directory; they are the complete fixture for this case.'
    : 'The scenario below is the complete evidence for this bounded case.';
  return `Evaluate this case using the loaded specialist skill.\n\nCASE ID: ${item.id}\n${source}\n\nSCENARIO:\n${item.scenario}\n\nDo not infer the expected answer from case metadata. Follow the skill invariant and false-positive controls.`;
}

function run(command, args, cwd, env) {
  const started = process.hrtime.bigint();
  const result = spawnSync(command, args, { cwd, env, encoding: 'utf8', maxBuffer: 50 * 1024 * 1024 });
  return {
    status: typeof result.status === 'number' ? result.status : 1,
    stdout: result.stdout || '', stderr: result.stderr || '',
    error: result.error ? String(result.error.message || result.error) : '',
    elapsedMs: Math.round(Number(process.hrtime.bigint() - started) / 1e6),
  };
}

function runPi(systemPrompt, prompt, cwd, model) {
  const args = ['--tools', 'read,grep,find,ls', '--system-prompt', systemPrompt];
  if (model) args.push('--model', model);
  args.push('-p', prompt);
  return run(process.env.PI_BIN || 'pi', args, cwd, process.env);
}

function copyOpenCodeConfig(tempHome) {
  const source = process.env.XDG_CONFIG_HOME ? path.join(process.env.XDG_CONFIG_HOME, 'opencode')
    : process.env.HOME ? path.join(process.env.HOME, '.config', 'opencode') : '';
  const target = path.join(tempHome, '.config', 'opencode');
  ensureDir(target);
  if (source && fs.existsSync(source)) fs.cpSync(source, target, { recursive: true, force: false, errorOnExist: false });
  return target;
}

function openCodeAgent(systemPrompt, model) {
  return `---\ndescription: Read-only behavioral evaluator for one canonical cookbook skill.\nname: skill-benchmark\nmode: primary\ntemperature: 0.1\n${model ? `model: ${model}\n` : ''}permission:\n  "*": deny\n  read: allow\n  grep: allow\n  glob: allow\n  list: allow\n  find: allow\n  ls: allow\n---\n\n${systemPrompt}\n`;
}

function runOpenCode(systemPrompt, prompt, cwd, model) {
  const tempHome = fs.mkdtempSync(path.join(os.tmpdir(), 'agents-cookbook-skill-eval-'));
  try {
    const configDir = copyOpenCodeConfig(tempHome);
    const agentDir = path.join(configDir, 'agents'); ensureDir(agentDir);
    fs.writeFileSync(path.join(agentDir, 'skill-benchmark.md'), openCodeAgent(systemPrompt, model));
    const env = { ...process.env, HOME: tempHome, XDG_CONFIG_HOME: path.join(tempHome, '.config') };
    return run(process.env.OPENCODE_BIN || 'opencode', ['run', '--dir', cwd, '--agent', 'skill-benchmark', prompt], cwd, env);
  } finally { fs.rmSync(tempHome, { recursive: true, force: true }); }
}

function parseResult(output) {
  const verdict = output.match(/^EVAL_VERDICT:\s*(FINDING|CLEAN)\s*$/mi);
  const scope = output.match(/^EVAL_SCOPE:\s*([A-Za-z0-9_-]+|NONE)\s*$/mi);
  const evidence = output.match(/^EVAL_EVIDENCE:\s*(.+)\s*$/mi);
  return { verdict: verdict ? verdict[1].toUpperCase() : '', scope: scope ? scope[1] : '', evidence: evidence ? evidence[1].trim() : '' };
}

function persist(result, base) {
  if (!base) return;
  const dir = path.join(base, result.runtime, result.id); ensureDir(dir);
  fs.writeFileSync(path.join(dir, 'stdout.txt'), result.stdout);
  fs.writeFileSync(path.join(dir, 'stderr.txt'), result.stderr);
  const copy = { ...result }; delete copy.stdout; delete copy.stderr;
  fs.writeFileSync(path.join(dir, 'result.json'), `${JSON.stringify(copy, null, 2)}\n`);
}

function executeCase(item, options) {
  const skillText = fs.readFileSync(path.join(repoRoot, 'skills', item.skill, 'SKILL.md'), 'utf8');
  const systemPrompt = evaluatorSystem(skillText, item.skill), prompt = casePrompt(item);
  const cwd = item.fixture ? path.resolve(repoRoot, item.fixture) : options.repoDir;
  const execution = options.runtime === 'pi' ? runPi(systemPrompt, prompt, cwd, options.model) : runOpenCode(systemPrompt, prompt, cwd, options.model);
  const parsed = parseResult(execution.stdout), expectedScope = item.expected === 'FINDING' ? item.skill : 'NONE';
  const pass = execution.status === 0 && parsed.verdict === item.expected && parsed.scope === expectedScope && parsed.evidence.length > 0;
  return { id: item.id, skill: item.skill, kind: item.kind, runtime: options.runtime, model: options.model || null,
    expected: item.expected, expectedScope, status: pass ? 'pass' : 'fail', exitCode: execution.status,
    elapsedMs: execution.elapsedMs, outputChars: execution.stdout.length, verdict: parsed.verdict || null,
    scope: parsed.scope || null, evidence: parsed.evidence || null, error: execution.error || null,
    stdout: execution.stdout, stderr: execution.stderr };
}

function main() {
  let options;
  try { options = parseArgs(process.argv.slice(2)); }
  catch (error) { process.stderr.write(`Error: ${error.message}\n`); usage(); process.exit(2); }
  const corpus = JSON.parse(fs.readFileSync(options.corpus, 'utf8'));
  const errors = validateCorpus(corpus);
  if (errors.length) { for (const error of errors) process.stderr.write(`CORPUS_ERROR ${error}\n`); process.exit(1); }
  if (options.validateCorpus) { process.stdout.write(`SUMMARY status=pass cases=${corpus.cases.length} specialists=${catalogSpecialists().length}\n`); return; }
  if (options.list) { for (const item of corpus.cases) process.stdout.write(`CASE id=${item.id} skill=${item.skill} kind=${item.kind} expected=${item.expected} fixture=${item.fixture || 'none'}\n`); return; }
  if (!['opencode', 'pi'].includes(options.runtime)) { process.stderr.write('Error: --runtime must be opencode or pi.\n'); process.exit(2); }
  const cases = selectedCases(corpus, options); if (options.artifactsDir) ensureDir(options.artifactsDir);
  const results = [];
  for (const item of cases) {
    process.stdout.write(`CASE id=${item.id} skill=${item.skill} runtime=${options.runtime} status=running\n`);
    const result = executeCase(item, options); persist(result, options.artifactsDir); results.push(result);
    process.stdout.write(`CASE id=${result.id} skill=${result.skill} runtime=${result.runtime} status=${result.status} expected=${result.expected} verdict=${result.verdict || 'missing'} scope=${result.scope || 'missing'} elapsed_ms=${result.elapsedMs} output_chars=${result.outputChars}\n`);
  }
  const passed = results.filter((x) => x.status === 'pass').length, failed = results.length - passed;
  process.stdout.write(`SUMMARY status=${failed ? 'fail' : 'pass'} runtime=${options.runtime} cases=${results.length} passed=${passed} failed=${failed}\n`);
  if (failed) process.exitCode = 1;
}

main();
