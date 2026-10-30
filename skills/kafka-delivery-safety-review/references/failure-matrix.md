# Kafka delivery responsibility: failure witnesses and controls

Use the rows relevant to the inspected path. This is a discrimination and failure-injection guide, not a new framework, mandatory finding count, or proof that the skill detects these cases. Establish the target's requirement and failure model before judging its implementation.

For every applicable row, identify the effect owner, deterministic failure cut, observable recovery outcome, and safe control. Prefer barriers, controllable futures, injected failures and durable effect counters over timing sleeps. An in-process model establishes the modeled ordering only; actual client/broker semantics require real-client tests.

| Seam | Unsafe witness | Safe control / required observable outcome |
| --- | --- | --- |
| Out-of-order completion | Delivered offset 42 finishes while delivered 41 is blocked; commit 43; crash loses 41. | Keep the frontier before 41 until it settles; independent partitions may advance. |
| Legitimate offset gap | Delivered 41 and 44 settle, but a tracker waits forever for nonexistent 42/43. | Advance over the settled delivery prefix; prove the gap came from log visibility, not application loss. |
| Concurrent duplicate claim | Both deliveries pass a registry lookup and execute a once-only effect. | Atomic effect key or claim admits one effect; the loser has a defined busy/terminal/recovery path. |
| Busy/abandoned claim | Row existence is treated as success; original worker dies before the effect. | Running is not terminal. Safe takeover or an independently recovering durable inbox retains responsibility. |
| Crash after effect | Remote side effect succeeds, local result is lost, replay sends it again. | Effect-owned idempotency or authoritative reconciliation resolves the uncertain result without blindly repeating it. |
| Deduplication expiry | Registry TTL or provider key lifetime expires before an allowed DLQ/operator replay. | Retain identity evidence through permitted replay, or explicitly reject/reconcile older replays; do not invent fresh retry identities. |
| Conflicting identity | Same business key arrives with different payload/operation version and is silently skipped. | Compare semantic identity/payload and use the authorized conflict or intentional-reprocessing contract. |
| Durable inbox transfer | An in-memory queue or a mere live lease is acknowledged as transferred work. | Payload, identity and pending obligation commit durably; an independent recovery owner resumes after process death. Business completion can occur later. |
| Producer buffering | Awaiting aiokafka `send()` yields a future, but input is committed before delivery failure is observed. | Await actual non-transactional delivery, or use a successfully committed Kafka transaction that includes the offsets. |
| Kafka transaction abort | Output/offset transaction aborts; local consumer position remains advanced; a later successful commit crosses the abandoned input. | Seek/re-fetch or restart from the authoritative committed position before processing/committing later records. |
| Transactional visibility | Aborted/open input or output is consumed under an incompatible isolation policy. | Applicable transactional boundaries use committed visibility; non-transactional input is not falsely claimed to gain transaction semantics. |
| Transaction fencing | Concurrent logical producers share one transactional identity unintentionally, or a stale producer's fatal fencing is swallowed. | Identity scope and client-supported fencing match the ownership contract; unresolved/fatal outcomes do not become success. |
| Business ordering | Offset commits are safe but parallel jobs apply an older order-sensitive update after a newer update. | Serialize the relevant key, compare business versions, or prove the effects commute. Retry-topic detours preserve the required order contract. |
| Rebalance/lost ownership | Old generation reports completion or attempts final commit after assignment was lost. | Reject stale completion/commit authority, while an explicitly independent durable effect owner may safely finish its own accepted obligation. |
| Callback deadlock | Rebalance callback needs a lock held by a consuming call that cannot finish until the callback returns. | Consumer/callback ownership avoids the cycle; drain has a bounded fallback. A live HTTP endpoint is not evidence against the deadlock. |
| Resource pressure | Queue record count is small but fetch buffers, decoded payloads, active models or retained results exceed the container limit. | Admission considers all relevant memory owners and oversized-batch behavior; bounded process/parser execution preserves replay or durable rejection. |
| Decode/tombstone | Deserializer fails before the business handler, leaving no disposition; alternatively a valid tombstone is rejected as corruption. | Decode failure retains source identity and controlled recovery; valid deletion/null semantics follow the topic contract. |
| Retry/DLQ failure | Handoff is unavailable, or delivery is uncertain, yet source offset commits. | Source retains responsibility until durable acceptance. Successful handoff preserves identity, recovery owner and redrive policy. |
| Retry-budget reset | Restart resets attempts to zero and a poison record circulates forever. | The required budget/horizon survives the failure model and exhaustion has a durable, actionable disposition. |
| Idle vs wedged | Idle/paused or legitimately progressing work is restarted; alternatively a timer masks a stalled worker. | Health uses actual state/progress and bounded deadlines, not mandatory completion freshness or unrelated health-server heartbeats. |
| Shutdown | SIGTERM stops all client progress during a long drain, or forced kill is assumed impossible. | Stop admission, maintain necessary client progress during bounded drain, and verify replay after forced termination. |
| Retention/reset | Outage, compaction, offset expiry or restore removes needed history; reset silently begins at latest. | Explicit gap detection and an authorized recovery/loss policy; earliest cannot recreate deleted records. |
| Durability dependency | Consumer logic is safe but an acknowledged input/output can be lost under the required broker failure model. | Inspect relevant effective producer/topic settings and state the supported fault envelope; unknown cluster policy prevents an end-to-end durability claim. |

## Qualification boundaries

**Static review:** source and configuration can establish a reachable defect or a bounded safe control. It does not exercise broker/client fault behavior.

**Executable fixture evidence:** run unsafe and corrected versions against independently stated expected effects/offsets. Verify that intentionally removing the guard changes the outcome. A test must assert what persisted or remained recoverable, not merely that an exception was raised. These tests establish the modeled counterexample, not real Kafka reliability or an independently adjudicated semantic oracle.

**Model-backed skill evaluation:** the agent must discriminate source-backed positive, safe and neighboring cases using the actual canonical skill. Narrative cases and pinned line matches are weaker than independently checked semantic conclusions. Record missed defects and false positives; do not invent an accuracy score or infer improvement without comparable runs. Current EvalShot result limitations remain applicable.

**Target-runtime qualification:** use the supported client/broker/deployment configuration to test the relevant crash, uncertain-send, abort, rebalance, lost-owner, restart, dependency-outage and resource boundaries. Reconcile admitted input identities to durable successes, authorized rejections and recoverable pending/handoff work. Observe both missing outcomes and duplicate protected effects. Preserve business ordering where required. A single-broker test cannot qualify a multi-broker failover claim.

No stage automatically implies the next. Required but untested runtime guarantees remain unqualified. A happy path, a large test count, or successful skill loading is not a gold/platinum certificate. Keep fast deterministic tests routine and schedule expensive campaigns separately where the project's risk policy permits.
