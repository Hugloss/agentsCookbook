#!/usr/bin/env node
'use strict';

// Static checks for the cookbook's npm-based Pi installation. Pi remains the
// authority for package/resource resolution; nonstandard filters are reported
// as unverified rather than silently treated as loaded extensions.
const fs = require('fs');
const path = require('path');

function supportedOpenAgents(version) {
  return version === '0.1.26';
}

function readSettings(file) {
  if (!fs.existsSync(file)) return {};
  const value = JSON.parse(fs.readFileSync(file, 'utf8'));
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`invalid settings object: ${file}`);
  return value;
}

function inspectPackage(agentDir, cwd) {
  const scopes = [
    { scope: 'project', base: path.join(cwd, '.pi') },
    { scope: 'user', base: agentDir },
  ];
  let selected;
  for (const entry of scopes) {
    const settingsPath = path.join(entry.base, 'settings.json');
    const settings = readSettings(settingsPath);
    for (const declaration of Array.isArray(settings.packages) ? settings.packages : []) {
      const source = typeof declaration === 'string' ? declaration : declaration?.source;
      if (typeof source !== 'string' || !/^npm:pi-open-agents(?:@[^\s]+)?$/.test(source)) continue;
      selected = { ...entry, declaration, source, settingsPath };
      break;
    }
    if (selected) break; // Native package identity precedence: project > user.
  }
  if (!selected) throw new Error('pi-open-agents is not declared in settings.packages; npm strings in settings.extensions are not package declarations; use the native pi install npm:pi-open-agents@0.1.26 command');
  const { declaration, source, base } = selected;
  if (typeof declaration === 'object') {
    if (declaration.autoload === false) throw new Error('pi-open-agents autoload delta requires native resource qualification; static preflight cannot prove the extension is enabled');
    if (declaration.extensions !== undefined
        && !(Array.isArray(declaration.extensions) && declaration.extensions.length === 1 && ['index.ts', './index.ts'].includes(declaration.extensions[0]))) {
      throw new Error('pi-open-agents extension filter disables or changes the package entry point; verify the effective extension with native Pi resource resolution');
    }
  }
  const packageFile = path.join(base, 'npm', 'node_modules', 'pi-open-agents', 'package.json');
  const installed = JSON.parse(fs.readFileSync(packageFile, 'utf8'));
  if (installed.name !== 'pi-open-agents') throw new Error(`unexpected package identity in ${packageFile}`);
  const version = String(installed.version || '');
  if (!supportedOpenAgents(version)) {
    const reason = version === '0.1.27'
      ? 'native inherited wildcard deny removes explicitly allowed child tools and blocks the child-only artifact sink'
      : 'version has no reviewed full-flow compatibility result';
    throw new Error(`pi-open-agents ${version || 'unknown'} is not accepted for full-flow preflight: ${reason}; checked extension=0.1.26 with Pi=1.4.0; review the native delegation contract before qualifying another version`);
  }
  const pinned = /^npm:pi-open-agents@(\d+\.\d+\.\d+)$/.exec(source)?.[1];
  if (pinned && pinned !== version) throw new Error(`declared pi-open-agents ${pinned} differs from installed ${version}; reconcile the native package installation`);
  return { version, source, scope: selected.scope, settingsPath: selected.settingsPath, packageFile };
}

function listMarkdown(dir) {
  if (!fs.existsSync(dir)) return [];
  const result = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const absolute = path.join(dir, entry.name);
    if (entry.isDirectory()) result.push(...listMarkdown(absolute));
    else if ((entry.isFile() || entry.isSymbolicLink()) && entry.name.endsWith('.md')) result.push(absolute);
  }
  return result.sort();
}

function discoveryIdentity(content, relative) {
  // pi-open-agents' own small frontmatter parser accepts scalar names (including
  // quoted keys/values) and uses the flattened relative filename as fallback.
  // Do not interpret names appearing in Markdown bodies or nested permissions.
  const normalized = content.replace(/\r\n?/g, '\n');
  let name;
  let disabled = false;
  function scalar(value) {
    if (value.startsWith('[') && value.endsWith(']')) {
      const inner = value.slice(1, -1).trim();
      return inner ? inner.split(',').map((item) => scalar(item.trim())) : [];
    }
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) return value.slice(1, -1);
    return value;
  }
  if (normalized.startsWith('---\n')) {
    const end = normalized.indexOf('\n---', 3);
    if (end !== -1) {
      for (const line of normalized.slice(4, end).split('\n')) {
        const match = /^(?:"(name|disable)"|'(name|disable)'|(name|disable)):\s*(.*)$/.exec(line);
        if (!match) continue;
        const key = match[1] || match[2] || match[3];
        const value = scalar(match[4].trim());
        if (key === 'name') name = String(value).trim() || undefined;
        else disabled = value === 'true';
      }
    }
  }
  return { name: name || relative.replace(/\.md$/, '').replace(/[/\\]/g, '-'), disabled };
}

function agentCollisions(agentDir, cwd, sourceDir) {
  const canonical = new Map(fs.readdirSync(sourceDir).filter((name) => name.endsWith('.md'))
    .map((name) => [name.slice(0, -3), fs.realpathSync(path.join(sourceDir, name))]));
  // Global OpenCode families cannot override the canonical global Pi family
  // (native family rank Pi=2, OpenCode=1). All project families can override it.
  const roots = [
    path.join(agentDir, 'agents'), path.join(cwd, '.pi', 'agents'),
    ...['agent', 'agents', 'mode', 'modes'].map((name) => path.join(cwd, '.opencode', name)),
    path.join(cwd, '.agents', 'agents'),
  ];
  const collisions = [];
  for (const root of roots) {
    for (const file of listMarkdown(root)) {
      const identity = discoveryIdentity(fs.readFileSync(file, 'utf8'), path.relative(root, file));
      if (identity.disabled || !canonical.has(identity.name)) continue;
      if (fs.realpathSync(file) !== canonical.get(identity.name)) collisions.push({ name: identity.name, file, canonical: canonical.get(identity.name) });
    }
  }
  return collisions;
}

function main(argv) {
  if (argv.length !== 3) throw new Error('Usage: check-pi-installation.js PI_AGENT_DIR TARGET_REPO CANONICAL_AGENT_DIR');
  const [agentDir, cwd, sourceDir] = argv.map((value) => path.resolve(value));
  let failures = 0;
  let version = '';
  try {
    const installed = inspectPackage(agentDir, cwd);
    version = installed.version;
    process.stdout.write(`CHECK name=pi_open_agents_package status=pass version=${version} scope=${installed.scope} source=${JSON.stringify(installed.source)} settings=${JSON.stringify(installed.settingsPath)} evidence=static_installation\n`);
  } catch (error) {
    failures += 1;
    process.stdout.write(`CHECK name=pi_open_agents_package status=fail reason=${JSON.stringify(error.message)}\n`);
  }
  const collisions = agentCollisions(agentDir, cwd, sourceDir);
  for (const entry of collisions) {
    failures += 1;
    process.stdout.write(`CHECK name=pi_agent_collision_${entry.name} status=fail path=${JSON.stringify(entry.file)} canonical=${JSON.stringify(entry.canonical)}\n`);
  }
  if (!collisions.length) process.stdout.write('CHECK name=pi_agent_discovery_collisions status=pass nested_and_frontmatter_names=true\n');
  if (failures) process.exitCode = 1;
}

module.exports = { supportedOpenAgents, inspectPackage, discoveryIdentity, agentCollisions };
if (require.main === module) {
  try { main(process.argv.slice(2)); }
  catch (error) {
    process.stderr.write(`CHECK name=pi_installation status=fail reason=${JSON.stringify(error.message)}\n`);
    process.exitCode = 1;
  }
}
