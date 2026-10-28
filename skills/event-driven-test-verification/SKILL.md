---
name: event-driven-test-verification
description: Build or repair integration-test verifiers that observe the exact operation outcome within a bounded deadline.
license: MIT
---

# Event-Driven Test Verification

Construct or repair observation helpers for asynchronous integration and system
tests. When asked only to review, inspect without editing.

Own the path from arming observation through triggering work, matching its
outcome, and releasing observer resources. General timing-smell review belongs
to `deterministic-causality-test-review`; service provisioning and data reset
are separate concerns. Do not require another skill to complete this workflow.

## INVARIANT

> Establish observation before triggering work, or prove a replay contract
> retains it; accept only that operation's required outcome within a bounded wait.

Anchor success, terminal failure, and correlation rules in the production
contract before changing the verifier. Do not weaken those rules to make a test
pass or substitute an unrelated event for completion.

## HUNT

- Trace one real test through configuration, observer setup, trigger, background
  producer, payload decoding, assertion, and cleanup. Include directly affected
  retries or concurrent waiters when they can change which event is accepted.
- Inspect the actual response model, serialization, topic/route settings,
  operation-ID generation, and completion semantics. Determine whether an
  acknowledgement proves completion or merely acceptance.
- Locate observer readiness, subscriptions/assignments, starting positions,
  retained messages, shared consumer groups, and timeouts. Check whether a fast
  response can arrive before the observer is ready or before the ID is returned.
- Establish resource ownership: consumer/client, reader task, buffer, and waiter.
  Check failures during startup and cancellation as well as successful teardown.

Read [Kafka and polling patterns](references/kafka-and-polling.md) when building
a broker observer or a bounded state poller. Treat its adapter examples as
contracts to implement against the repository's actual clients and schemas.

## BUILD OR REPAIR

1. **Choose the observation contract.** Prefer an existing completion handle,
   callback, event, or queryable terminal state. Keep assertions meaningful for
   the real integration boundary. If production exposes no adequate completion
   signal, identify that owner instead of inventing a success heuristic.
2. **Arm before triggering.** For fresh-only observation, establish the subscription
   and required assignment/starting position before publishing or seeding work.
   A proven replay path may retain an earlier cursor instead. A client
   `start()` call is sufficient only when its documented contract proves those
   conditions. Buffer events that can arrive before a server-generated operation
   ID is returned. Never advance the observation boundary after the trigger.
3. **Correlate precisely.** Match a unique operation ID and the relevant run,
   tenant, attempt, or topic scope when those affect identity. Reject stale
   observations. Ignore unrelated events without losing them for another active
   waiter; use independent observers or one dispatcher for concurrent waiters.
4. **Apply the real result contract.** Decode with the production schema or a
   contract-equivalent adapter. Return on the required terminal success; fail
   immediately on a matching terminal failure or invalid matching payload.
   Continue through intermediate states. Keep test doubles aligned with the
   production API instead of preserving obsolete mock shapes.
5. **Bound the operation.** Use one monotonic deadline for arming, triggering,
   and waiting, or explicitly document separate setup and assertion budgets.
   Pass remaining time into reads and readiness probes; never restart the wait
   budget for each message, poll, retry, or rebalance. Permit short bounded
   sleeps between condition checks. Do not catch cancellation or terminal
   failures as retryable absence.
6. **Release ownership.** Close clients and cancel and await owned reader tasks
   on success, timeout, assertion failure, cancellation, and partial startup.
   Bound cleanup separately so an exhausted observation deadline does not
   prevent teardown. Preserve the original failure and report cleanup failures
   without silently swallowing either. Restore temporary configuration.

Take topics, endpoints, credentials, and options from the resolved application
or test configuration. Literal values are appropriate when the literal itself
is the test's explicit contract. Prefer a small helper around existing clients
over a new polling framework or an invented universal manager.

## PROVE

For a finding, show the reachable ordering or matching error: what observation
the test requires, what it can actually accept or miss, and the resulting false
pass, false failure, hang, or leak. A `sleep`, polling loop, or `latest` setting
alone is not proof.

For a change, exercise the affected contract with focused cases: an immediate
response, stale/unrelated messages, the matching success and terminal failure,
timeout, and interrupted startup/cleanup where applicable. Add a concurrency
case only when observers share state. Use the repository's existing test seams;
do not require a live broker to prove pure matching logic.

Distinguish structural checks, fake-client behavior, and actual integration
execution. Report which backend/configuration was exercised. A passing mocked
case does not establish broker assignment, connectivity, or production schema
compatibility.

## DO NOT REPORT

- Bounded polling for an observable integration result when no stronger usable
  signal exists; a sleep inside that poller is not an arbitrary completion delay.
- An observer started after the trigger when an established replay/cursor
  contract demonstrably retains and selects the required response.
- Historical messages that cannot satisfy the established operation identity,
  or harmless status events the production contract defines as intermediate.
- A missing reusable verifier class when the existing short test already owns
  readiness, correlation, deadlines, and cleanup correctly.
- General container lifecycle, global data isolation, or timeout tuning without
  evidence of a failure in this observation path.

## OUTPUT

Return `# Event-Driven Test Verification` with the inspected operation and
contract, relevant evidence, change or correction direction, and verification.
For construction, distinguish completed changes from partial work and identify
unverified transport behavior or missing production contracts.

For review, use `FINDING` only for a proved contract violation; use `CLEAN` only
for the fully inspected observation path, `LEAVE ALONE` for a supported existing
pattern, or `INSUFFICIENT EVIDENCE` when missing code/runtime evidence prevents a
decision. State the inspected boundary and exclusions for clean results too;
never turn a bounded inspection or skipped integration run into a suite-wide
reliability claim.
