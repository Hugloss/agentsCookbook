'use strict';

// Read native Pi session trees. Both audit entry points must use the selected
// branch, and malformed evidence must not be repaired into a successful run.
function object(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function parsePiSession(raw, label) {
  const entries = [];
  for (const [index, line] of raw.split(/\r?\n/).entries()) {
    if (!line.trim()) continue;
    let entry;
    try { entry = JSON.parse(line); }
    catch (error) { throw new Error(`${label}:${index + 1}: invalid JSON: ${error.message}`); }
    if (!object(entry)) throw new Error(`${label}:${index + 1}: session entry must be an object.`);
    entries.push(entry);
  }
  const header = entries[0];
  if (!header || header.type !== 'session' || ![2, 3].includes(header.version)
      || typeof header.id !== 'string' || !header.id || typeof header.cwd !== 'string' || !header.cwd) {
    throw new Error(`${label}: expected a native Pi version 2 or 3 session header.`);
  }
  const byId = new Map();
  for (const entry of entries.slice(1)) {
    if (typeof entry.type !== 'string' || !entry.type || entry.type === 'session'
        || typeof entry.id !== 'string' || !entry.id || entry.id === header.id || byId.has(entry.id)) {
      throw new Error(`${label}: missing, duplicate, or invalid session entry identity.`);
    }
    if (entry.parentId !== null && (typeof entry.parentId !== 'string' || !byId.has(entry.parentId))) {
      throw new Error(`${label}: entry ${entry.id} has an unknown or nonpreceding parent.`);
    }
    if (entry.type === 'message' && (!object(entry.message) || typeof entry.message.role !== 'string')) {
      throw new Error(`${label}: entry ${entry.id} has an invalid message.`);
    }
    byId.set(entry.id, entry);
  }
  const branch = [];
  let current = entries.length > 1 ? entries[entries.length - 1] : undefined;
  while (current) {
    branch.push(current);
    current = current.parentId === null ? undefined : byId.get(current.parentId);
  }
  return { header, entries: branch.reverse() };
}

function toolArguments(value, label) {
  let args = value;
  if (typeof value === 'string') {
    try { args = JSON.parse(value); }
    catch { throw new Error(`${label}: malformed tool arguments.`); }
  }
  if (!object(args)) throw new Error(`${label}: tool arguments must be an object.`);
  return args;
}

function collectPiTools(entries, label) {
  const calls = [];
  const byId = new Map();
  for (const entry of entries) {
    if (entry.type !== 'message') continue;
    const message = entry.message;
    if (message.role === 'assistant') {
      if (!Array.isArray(message.content)) throw new Error(`${label}: assistant message content must be an array.`);
      for (const part of message.content) {
        if (!object(part) || part.type !== 'toolCall') continue;
        if (typeof part.id !== 'string' || !part.id || (byId.has(part.id) && !byId.get(part.id).result)
            || typeof part.name !== 'string' || !part.name) {
          throw new Error(`${label}: missing or duplicate tool-call identity.`);
        }
        const call = { id: part.id, name: part.name, args: toolArguments(part.arguments, `${label}: ${part.id}`), result: undefined };
        calls.push(call);
        byId.set(part.id, call);
      }
    } else if (message.role === 'toolResult') {
      const call = byId.get(message.toolCallId);
      if (!call || call.result || message.toolName !== call.name) {
        throw new Error(`${label}: tool result has an unknown, duplicate, or mismatched call identity.`);
      }
      call.result = message;
    }
  }
  return calls;
}

module.exports = { parsePiSession, collectPiTools, toolArguments, object };
