---
name: proxy-gate-authority-review
description: Finds hard qualification gates that use heuristic proxies as if they proved the semantic contract being certified.
license: MIT
---

# Proxy Gate Authority Review

Standalone, read-only review of admission, certification, release, readiness, and qualification gates.

## INVARIANT

> **A hard gate may block only on evidence that is part of, or directly proves, the semantic contract that gate claims to qualify. A heuristic may guide investigation; it must not silently become product-validity authority.**

A metric can be useful without being a valid veto. File size, line count, complexity, lint debt, source position, formatting, churn, warning count, or another proxy may indicate where to inspect while still being unable to prove that the product is invalid.

## HUNT

Trace real paths that return admitted/rejected, certified/failed, releaseable/blocked, ready/not-ready, qualified/unqualified, or another hard success result.

Hunt for hard gates driven by:
- source-file or function line ceilings;
- complexity, branch, fan-out, churn, debt, warning, smell, or maintainability scores;
- formatting, naming, documentation shape, or implementation decomposition;
- exact source-line ranges or source positions that change under semantic no-ops;
- test-count, coverage, benchmark, or static-analysis numbers used beyond what their governing contract actually requires;
- aggregate repository-quality signals treated as proof of runtime correctness, safety, or release validity;
- historical quality rules copied into certification after the original semantic reason disappeared;
- a regression test that freezes the proxy threshold instead of the defect that originally motivated it;
- a preflight that repeats a native/runtime fact only to satisfy an internal quality rule rather than the execution contract.

The signal is not that a threshold exists. The signal is **authority mismatch**: violating the proxy can hard-fail the qualification claim even though the claimed semantic contract remains satisfied.

## PROVE

Before reporting a finding:

1. Name the **hard claim** being made, such as runtime certification, admission, release validity, security qualification, or readiness.
2. Name the **proxy** that can veto that claim.
3. Establish the governing semantic contract independently of the proxy.
4. Show a reachable case where the proxy changes while the relevant semantics do not, or where the proxy can pass while the relevant semantic defect remains.
5. Trace the exact gate path from proxy result to hard PASS/FAIL authority.
6. Show that the proxy itself is not an explicit required property of the contract being qualified.
7. Identify the real invariant, if one exists, that the proxy was trying to approximate.
8. Prefer a semantic regression for that invariant, or demote the proxy to diagnostics when no hard semantic invariant exists.

A particularly strong proof is a semantic no-op that flips the gate:

~~~text
working candidate
  + harmless comment / code movement / equivalent decomposition
  -> proxy threshold crossed
  -> certification fails
  -> certified behavior is unchanged
~~~

or a false reassurance:

~~~text
proxy remains under threshold
  -> real runtime/security invariant is broken
  -> qualification still passes
~~~

## DO NOT REPORT

Do not report a limit merely because it is numeric or strict.

Leave alone hard gates that directly express the contract being qualified, for example:
- an artifact exceeds a documented protocol or deployment size limit;
- a deadline/timeout, memory, storage, or resource budget is itself part of the supported product contract;
- a security/compliance policy explicitly requires a particular property and the gate measures that property directly;
- an API or wire-format bound is part of compatibility semantics;
- a repository has a separately named quality-policy gate whose claim is exactly compliance with that quality policy, rather than runtime/product certification.

Do not report a quality metric that is advisory only, or that merely selects an investigation target.

Do not report candidate weakening of an otherwise legitimate governing threshold under this skill; use baseline-self-authorization-review when the defect is that the candidate changes its own oracle.

Do not report missing or vacuous evidence under this skill; use evidence-readiness-review when the gate lacks the evidence required by its legitimate contract.

Do not report a hard semantic violation being averaged away by soft metrics under this skill; use aggregate-hard-failure-masking-review.

## PREFER

Prefer the smallest correction in this order:

1. Delete the proxy gate if it adds no semantic protection.
2. Demote useful heuristics to diagnostics, warnings, or investigation signals.
3. Recover the actual semantic invariant the proxy was approximating.
4. Test that invariant directly with a focused regression.
5. Keep hard qualification authority narrow: fail on broken product/runtime/policy semantics, not implementation shape.

Do not fix an arbitrary threshold by raising it, making it configurable, moving it to another certification stage, or adding exceptions for the current file. Those changes preserve the proxy as authority.

Prefer:

~~~text
semantic contract
  -> direct evidence
  -> hard gate

heuristic
  -> diagnostic / investigation
~~~

not:

~~~text
heuristic proxy
  -> hard product-validity gate
~~~

## OVERLAP

- baseline-self-authorization-review — a candidate weakens or rewrites the governing gate/baseline and then validates itself against that new authority.
- evidence-readiness-review — the governing qualification contract is legitimate but required evidence is missing, empty, filtered, or insufficient.
- aggregate-hard-failure-masking-review — a real hard violation exists but an aggregate score lets unrelated positives compensate for it.
- static-evidence-overclaim-review — a static analyzer claims facts its proof model cannot establish; use this skill only when that result is then promoted into the wrong hard gate authority.
- test-contract-coupling-review — tests freeze private choreography; use this skill when the frozen implementation shape is specifically used as qualification/certification authority.

Use proxy-gate-authority-review when the central defect is: **the gate claims one semantic outcome, but its veto is controlled by a proxy that does not prove that outcome.**

## OUTPUT

Return # Proxy Gate Authority Review with:
- hard qualification claim and governing semantic contract;
- proxy metric/check and exact gate path;
- semantic-no-op or counterexample proving the proxy is not authoritative;
- legitimate direct semantic invariants that should remain hard;
- proxy gates to delete or demote;
- focused semantic regressions that should replace proxy regressions;
- inspected qualification scope and any untraced gates.

End with one:
- CLEAN — every inspected hard gate is directly owned by the semantic contract it claims to qualify;
- LEAVE ALONE — suspicious thresholds/proxies were inspected and each directly represents the claimed contract or is advisory only;
- INSUFFICIENT EVIDENCE — the governing contract or real gate path could not be established far enough to distinguish a proxy from a legitimate hard requirement.
