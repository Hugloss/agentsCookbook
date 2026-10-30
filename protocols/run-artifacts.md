# Run Artifact Protocol

Run artifacts are optional external working memory for low-context models. Standalone capabilities must still work without them.

Two persistence modes are supported:

1. **live artifact-backed mode** — reduces coordinator context during the run;
2. **post-run export** — materializes evidence after a normal run for audit/reuse.

## Live artifact-backed mode

Set an absolute run root before starting OpenCode or Pi:

```bash
export AGENTS_COOKBOOK_RUN_DIR=/absolute/path/to/runs/<run-id>
```

The installed runtime adapters then expose two different capabilities under agent permissions:

```text
reviewers: review_artifact      # write one own report + compact receipt
primaries: review_artifact_read # read one named report selectively
```

Reviewers remain deny-by-default and receive no generic project write/edit authority. Primary agents cannot create or replace reviewer reports.

### Reviewer write contract

`review_artifact` accepts only:

```text
artifact_id
summary          <= 1200 characters
content          <= 65536 characters
subject_id?      optional
subject_revision? optional
```

It does **not** accept a path. The adapter chooses:

```text
<run-root>/reviews/<artifact-id>.md
<run-root>/receipts/<artifact-id>.json
```

Writes use create-only semantics; an existing artifact ID cannot be overwritten. The adapters realpath-check their run subdirectories so a symlink cannot redirect writes outside the configured root.

Both live adapters bind writes to reviewer identity rather than trusting a free-form artifact name:

- OpenCode requires the current reviewer identity in tool context and binds `artifact_id` to it;
- Pi registers the write tool only inside a recognized delegated cookbook reviewer child, accepts only the nine known reviewer IDs, and requires `artifact_id` to equal `PI_OPEN_AGENTS_NAME`.

Pi's top-level process never registers `review_artifact`; it may register only `review_artifact_read`. A directly selected standalone reviewer therefore still works but returns its full report normally. Use `subagent-router` for a one-reviewer Pi run that also needs live low-context persistence.

### Compact live receipt

A successful live write returns a compact receipt containing:

```text
schema_version
runtime
run_id
reviewer / artifact_id
subject_id / subject_revision
artifact
sha256
chars
summary
```

MASTER uses `summary` first. It reads the full report only when:

- a material finding is ambiguous;
- two findings conflict;
- the finding conflicts with verified repo/implementation evidence;
- a severe verdict cannot be resolved safely from the compact summary;
- a one-reviewer user request explicitly asks for the full detailed artifact.

Never bulk-read every report merely because it exists.

Before returning a named report, the live reader validates its receipt's schema,
runtime, run/reviewer identity, fixed relative path, hash, character count and
summary budget. Both directories and files must resolve inside the configured
run root. A missing or inconsistent receipt is a failed read, not an invitation
to return unverified text. Live `run_id` is the basename of the canonical run
root; preserve that name when relocating a live store for these checks.

Receipt hashes are local integrity checks, not signatures. Someone able to
rewrite both the body and its receipt can change both; a matching receipt also
does not prove the review's substantive correctness.

For Pi specifically, `pi-open-agents` returns the child `result.output` as the parent-visible subagent tool text and retains the richer child `AgentResult` separately in `details`. In artifact-backed mode the reviewer therefore returns the compact receipt as its final output; the full report remains in the run store unless MASTER selectively reads it. Runtime qualification still verifies this on the deployed Pi/plugin versions.

## Post-run fallback export

Runs performed without live artifact mode can be projected afterward from runtime evidence:

```bash
node scripts/export-review-artifacts.js \
  --runtime pi \
  --input /path/to/session.jsonl \
  --out runs/<run-id> \
  --run-id <run-id> \
  --subject-id plan-v2 \
  --subject-revision 2

node scripts/export-review-artifacts.js \
  --runtime opencode \
  --input /path/to/opencode-export.json \
  --out runs/<run-id>
```

The exporter reads structured native `subagent` or `task` calls and matched
results. Pi export follows the active session branch. Reviewer success requires
explicit successful completion and usable output; attempted, unfinished and
unknown work remains separate. Invalid session/entry identities or malformed
input fail before output is published.

The output directory must be absent or empty and cannot itself be a symlink.
The exporter materializes a complete staging directory before publishing it;
existing artifacts are never mixed with a new export. Its successful exit means
the export operation completed, not that every reviewer succeeded.

Its shape is sequence-oriented because it projects a completed runtime trace:

```text
<run-dir>/
├── manifest.json
├── reviews/
│   ├── 01-<reviewer>.md
│   └── ...
└── receipts/
    ├── 01-<reviewer>.json
    └── ...
```

A failed, missing, incomplete or unknown call gets an explicit unavailable
artifact. Receipts record the output hash, size, headings, status, native call
identity, source-file hash, session/branch scope and a deterministic summary hint.
The manifest counts each outcome separately. These sequence-oriented exports
are a different format from the live store checked by `check-run-artifacts.js`.

## Provenance and identity

When available, bind artifacts to run ID, repository identity, subject revision/identity, reviewer identity, capability identity, and runtime tool-call evidence. Never combine findings produced against different subject revisions as though they reviewed the same object.

Current live adapters bind run/reviewer/subject/output identity. The post-run exporter accepts subject identity fields. Neither path invents repository/capability identities that its source evidence does not contain.

## Authority

The governing rule is:

```text
full report durability != generic project write permission
```

Live mode uses a fixed run-root tool. Fallback mode writes outside the model from captured runtime evidence. Both preserve reviewer project read-only authority.

Long-lived knowledge remains separate from run-local artifacts; promotion across runs must be explicit so stale findings never silently become current facts.

For real model-backed promotion, use [`../docs/local-runtime-qualification.md`](../docs/local-runtime-qualification.md).
