'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { supportedOpenAgents, inspectPackage, agentCollisions } = require('./check-pi-installation.js');

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'cookbook-pi-installation-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const agentDir = path.join(root, 'pi agent');
  const cwd = path.join(root, 'target repo');
  const sourceDir = path.join(root, 'source');
  for (const dir of [agentDir, cwd, sourceDir]) fs.mkdirSync(dir, { recursive: true });
  function write(file, content) {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, content);
  }
  function install(base, version = '0.1.26', declaration = `npm:pi-open-agents@${version}`) {
    write(path.join(base, 'settings.json'), JSON.stringify({ packages: [declaration] }));
    write(path.join(base, 'npm/node_modules/pi-open-agents/package.json'), JSON.stringify({ name: 'pi-open-agents', version }));
  }
  return { root, agentDir, cwd, sourceDir, write, install };
}

test('version gate accepts the checked extension and rejects untested, known incompatible, and prerelease extensions', () => {
  assert.equal(supportedOpenAgents('0.1.26'), true);
  for (const value of ['0.1.19', '0.1.20', '0.1.25', '0.1.27', '0.1.28', '1.0.0', '0.1.26-beta.1', '0.1.260', '']) assert.equal(supportedOpenAgents(value), false);
});

test('native packages string and enabled object declarations pass; local extension strings do not masquerade as packages', (t) => {
  const f = fixture(t);
  for (const declaration of ['npm:pi-open-agents@0.1.26', { source: 'npm:pi-open-agents@0.1.26' }, { source: 'npm:pi-open-agents@0.1.26', extensions: ['./index.ts'] }]) {
    f.install(f.agentDir, '0.1.26', declaration);
    assert.equal(inspectPackage(f.agentDir, f.cwd).version, '0.1.26');
  }
  f.write(path.join(f.agentDir, 'settings.json'), JSON.stringify({ extensions: ['npm:pi-open-agents@0.1.26'] }));
  assert.throws(() => inspectPackage(f.agentDir, f.cwd), /not declared in settings.packages/);
});

test('disabled/unknown package filters and inconsistent pins fail instead of claiming enabled', (t) => {
  const f = fixture(t);
  for (const filter of [{ extensions: [] }, { extensions: ['!index.ts'] }, { autoload: false }, { extensions: ['unrelated.ts'] }]) {
    f.install(f.agentDir, '0.1.26', { source: 'npm:pi-open-agents@0.1.26', ...filter });
    assert.throws(() => inspectPackage(f.agentDir, f.cwd), /qualification|entry point/);
  }
  f.install(f.agentDir, '0.1.26', 'npm:pi-open-agents@0.1.27');
  assert.throws(() => inspectPackage(f.agentDir, f.cwd), /differs from installed/);
});

test('project package precedence cannot hide a missing or incompatible active package behind a valid user install', (t) => {
  const f = fixture(t);
  f.install(f.agentDir);
  const projectBase = path.join(f.cwd, '.pi');
  f.install(projectBase, '0.1.27');
  assert.throws(() => inspectPackage(f.agentDir, f.cwd), /native inherited wildcard deny/);
  f.install(projectBase, '0.1.26');
  assert.equal(inspectPackage(f.agentDir, f.cwd).scope, 'project');
  fs.unlinkSync(path.join(projectBase, 'npm/node_modules/pi-open-agents/package.json'));
  assert.throws(() => inspectPackage(f.agentDir, f.cwd), /ENOENT/);
});

test('current native discovery finds every project family, nested flattened names, and explicit frontmatter aliases', (t) => {
  const f = fixture(t);
  const name = 'plan-improver-model2';
  const canonical = path.join(f.sourceDir, `${name}.md`);
  f.write(canonical, `---\nname: ${name}\n---\nCanonical`);
  const roots = ['.pi/agents', '.opencode/agent', '.opencode/agents', '.opencode/mode', '.opencode/modes', '.agents/agents'];
  for (const relative of roots) {
    const candidate = path.join(f.cwd, relative, 'different/nested-name.md');
    f.write(candidate, `---\n"name": '${name}'\n---\nOverride`);
    const collisions = agentCollisions(f.agentDir, f.cwd, f.sourceDir);
    assert.equal(collisions.length, 1, relative);
    assert.equal(collisions[0].file, candidate);
    fs.unlinkSync(candidate);
  }
  const flattened = path.join(f.cwd, '.opencode/agents/plan/improver-model2.md');
  f.write(flattened, 'A filename-derived identity.');
  assert.equal(agentCollisions(f.agentDir, f.cwd, f.sourceDir).length, 1);
  fs.unlinkSync(flattened);
  const coerced = path.join(f.cwd, '.pi/agents/array-name.md');
  // The native schema string-coerces this parsed single-element YAML array.
  f.write(coerced, `---\nname: ['${name}']\n---\nOverride`);
  assert.equal(agentCollisions(f.agentDir, f.cwd, f.sourceDir).length, 1);
});

test('canonical links, disabled definitions, and obsolete loose shared files do not cause current false shadows', (t) => {
  const f = fixture(t);
  const name = 'plan-improver-model2';
  const canonical = path.join(f.sourceDir, `${name}.md`);
  f.write(canonical, `---\nname: ${name}\n---\nCanonical`);
  const installed = path.join(f.agentDir, 'agents', `${name}.md`);
  fs.mkdirSync(path.dirname(installed), { recursive: true });
  fs.symlinkSync(canonical, installed);
  f.write(path.join(f.cwd, '.agents', `${name}.md`), 'Legacy override');
  f.write(path.join(f.cwd, '.pi/agents/disabled.md'), `---\nname: ${name}\ndisable: true\n---\nDisabled`);
  assert.deepEqual(agentCollisions(f.agentDir, f.cwd, f.sourceDir), []);
  f.write(path.join(f.agentDir, 'agents/z-alias.md'), `---\nname: ${name}\n---\nGlobal Pi override`);
  assert.equal(agentCollisions(f.agentDir, f.cwd, f.sourceDir).length, 1);
});
