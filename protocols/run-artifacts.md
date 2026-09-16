# Optional Run Artifact Protocol

Run artifacts are external working memory for low-context models. They are optional infrastructure around standalone capabilities, not a requirement of those capabilities.

Suggested per-run shape:

```text
runs/<run-id>/
├── manifest.json
├── subjects/
├── reviews/
│   ├── <review>.md
│   └── <review>.receipt.json
├── evidence/
└── synthesis/
```

## Full review artifact

A full report may contain the detailed reviewer artifact. Once complete, treat it as immutable evidence for that run.

## Compact receipt

A receipt should remain small and include:

```text
reviewer
capability
status
subject_revision
subject_identity
material finding IDs/severities/titles
unresolved items
artifact location
```

The synthesizer consumes receipts first and reads full reports only for material findings, conflicts, verification, or explicit audit needs.

## Provenance

When identities are available, bind artifacts to run ID, repository identity, subject revision/identity, reviewer identity, and capability identity. Never silently combine findings produced against different subject revisions as if they reviewed the same object.

## Authority

Reviewers must not receive broad project write permission merely to persist artifacts. Persistence is enabled only when a runtime provides a safe, bounded artifact-write mechanism. Otherwise the caller captures returned reports externally.

Long-lived knowledge is separate from run-local artifacts; promotion across runs must be explicit so stale findings do not silently become current facts.
