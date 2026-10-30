---
name: kafka-delivery-safety-review
description: Finds Kafka acknowledgements, rebalances, and long-running work that lose messages or repeat protected effects.
license: MIT
---

# Kafka Delivery Safety Review

Standalone, read-only review of Kafka consumer delivery responsibility, including long-running OCR, inference, ETL, and ordinary event processing. Applies across clients and deployments; this is not a worker framework or a certification of an entire Kafka installation.

## INVARIANT

> **A source record may be acknowledged only after its required outcome is durable or responsibility has been durably transferred to an explicit recovery owner. Replay and ownership changes must preserve protected effects, required business ordering, and a reachable recovery path.**

A record is **settled at this boundary** when its effect is durable, an authorized terminal rejection is durable, or a durable handoff has accepted its remaining obligations. Settlement is not necessarily business success. An in-memory queue, a running claim, a live process, or a scheduled-but-unconfirmed publish is not sufficient evidence of settlement.

Repeated computation can be unavoidable after a crash. Distinguish at-least-once delivery, effectively-once protected effects, Kafka transactional processing, and exactly-once execution; do not promise the last merely because an idempotency table exists.

## SCOPE AND AUTHORITY

Start with the user's required guarantees and an explicit failure model: which crashes, duplicate deliveries, outages, ownership changes, retention windows, and ordering obligations must be tolerated? Record the actual client/version, group/assignment mode, entrypoints, effective configuration, effect owners, and deployment boundaries. Do not replace these requirements with weaker ones after discovering a failure.

The minimum end-to-end scope is the selected input path through decode/admission, all directly required effects, settlement/acknowledgement, retry or handoff, and restart/rebalance recovery. Inspect relevant producer/topic durability and downstream isolation as dependencies of that guarantee, not as an unrelated cluster audit. Expand along newly discovered causal dependencies; do not exclude a failing sink or retry path to obtain CLEAN. A deliberately local review remains local and cannot qualify the full worker.

Missing deployed configuration, external API semantics, or recovery ownership is **unknown**, not a safe default. An independently established intentionally lossy contract is not a product defect merely because it is not lossless; it also does not satisfy a user's lossless-worker goal.

## HUNT

Trace real code and configuration across fetch -> admission -> effect or handoff -> acknowledgement -> recovery. Concentrate on these seams:

### 1. Offset eligibility and business ordering

- Check auto-commit, implicit position commits, batch maximums, concurrent completion, commit retries, and late callbacks. Commit only a restart position that does not cross an **unsettled delivered record** for that topic-partition and assignment generation. Never use the highest fetched offset as proof of completion.
- The safe prefix is in **delivery order**, not consecutive integer arithmetic. Compaction, transaction markers, and aborted records can create legitimate offset gaps. Completing delivered offsets 41 and 44 can permit committing 45; an actually delivered unfinished 42 must block that advance. Do not invent missing work or use numeric gaps to excuse application-discarded work.
- Use the client's supported next-offset/metadata representation; last safely settled record offset + 1 is a conservative boundary when applicable. Discard stale completion/commit authority on reassignment. A failed commit does not undo an already durable effect.
- A safe commit frontier does not order effects. For order-sensitive updates, prove per-key/partition serialization, version checks, or an equivalent business guard across concurrent jobs and retry-topic detours. Do not impose global ordering on independent or commutative work.

### 2. Identity, admission, and protected effects

- Establish stable logical identity, tenant/producer/operation scope, and payload/version consistency. Topic-partition-offset identifies a Kafka record, not necessarily the same business operation republished at another offset or cluster. A conflicting payload under the same key must not silently inherit old success. Authorized reprocessing needs explicit semantics, not a newly random key on every retry.
- A read-then-insert check is not atomic admission. Where a claim is needed, verify unique/CAS acquisition, claim-busy handling, expiry/takeover and fenced completion. Do not acknowledge merely because a row exists or let abandoned claims remain unrecoverable. Do not demand claims when the effect owner's existing atomic idempotency suffices.
- Commit effect and terminal evidence atomically when one store owns both. Otherwise inspect the actual effect-owned idempotency key, conditional write, outbox/inbox protocol, or reconciliation owner. An outbox transfers responsibility; it does not make an arbitrary remote effect atomic. A timeout/cancellation can leave a remotely successful effect with an unknown local outcome.
- Deduplication retention and external idempotency-key lifetime must cover the **permitted replay horizon**, including delayed retries, DLQ redrive, operator replay and restore. Preserve required identities on handoff. Expired evidence cannot justify a once-only claim. A stale lease holder must be fenced at every protected effect or use an effect boundary that is independently replay-safe.

### 3. Kafka publication and transactions

- Follow output, retry, and DLQ publication through the real delivery outcome. Local buffering or obtaining a send future is not broker acknowledgement; verify delivery failure propagation before settlement. For transactional output, successful enqueue alone is not transaction commit.
- Bind required durability to actual producer acknowledgements, replication/in-sync-replica policy, leader-election behavior, and the declared failure budget. No universal replica count or `acks=all` checkbox proves every failure model. Unknown external cluster settings remain an assumption; name their owner.
- For Kafka transactional claims, inspect atomic output-plus-input-offset commit, correct group/partition metadata supported by the client, transactional identity/fencing, and `read_committed` at the applicable transactional input and output boundaries. Producer idempotence alone is not business deduplication or a consume-process-produce transaction.
- On abort, the consumer's local fetch position is not automatically rewound. Prove safe seek/re-fetch or consumer restart before later commits can skip the aborted batch. Unknown transaction outcomes require client-supported resolution; do not blindly republish. Transaction timeouts and open transactions must fit the actual work; do not automatically hold a transaction open for an entire multi-minute AI job.

### 4. Rebalance, backpressure, and lifecycle

- Preserve required consumer/group progress while limiting admission. Bound fetched bytes, decoded expansion, queues, active jobs, downstream calls and retained results against container/cgroup/GPU capacity. A record-count cap, host-RAM percentage or post-allocation check is not a hard memory bound. Fetch limits can have client-specific oversize-batch exceptions.
- Keep CPU/blocking work off cooperative client loops where necessary. Saturation pauses admission, not all client progress. On reassignment, reconcile pending work and reapply required admission limits; do not assume a previous pause state survives.
- On revocation or lost assignment, stop admitting affected work, resolve or fence its authority and commit only where the client/group protocol still permits it. Do not blindly attempt a final commit after ownership is lost. Avoid waiting for work that needs the same callback lock or suspended consuming API to progress.
- On SIGTERM, stop **new admission**, drain within a bounded budget while keeping required client progress, then close clients. Include hooks and cleanup in termination grace; test forced kill as a replay case. Cancelling a future or thread does not prove a remote call or subprocess stopped.
- Distinguish startup, readiness/admission, liveness and actual job progress. Idle, paused, long-but-progressing, dependency-blocked and wedged are different states. Claim renewal or a timer in the health server is not proof of worker progress. Readiness alone does not stop internal consumption; dependency outages should not automatically create liveness restart storms.

### 5. Failure disposition and recovery

- Cover decode/deserializer failures **before** the normal business handler, malformed/missing identity, unsupported schema and tombstones. A legitimate tombstone is not corrupt input. Preserve safe source coordinates and diagnostic evidence when business identity cannot be decoded; do not leak sensitive payloads into logs or DLQ by default.
- Classify errors by operation and outcome, not exception-name folklore: retryable dependency failures, authorized permanent rejection, and ambiguous external completion need different actions. A DB outage is not a reason to mark business success or permanently discard every input. Persist rejection or a durable retry/DLQ handoff before acknowledgement; failure of that handoff retains source responsibility.
- Define bounded backoff/jitter, retry horizon, durable attempt accounting where budgets must survive restart, and exhaustion disposition. Retry/DLQ handoff needs a delivery owner, retained identity, retention, actionable alerts and a controlled redrive path. Prevent retry cycles and overtaking where business order matters. A DLQ is neither mandatory nor a substitute for recovery ownership.
- A durable inbox may acknowledge before expensive processing **only** when its committed payload/identity, pending state, independent restart recovery and effect safeguards own all remaining work. A running lease without such recovery is not a durable handoff.
- Check source/output/retry retention, compaction semantics, group-offset expiration, reset/seek/restore and manual replay. `earliest` cannot restore deleted history; `latest` can skip unseen work. Make unrecoverable gaps explicit rather than silently reporting success. Recovery must eventually settle or escalate under the declared dependency/failure assumptions, not retry or renew forever.

## PROVE

For each finding establish:

1. The independently applicable delivery/effect/order/recovery requirement and actual scope.
2. Source/configuration evidence for a reachable sequence or failure cut, including what may already have succeeded.
3. The authority allowed to act and the exact missing, raced, expired or incorrectly interpreted guard.
4. A concrete consequence: lost responsibility, repeated protected effect, stale/incorrectly ordered result, or recovery that cannot meet its declared contract.
5. The smallest coherent correction and a deterministic witness plus safe near-neighbor control. Tests may support a finding; a clear code/config trace can also prove one without a mandatory benchmark exercise.

Distinguish a proved product defect from missing evidence or a needed qualification test. Do not turn every untested scenario into a bug. For applicable edge cases use the [failure matrix](references/failure-matrix.md); document why an edge is not applicable rather than silently omitting it.

## CLIENT-SPECIFIC CAUTIONS

Verify the installed client/version and effective configuration instead of translating Java Kafka settings literally into Python or another client.

- **aiokafka:** background heartbeats/rejoins still need event-loop scheduling. Inspect `getmany()`/`getone()` progress, `max_poll_interval_ms`, rebalance callbacks and `pause()/resume()` together. Do not hold a callback-needed lock around a consuming call. In a non-transactional publish, `await producer.send(...)` returns a delivery future; `send_and_wait()` or awaiting that future observes delivery. A successful transaction context supplies its own commit boundary. Reject unsupported configuration keys rather than copying a supposed `connection_timeout_ms` from a generic blueprint.
- **Other clients:** honor their thread-affinity, poll, callback, auto-commit and lost-assignment semantics. Do not impose aiokafka behavior on Java or librdkafka clients, or report safe client-owned progress mechanisms as missing custom poll loops.
- **Kubernetes:** termination grace is a bounded shutdown opportunity, not guaranteed completion or exactly-once execution. Readiness and liveness have different operational effects.

Primary semantics: [Apache Kafka consumer/offset API](https://kafka.apache.org/41/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html), [Kafka delivery and transaction design](https://kafka.apache.org/41/design/design/), [Kafka topic durability and retention configuration](https://kafka.apache.org/41/configuration/topic-configs/), [aiokafka consumer guide](https://aiokafka.readthedocs.io/en/stable/consumer.html), [aiokafka producer guide](https://aiokafka.readthedocs.io/en/stable/producer.html), [aiokafka API](https://aiokafka.readthedocs.io/en/stable/api.html), [Kubernetes probes](https://kubernetes.io/docs/concepts/workloads/pods/probes/), [Kubernetes termination](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/). Match these semantics to deployed versions; a documentation link is not proof of a target's configuration.

## DO NOT REPORT

Do not report normal redelivery or repeated pure computation when the required effects are replay-safe. Do not require queues, registries, distributed leases, outboxes, a DLQ, or a new orchestration layer when a simpler existing owner proves the contract. Do not demand numeric offset continuity, global ordering, a heartbeat on every completed message, or a universal timeout/queue/page-count value. Preserve safe transactional, sequential, idempotent-effect and durable-inbox designs.

Neighboring ownership: `retry-idempotency-review` owns generic repeated effects; `stale-work-race-review` owns generic old-owner writes; `resource-lifetime-review` owns cleanup; `failure-contract-review` owns cross-layer error meaning; `durable-commit-path-review` owns competing commit authorities. This skill owns their **Kafka delivery-responsibility composition**. Reconcile one causal defect into one finding rather than issuing overlapping repairs. General security, disaster-recovery, broker operations and performance audits are not implicitly completed by this review.

## PREFER

Repair the existing semantic owner: delivered-record commit frontier, atomic effect/settlement, effect-owned idempotency, fenced takeover, explicit durable transfer, bounded admission, and one recovery path. Delete competing paths before adding managers or wrappers. Keep fast deterministic correctness tests in the edit loop; use focused real-client/broker fault tests for the boundaries they alone can prove. Expensive soak, failover and resource-exhaustion campaigns can run separately on the project's risk-based schedule; do not infer native guarantees from mocks or make all slow tests mandatory for every edit.

## OUTPUT

Return `# Kafka Delivery Safety Review` with:

- required guarantees, failure model, inspected revision/client/configuration, lifecycle/effect owners, and uninspected boundaries;
- a compact guarantee/evidence table: supported, violated, unknown or not applicable, with rationale and any remaining deployment assumptions;
- proved findings, each with the unsafe sequence, consequence, minimal correction and decisive regression/control test;
- prioritized qualification gaps separately from product defects; required broker/client/restart checks and any operator recovery obligation;
- qualification actually performed: static review, executable fixture tests, model-backed discrimination, and target-runtime fault testing must be reported separately with `NOT RUN` where appropriate.

“Gold” and “platinum” are aspirations here, not certifications, average scores, or outputs inferred from loading this skill. Structural CI cannot qualify review accuracy; model case success cannot certify a production deployment; a safe consumer cannot guarantee data that an upstream producer never durably stored. Any reliability statement must name its supported failure model and remaining assumptions.

End with exactly one bounded verdict:

- `FINDING` — at least one reachable violation is established; retain other unresolved scope explicitly.
- `CLEAN` — all materially applicable paths within the declared complete review scope have evidence for the invariant, with no unresolved question material to that conclusion. State whether this is static only; it is not runtime certification.
- `LEAVE ALONE` — the suspected pattern is positively safe under the inspected explicit contract, without an unresolved material dependency.
- `INSUFFICIENT EVIDENCE` — no violation is established and missing paths, configuration, effect semantics or recovery proof prevent a bounded clean conclusion.

Unknown required guarantees cannot be averaged away, relabeled not applicable, or excluded after inspection. A finding never certifies uninspected paths.
