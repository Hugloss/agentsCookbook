---
name: empirical-benchmark-campaign
description: Runs frozen agent/tool benchmark campaigns from fresh authority through preflight, execution, resume, and evidence handoff.
license: MIT
---

# Empirical Benchmark Campaign

Use this skill to execute or resume a controlled empirical benchmark campaign after the experiment contract exists.

## INVARIANT

> **A benchmark campaign may compare only frozen definitions under observed execution authority, and may advance from preflight to interpretation only through independently qualified evidence. Missing, stale, incompatible, or contaminated evidence stays explicit; it is never repaired by changing the experiment after results exist.**

This skill owns campaign execution discipline. It does not decide product semantics, rank products, or repair defects found in a product.

## ESTABLISH AUTHORITY

Before executing trials:

1. re-establish the current harness/repository authority from exact source bytes;
2. identify the frozen suite/experiment version and exact definition set to run;
3. keep repository/model/tool/native-config identities observable rather than inferred;
4. keep independent oracle authority separate from every evaluated subject;
5. confirm selected assisted conditions have matching bare controls when assistance gain is claimed.

If the experiment contract must change, create a new experiment version before collecting results.

## PREFLIGHT

Run the benchmark's real admission path without invoking the coding agent.

Preflight must prove, for every selected definition:
- exact repository commit/tree can be materialized;
- the frozen mutation, if any, validates and applies;
- subject preparation succeeds;
- agent/runtime preparation succeeds;
- native tool/workspace binding is positively verified where required;
- the independent oracle healthcheck succeeds;
- preparation does not contaminate the workspace beyond frozen allowances.

Treat preflight states exactly:
- `READY` — eligible for execution;
- `COMPLETE` — an immutable valid experimental outcome already exists for the same execution authority;
- `INCOMPLETE` — environment/tool/runtime evidence is insufficient;
- `INVALID` — experiment/oracle/admission evidence is invalid;
- `CONTAMINATED` — isolation was violated;
- recorded non-outcome states remain evidence and are not silently overwritten.

Do not interpret `INCOMPLETE`, `INVALID`, or `CONTAMINATED` as a product failure.

## EXECUTE AND RESUME

Use one frozen selection for preflight, run, status, and report.

During execution:
- preserve the same task, mutation, oracle, budgets, seed/trial index, agent, and subject definitions;
- let native tools retain their own semantics and configuration authority;
- record tool availability separately from tool invocation;
- preserve bounded timeout/output/tool-call failures as evidence;
- write immutable, verified receipts only after sealed execution evidence is complete.

For resume:
- derive state from verified receipts plus frozen definitions;
- reuse matching completed execution identities;
- surface corrupt, foreign, duplicate, or conflicting receipts explicitly;
- never delete or overwrite a non-outcome receipt to make a campaign appear complete.

If a transient condition is fixed but execution identity does not change, use a new campaign root rather than mutating prior evidence.

## INTERPRETATION

Before interpreting results:
- require structural completeness for the selected definition set;
- distinguish structural completeness from qualification;
- exclude `INCOMPLETE`, `INVALID`, and `CONTAMINATED` from product success-rate claims;
- retain their execution cost where economics are reported;
- compare assistance only within compatible runtime/model authority;
- treat cross-agent/runtime rows as descriptive unless a separate comparability contract qualifies them;
- do not create an overall winner score unless the frozen experiment explicitly defines and independently justifies one.

When a metric is not authoritatively observable, report it as unavailable rather than estimating it from adjacent evidence.

## DEFECT HANDOFF

If the campaign exposes a reproducible product or harness defect:

1. freeze the failing definition, receipt, and reproduction evidence;
2. identify the true semantic owner;
3. repair upstream first when the defect belongs to another repository/component;
4. hand the mutable repair candidate to `adversarial-repair-campaign`;
5. after repair, rerun the **unchanged** frozen benchmark definition when the experiment remains valid;
6. create a new experiment version if the repair changes the benchmark contract itself.

Do not change prompts, answer keys, mutations, scoring, or task selection after seeing results merely to improve an outcome.

## STOP CONDITION

A campaign is ready for interpretation only when:
- the selected frozen definition set is fully accounted for;
- all evidence bundles are verified and non-conflicting;
- every product outcome used in comparison is qualified;
- runtime/model/config authority is comparable for the claimed comparison;
- known campaign infrastructure defects are either repaired and remeasured or explicitly excluded as incomplete evidence.

A campaign with all receipts present but one `INCOMPLETE`, `INVALID`, or `CONTAMINATED` trial is structurally complete but not qualified.

## OUTPUT

Return `# Empirical Benchmark Campaign` with:
- current harness/source authority;
- suite/experiment identity;
- frozen selection and paired controls;
- preflight readiness summary;
- completed/pending/conflicting/corrupt evidence;
- qualified outcome counts;
- runtime/model/tool identities relevant to comparison;
- unavailable metrics and observability limits;
- reproducible defects and semantic owners;
- exact next action.

End with exactly one:
- `READY_TO_RUN` — preflight is clean and selected unresolved definitions may execute;
- `EVIDENCE_READY` — the selected campaign is complete and qualified for interpretation;
- `BLOCKED_INCOMPLETE` — required authority, admission, isolation, oracle, or receipt evidence is incomplete/invalid/contaminated.
