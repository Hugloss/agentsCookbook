# Optional Run Artifact Protocol

Run artifacts are external working memory for low-context models. They are optional infrastructure around standalone capabilities, not a requirement of those capabilities.

The preferred persistence boundary is **outside the reviewer agent**. Reviewers stay read-only; a harness-side exporter materializes completed runtime evidence after the call has returned.

## Materialized run shape

`scripts/export-review-artifacts.js` writes:

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

Examples:

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

The exporter reads real `subagent` calls from Pi JSONL or real `task` results from an OpenCode exported session. It does not synthesize missing reviews.

## Full review artifact

A successful reviewer output is written verbatim to its Markdown artifact. A failed/missing call gets an explicit unavailable artifact rather than an invented review.

Once materialized, treat the artifact as immutable evidence for that run. Its receipt records the SHA-256 and character count.

## Compact receipt

Each receipt contains only cheap indexing/provenance data:

```text
run_id
runtime
sequence
reviewer
status
runtime_status
tool_call_id
subject
artifact
output_sha256
output_chars
headings
summary_hint
```

The receipt is intentionally not a second AI-authored summary. It is deterministic projection of the runtime result. Consumers inspect receipts first and load full Markdown only when the reviewer identity/status/headings indicate that detailed evidence is needed.

## Manifest

`manifest.json` binds the exported reviewer sequence to:

- run ID;
- runtime;
- source trace filename;
- optional subject ID/revision/SHA-256;
- per-reviewer artifact and receipt paths;
- per-reviewer output identity and size;
- success/failure counts.

## Provenance

When identities are available, bind artifacts to run ID, repository identity, subject revision/identity, reviewer identity, and capability identity. Never silently combine findings produced against different subject revisions as if they reviewed the same object.

The current exporter accepts subject identity fields but does not invent repository or capability identities that the source trace does not contain.

## Authority

Reviewers must not receive broad project write permission merely to persist artifacts. The default authority model is:

```text
reviewer (read-only)
  -> runtime result
  -> harness-side exporter
  -> run-local immutable artifacts
```

A future runtime-native artifact sink may replace the post-run exporter only if it can prove path-scoped writes without granting project write authority.

Long-lived knowledge is separate from run-local artifacts; promotion across runs must be explicit so stale findings do not silently become current facts.
