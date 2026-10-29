---
name: kafka-delivery-safety-review
description: Finds Kafka acknowledgements, rebalances, and long-running work that lose messages or repeat protected effects.
license: MIT
---

# Kafka Delivery Safety Review

Standalone, read-only review of Kafka **consumer delivery safety** for short or long-running workers, including OCR, AI inference, ETL, and ordinary event processing. Client-language and deployment agnostic; `aiokafka`/Kubernetes notes below are illustrative, not mandatory technology choices.

## INVARIANT

> **No Kafka offset may acknowledge unfinished work, and no replay, rebalance, or stale owner may repeat a non-repeatable effect without an enforceable idempotency boundary.**

This skill tests the *end-to-end handoff*: fetch -> admission -> execution -> durable effect/terminal disposition -> eligible offset commit -> recovery. Its "platinum" standard is a verified contract, **not** a blanket "exactly once" or "no loss" marketing claim.

## HUNT

Trace real consumer paths, not configuration strings alone:

- **Poll/processing separation:** CPU or blocking I/O starves client calls or event-loop heartbeat tasks; long work exceeds `max.poll.interval.ms`/client-specific progress limits; an internal queue grows without bounds or its work survives ownership loss.
- **Backpressure:** fetched and decoded record bytes, queued work, per-partition in-flight positions, simultaneous model jobs, process/container memory and GPUs exceed an explicit admission budget; pausing intake is mistaken for freeing retained records.
- **Offset correctness:** automatic commits, commits of the consumer's fetched position, a batch-wide highest offset, or an out-of-order completion commit skip an unfinished earlier offset in the same partition; failure/commit retry hides `CommitFailedError` or revoked ownership.
- **Idempotency authority:** a read-then-insert "already processed?" check races; duplicate business IDs are not scoped or versioned correctly; claims have no uniqueness/lease/fencing; terminal registry status is written separately from required durable effects; a zombie worker can commit after lease expiration.
- **External effects:** DB commit, object write, outbound Kafka publish, email/payment/API side effect or DLQ record cannot be atomically reconciled with an acknowledgement; a timed-out effect can succeed remotely and be retried locally.
- **Rebalance and shutdown:** revoked partitions keep processing without explicit authority; pending tasks can complete or commit after reassignment; SIGTERM/dropout neither drains bounded work nor leaves safe replay; a grace period is treated as a crash-proof guarantee.
- **Error handling:** transient, permanent, poison, and infrastructure failures collapse into one `skip` or DLQ path; failure to persist a terminal result or publish to DLQ is followed by a commit; retries are unbounded and starve a partition.
- **Health and recovery:** an idle worker is diagnosed dead because no record was completed; a healthy long task is restarted merely because its last *completion* is old; liveness reports healthy while poll/worker progress is permanently wedged; retention/lag or offset-reset policy silently discards unseen records.

## PROVE

For each suspected defect establish, using source, deployed configuration and/or controlled execution evidence:

1. **Delivery contract:** consumer group, partition/offset ordering, event identity and deduplication scope, expected effects, and declared semantics (at-most-once, at-least-once, effectively-once effects, or Kafka-to-Kafka transactional exactly-once).
2. **Reachable failure cut:** concrete ordering of fetch, queue, claim, effect, registry write, acknowledgement, crash, retry, rebalance, or lease expiry.
3. **Owner and transition:** who may execute, renew, fence, finish, classify, and commit; show the actual concurrency/transaction guard or missing guard, not just a `SELECT` result.
4. **Consequence:** which input can be skipped forever, which non-repeatable effect can happen twice, or which owner can commit stale output; identify the first unsafe boundary.
5. **Decisive proof:** a deterministic replay/race test or code/config trace that distinguishes the defect from a safe near-neighbor. Identify any uninspected effects or client behavior instead of guessing.

A deduplication row alone **does not** prove exactly-once effects. A pre-work DB lookup is not atomic admission; concurrent copies may both pass. Even a lease is not sufficient unless late effect/commit paths are fenced or inherently idempotent. Kafka transactions can make Kafka-output-plus-offset atomic, but do **not** automatically include arbitrary databases, files, or external APIs.

## DELIVERY CONTRACT TO VERIFY

- **Identity and admission:** use a stable logical-operation identity with correct producer/tenant/version scope; acquire one atomic claim (for example, unique insert or compare-and-set), distinguish `claimed/running/succeeded/permanently-rejected/retryable`, and define expiry, takeover, and fencing of stale generations where relevant. Do not wait forever on an abandoned claim.
- **Durable completion:** require domain effects and success evidence to commit atomically where the same database owns both; otherwise use effect-owned idempotency keys, transactional outbox/inbox, conditional writes, or explicit reconciliation. Mark a business rejection terminal only with an authorized policy and durable reason.
- **Offsets:** disable auto-commit when application-controlled acknowledgement is required. Commit only the **next offset after the contiguous terminal prefix** per topic-partition; preserve gaps from unfinished work even if later records finish. Acknowledge a safely completed duplicate without repeating its effects. Failed or uncertain commits must be replay-safe; commit failure does not undo durable effects.
- **Partition ownership:** pause intake for saturated partitions while continuing necessary consumer-client progress; bound each queue/in-flight unit. On partition revocation, stop admitting, cancel/finish with a bounded plan, revoke/fence write authority, and commit only eligible prefix while ownership still permits; unresolved work remains eligible for replay. Assignment generation alone does not fence an external side effect unless the effect owner checks it.
- **Process resources:** bound preflight document/record size and decoded memory, in-flight work, fetch buffers, and execution concurrency against **container/cgroup** capacity and downstream capacity. Apply workload-specific admission policy and explicit disposition; avoid universal "100 pages", "85% RAM", or "queue 1-5" thresholds. Isolate CPU-heavy work from an async event loop when necessary. Backpressure pauses admission; it cannot retroactively eliminate an OOM.
- **Failure and terminal disposition:** retry transient failures with bounded backoff/jitter and a defined retry horizon; persist poison/permanent outcomes or a durable retry/DLQ handoff **before** acknowledging. Do not route a DB outage directly to DLQ merely to make the consumer move forward; if DLQ or status persistence fails, retain replay responsibility. An empty or unusual business result is not automatically a permanent error.
- **Health and termination:** separate liveness (irrecoverable deadlock), readiness/admission (can accept more work), startup, and progress telemetry (poll, fetch, in-flight start/age/renewal, completions, commit attempts/errors, lag, pauses, rebalances). Interpret idle periods and legitimate long jobs explicitly. SIGTERM stops intake, drains bounded work where possible, flushes eligible commits and closes clients; forced kill always remains a replay case. Termination grace includes hooks/drain/cleanup and is not an exactly-once mechanism.
- **Retention/recovery:** verify retention, offset-reset and source replay assumptions, especially after a prolonged outage or DLQ failure. A `latest` reset without an explicit data-loss policy cannot qualify as lossless.

## CLIENT-SPECIFIC CAUTIONS

- In **aiokafka**, heartbeats/rejoin work can run in the background, but cooperative event-loop scheduling still matters; `max_poll_interval_ms` also concerns time between consuming API calls. Decoupling processing does not authorize abandoning consumption forever. Use bounded `getmany()` and `pause()/resume()` according to the client's semantics.
- For **manual commits**, commit `last_contiguously_processed_offset + 1` **for that partition**; register and handle rebalance callbacks and commit failure. Do not infer that a single highest offset from a mixed batch is safe.
- For **Kubernetes**, liveness probes can restart the worker, readiness failures alone do not stop an internal Kafka poller, and `terminationGracePeriodSeconds` is a bounded termination window, not guaranteed task completion.

Reference semantics: [aiokafka consumer guide](https://aiokafka.readthedocs.io/en/latest/consumer.html), [aiokafka API](https://aiokafka.readthedocs.io/en/latest/api.html), [Kafka delivery semantics](https://docs.confluent.io/kafka/design/delivery-semantics.html), [Kubernetes probes](https://kubernetes.io/docs/concepts/workloads/pods/probes/), [Kubernetes termination](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/).

## DISCRIMINATING TEST VECTORS

Select cases made relevant by the actual workflow; use controlled barriers/side-effect counters instead of scheduler timing:

- Two consumers concurrently claim the same logical operation; only one non-repeatable effect is admitted, and the loser has a defined wait/replay/terminal path.
- Crash **before** effect, **after** effect before registry/ack, and **after** durable completion before offset commit; none loses work or repeats a protected effect.
- Partition offsets `10` and `11` finish out of order; completion of `11` cannot advance committed position past unfinished `10`.
- Rebalance or lease expiry during a slow job; old owner cannot write stale output or commit after losing authority; replacement safely recovers.
- DLQ publish/DB failure during poison handling; no acknowledgement until the durable terminal handoff exists.
- Slow valid job, legitimately idle consumer, stuck poll loop, and stuck worker are distinguishable by health policy.
- Oversized input, memory pressure, cancelled drain, forced termination, and retention/offset reset obey explicit bounded recovery/disposition contracts.

A genuinely safe transactional Kafka-to-Kafka processor, a simple sequential consumer with proven bounded execution, and an idempotent remote effect with a strong key are **control cases**: do not demand a database registry, custom queue, lease service, or a second orchestration layer if the existing guarantees suffice.

## DO NOT REPORT

Do not report duplicate *execution* when repeated computation is permitted and the contract protects its non-repeatable effects; do report waste only through the appropriate performance skill. Do not call Kafka's normal at-least-once redelivery a defect by itself. Do not require literal poll/queue/worker architecture when the client already keeps required group progress safely. Do not treat stale completion timestamps, temporary backpressure, or absence of a DLQ as defects without a violated delivery/disposition contract. Do not claim full-system safety from sampled tests, a passing happy path, or a registry existence check.

Neighboring ownership: `retry-idempotency-review` owns generic duplicate effects across transports; `stale-work-race-review` owns general old-owner writes; `resource-lifetime-review` owns resource cleanup; `failure-contract-review` owns error meaning; `durable-commit-path-review` owns multiple durable transition authorities. **This skill owns their Kafka-specific composition at the fetch/acknowledgement/rebalance boundary.** Do not issue duplicate findings for one causal defect.

## PREFER

Repair the smallest existing semantic owner: partition-aware contiguous commits, atomic admission/terminal transitions, effect-owned idempotency, fenced takeover, bounded fetch/in-flight capacity, and explicit recovery. Simplify before adding registries, coordinators or wrappers. Derive configuration values from documented execution, resource, group, and shutdown contracts rather than copying example numbers.

## OUTPUT

Return `# Kafka Delivery Safety Review` with:

- inspected scope (client/version, consuming entrypoints, topic/partition model, offset settings, effect owners, deployments) and **uninspected boundaries**;
- delivery/identity/terminal/disposition contract and compact phase/ownership map;
- each **proved** finding: source/config evidence, failure cut, premature acknowledgement or repeated effect, missing owner/guard, minimal correction and deterministic test;
- qualified safe/control paths, unresolved assumptions (especially external effects), and the declared limits of any "exactly once" claim.

End with one bounded verdict:
- `FINDING` — a reachable Kafka delivery-safety violation is established; state unresolved scope separately.
- `CLEAN` — every applicable fetch-to-terminal/ack, replay/rebalance, and failure path **within the declared inspected scope** has evidence of a safe disposition; never imply repository-wide qualification.
- `LEAVE ALONE` — the suspected risky pattern was inspected and is safe under its explicit contract.
- `INSUFFICIENT EVIDENCE` — unknown effects, incomplete paths, missing configuration, or unverified client assumptions prevent a finding or clean conclusion.

A `FINDING` does not certify uninspected paths; missing proof never becomes `CLEAN`.
