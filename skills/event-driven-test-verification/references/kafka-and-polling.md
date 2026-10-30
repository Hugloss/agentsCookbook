# Kafka and polling patterns

Use these patterns to implement the smallest observer compatible with the
repository's installed client, schema, and integration boundary.

## Contents

- [Observation contract](#observation-contract)
- [Kafka arming and offsets](#kafka-arming-and-offsets)
- [Bounded state polling](#bounded-state-polling)
- [Cleanup and diagnostics](#cleanup-and-diagnostics)
- [Focused verification](#focused-verification)
- [Primary references](#primary-references)

## Observation contract

Establish these facts from production code before implementing an adapter:

| Question | Required decision |
| --- | --- |
| Which operation? | ID plus any scope needed to distinguish runs/attempts |
| Which result? | Production payload type and terminal success/failure states |
| Which source? | Resolved topic, endpoint, route, and authentication settings |
| When does observation begin? | Subscription/assignment and replay or cursor boundary |
| What survives a fast response? | Buffered observation until the caller knows the ID |
| What is the time budget? | One monotonic deadline; separate bounded cleanup |

Do not infer that every `status` field uses `completed` or `failed`, or that the
first event for a job is its final result. Use the existing model and domain
semantics. An acknowledgement may only mean a worker accepted the job.

The following is **adapter pseudocode**, not a drop-in Kafka API. Implement its
methods using the existing project's clients; do not copy names as a new public
framework. `close()` must handle partial startup and preserve any active error.

```python
deadline = monotonic_now() + configured_operation_timeout
observer = make_observer(resolved_test_settings)
try:
    await observer.start(deadline=deadline)
    await observer.arm(deadline=deadline)
    # arm() establishes the cursor and begins retaining relevant observations.
    operation_id = await trigger_work(deadline=deadline)
    result = await observer.wait_for_response(
        operation_id, deadline=deadline
    )
    assert_production_terminal_success(result)
finally:
    await observer.close(timeout=configured_cleanup_timeout)
```

Apply an outer deadline guard as well as client I/O timeouts. Do not rely only
on passing a number into an adapter that may ignore it. Where the trigger
returns a server-generated ID, retain intervening events so an immediate result
is still available after the trigger returns. Bound buffers and expose overflow
as an explicit observation failure rather than silently evicting needed events.

## Kafka arming and offsets

1. Use the actual configured topic and client security options. Confirm topic
   metadata, required partitions, and reachable advertised broker addresses.
   Connecting to a bootstrap socket does not prove this path works.
2. Choose one ownership strategy: an independent unique verification group, or
   explicit partition assignment where suitable. Never reuse the application's
   worker group: verification must not take partitions away from the application.
3. Establish the expected partition assignment. A nonempty assignment alone is
   insufficient if the response can land in another partition. Resolve starting
   positions before triggering work; use the installed client's documented
   assignment/position APIs rather than assuming `start()` always guarantees it.
4. Choose the replay boundary. For a fresh-only observation, capture end offsets
   and seek to them **before** the trigger. For retained/replayed responses,
   preserve the required earlier cursor and prove correlation excludes stale
   results. Never seek to the end after the response might have been published.
5. Begin observing, trigger work, and wait for the matching production outcome.
   Unrelated messages must not reset the timeout. If multiple operations share
   an observer, dispatch by identity; concurrent readers that discard each
   other's messages are not independent verifiers.
6. Handle a rebalance explicitly. Preserve already established observation
   boundaries and buffered responses, or fail with a useful diagnostic if the
   adapter cannot guarantee them. Do not silently reset all positions to latest.

`auto_offset_reset="latest"` is not an arming barrier. Aiokafka uses a valid
committed position when one exists; the reset policy applies when the position
is invalid. A reused group can therefore read old data or skip required data
despite an unchanged reset setting. A fresh group avoids inherited commits but
still needs assignment and position establishment before a fresh-only trigger.

Let the client parse bootstrap configuration. Do not split it with
`host, port = bootstrap_servers.split(":")`: multiple brokers and bracketed
IPv6 addresses require the client's supported representation.

Do not mutate or delete shared topics to clear a verifier. Keep topic lifecycle
in the test's infrastructure/state owner and use identity/cursor boundaries for
observation. Match the application's isolation level if transactional messages
are part of the contract.

## Bounded state polling

Prefer an existing completion handle or notification. When a real service only
offers a queryable state, poll the specific operation using its production
query/model. Use real elapsed time for real I/O; fake time is appropriate only
when the behavior under test and its clock are controlled together.

```text
deadline := monotonic_now() + operation_budget
repeat:
    remaining := deadline - monotonic_now()
    if remaining <= 0: fail with bounded diagnostics
    observation := read(operation_id, timeout <= remaining)
    validate the applicable production payload contract
    if the matching operation has terminal failure: fail immediately
    if the matching operation has required terminal success: return observation
    if an unexpected nontransient read/contract error occurs: propagate it
    await a short interval bounded by time remaining
```

Treat cancellation as cancellation, not as “no result yet.” Retry only errors
whose transient nature is established for this client/protocol. Do not retry
invalid credentials, invalid matching payloads, terminal domain failures, or
arbitrary exceptions until the deadline hides the original cause.

Use a monotonic clock and an outer timeout/cancellation mechanism appropriate
to the project's Python/runtime version. In Python 3.11+, `asyncio.timeout_at`
can enforce a deadline expressed in the running event loop's clock. Keep read,
decode, and sleep inside the budget. If a callback raises its own `TimeoutError`,
distinguish that from expiry of the outer budget when the difference affects
diagnosis or retry policy.

Negative assertions need their own explicit contract: absence during a bounded
observation window proves only that window. Do not report “never published”
without a completion/barrier guarantee that closes future publication.

## Cleanup and diagnostics

Register ownership as resources are acquired. Make partial-start cleanup close
any created client and cancel and await any owned reader task. If a library's
context-manager entry fails, establish whether it cleans itself up; do not rely
on an exit method that may never run. Do not leave readers active after timeout.

Give cleanup a bounded budget distinct from the expired wait budget. Preserve
the original test or cancellation failure and surface any cleanup failure as
additional evidence; do not mask it with a generic timeout. Avoid broad shields
or exception suppression that leave background work running indefinitely.

Useful timeout evidence includes elapsed time, expected operation identity when
safe to disclose, topic/partition assignment, starting/current offsets, message
counts, and the last relevant state. Redact credentials and sensitive payloads;
do not dump entire connection strings, message bodies, or unbounded logs.

## Focused verification

Choose cases according to the changed behavior:

- Emit a response immediately after trigger; verify the prearmed observer sees
  it, including when it precedes the trigger's returned ID.
- Supply unrelated events and a stale run/attempt; neither may satisfy the
  operation or extend its deadline. A matching valid event must still succeed.
- Supply matching intermediate, terminal failure, and malformed payloads;
  preserve the production distinction instead of treating all as eventual success.
- Exhaust the wait budget or cancel startup; verify clients/tasks are released.
- Exercise shared-observer routing or rebalances only when the adapter supports
  those paths. Verify the actual broker path separately from fake-client tests.

Do not invent a universal response schema or claim live integration evidence
from these synthetic cases.

## Primary references

- [Aiokafka consumer positions, groups, and offsets](https://aiokafka.readthedocs.io/en/latest/consumer.html).
- [Aiokafka consumer API](https://aiokafka.readthedocs.io/en/latest/api.html).
- [Kafka advertised listener configuration](https://kafka.apache.org/40/configuration/broker-configs/#advertised.listeners).
- [Python asyncio timeouts and cancellation](https://docs.python.org/3/library/asyncio-task.html#timeouts).
- [Pytest fixture teardown and safe structure](https://docs.pytest.org/en/stable/how-to/fixtures.html#teardown-cleanup-aka-fixture-finalization).

Check installed versions before copying client methods; these references define
the underlying contracts, not the project's adapter implementation.
