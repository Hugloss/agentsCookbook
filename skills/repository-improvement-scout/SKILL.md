---
name: repository-improvement-scout
description: Scouts a repository for evidence-backed investigation leads and suggests what to inspect next before proposing fixes.
license: MIT
---

# Repository Improvement Scout

Standalone, read-only repository discovery skill for deciding what is worth investigating next.

## INVARIANT

> **Do not start with a fix. Start with a repository signal strong enough to justify a bounded investigation.**

## HUNT

Trace important production, test, build, and recovery paths and hunt for signals such as:
- the same decision, state, lookup, parse, or traversal appearing in several owners;
- old and new architecture paths coexisting;
- unclear ownership of durable state, resources, retries, failure handling, or lifecycle;
- repeated defensive guards that may indicate a weak upstream model or contract;
- slow or complex tests that appear to expose production coupling or repeated work;
- hidden side effects, broad dependency surfaces, or long forwarding chains;
- async work, callbacks, retries, recovery, or cleanup whose ownership is hard to explain;
- code that repeatedly reconstructs information already resolved earlier in the path;
- cleanup, compatibility, or fallback code whose current callers are unclear.

Search broadly enough to find patterns, then follow at least one real path before promoting a signal into an investigation lead.

## PROVE

For every investigation lead, provide:
- **Observed signal** — what in the repository triggered attention;
- **Reachable path** — where that code participates in real production/test behavior;
- **Why it may matter** — correctness, reliability, performance, testability, or unnecessary complexity;
- **Evidence already seen** — concrete files, symbols, call paths, tests, or runtime behavior;
- **Next question** — the smallest question that would confirm or dismiss the concern;
- **Where to inspect next** — exact files, callers, state owners, tests, or transitions;
- **Disconfirmation check** — evidence that would show the suspected issue is actually intentional or safe;
- **Next skill** — `codebase-finding-derivation` or the narrow specialist that should prove the issue if the lead survives.

A lead does not need enough proof to be a finding. It needs enough evidence to justify the next inspection.

## DO NOT REPORT

Do not call these things findings by themselves:
- large files or long functions;
- TODO/FIXME comments;
- grep similarity;
- many dependencies or imports;
- old-looking names;
- theoretical races without a reachable ordering;
- code that merely differs from your preferred design;
- speculative rewrites with no repository signal.

Do not produce a generic refactor wishlist or fixed Top N list.

## PREFER

Prefer a small number of high-signal investigation leads over broad commentary. Order them by likely material impact and current evidence strength.

The preferred sequence is:

```text
repository signal
-> bounded investigation lead
-> codebase-finding-derivation or narrow specialist
-> proven finding
-> smallest corrective change
```

Stop when the evidence says `LEAVE ALONE`.

## OUTPUT

Return `# Repository Improvement Scout`.

For each lead include:
- `Signal`
- `Why worth investigating`
- `Evidence seen`
- `Inspect next`
- `Question to prove or dismiss`
- `Disconfirmation check`
- `Suggested next skill`

End with `## Leave Alone` for suspicious-looking areas that were inspected but currently have a coherent explanation, and `## No Further Leads` when no additional evidence-backed investigation is justified.
