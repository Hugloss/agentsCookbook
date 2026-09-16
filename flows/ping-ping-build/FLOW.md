# Ping-Ping Build Flow

This flow composes implementation ownership with eight standalone read-only reviews.

## Authority

- `ping-ping-build` alone modifies project files.
- Reviewers inspect implementation evidence and remain read-only.
- Skills define review methodology but never authorize edits.

## Sequence

1. Inspect request and affected areas.
2. Plan bounded implementation work.
3. Edit directly as the build master.
4. Run relevant validation.
5. Build a compact implementation-evidence packet.
6. Run all eight mandatory reviewers exactly once.
7. Classify material findings as accepted, rejected, or deferred.
8. Apply accepted fixes as the build master.
9. Rerun affected validation.
10. Audit actual reviewer calls and report status.

## Context economics

Do not propagate whole reviewer reports through later reviews. Keep changed-file summary, validation receipt, unresolved risks, and material finding decisions in active context. Full reports may live in an optional run artifact store when a runtime can provide path-scoped writes safely.
