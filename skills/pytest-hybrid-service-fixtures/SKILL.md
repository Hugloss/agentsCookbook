---
name: pytest-hybrid-service-fixtures
description: Builds fast pytest fixtures for local containers, external services, and mixed environments with safe cleanup.
license: MIT
---

# Pytest Hybrid Service Fixtures

Construct or refactor the requested integration fixtures. Own the transformation
from environment-specific setup to one service contract with explicit provisioning
and cleanup ownership. Optimize the test code by removing avoidable service startup,
schema rebuilding, data preparation, and waiting. Keep application behavior,
isolation, and integration assertions intact.

## INVARIANT

> **Selecting a local container or an external endpoint changes provisioning, not
> the tested service contract, readiness requirement, or isolation guarantee.**

Borrow an external service unless a separately established test allocation grants
ownership. A connection URL alone never grants permission to migrate, truncate,
drop, or stop everything reachable through that connection.

## ESTABLISH THE BOUNDARY

Inspect the relevant `conftest.py` chain, fixture consumers, settings construction,
dependency lock, application migrations, background workers, and CI service inputs.
Record the requested services, supported versions, endpoint variables, client URL
formats, resource owner, state namespace, and teardown order. Expand inspection to
directly affected consumers; do not remove an inconvenient mode from scope after
it fails.

Use the project's existing configuration and administrative owners. Read
[Postgres and Kafka patterns](references/postgres-and-kafka.md) when adapting
Python APIs, async lifetimes, URL handling, or a concrete fixture graph.

## TRANSFORM

1. **Resolve each service independently before constructing settings or clients.**
   Use its explicitly configured external endpoint; otherwise provision its local
   container. Support mixed selections, such as external Postgres and local Kafka.
   Reject a present but empty, malformed, unauthorized, or unreachable endpoint;
   never silently fall back after an explicit selection fails. Keep any documented
   skip policy visible as a skip, not successful integration coverage.

2. **Share expensive infrastructure only as far as isolation permits.** Prefer
   session-scoped containers/endpoints and function-scoped mutable state. Pytest
   session scope lasts one pytest invocation, per worker under xdist; parametrized
   fixtures can create multiple instances within that scope. Give concurrent runs,
   workers, and tests distinct allocations where they can interfere. If the schema
   is safely reusable, prepare/migrate a worker-owned database once and reset only
   test state between tests. Retain narrower containers/schemas for lifecycle or
   migration tests and state that cannot be reset safely. Session scope does not
   imply reuse across separate pytest runs or a live async client shared by all tests.

3. **Keep the external path independent of Docker.** Import Testcontainers and
   create Docker clients only inside the local branch. Avoid global autouse startup
   for tests that do not need services. Use mapped endpoints from the container API;
   do not assume `localhost` or fixed host ports in a remote Docker environment.
   Return the same endpoint/configuration shape in both branches.

4. **Adapt configuration at the actual client boundary.** Preserve TLS/auth options,
   credentials, escaping, database paths, and IPv6. A raw asyncpg DSN and a
   SQLAlchemy async-engine URL are different contracts. Do not globally remove
   driver suffixes or rewrite production settings. Inject test settings explicitly;
   if environment overrides are necessary, restore them and any owned settings
   cache after dependent clients stop. Read topic names from that same settings
   object, including any allocated test namespace.

5. **Require functional readiness before yielding usable resources.** Use the
   pinned library's wait support plus the application client's protocol check in
   both modes. Authenticate and query Postgres; obtain Kafka metadata and required
   partition leaders through reachable advertised listeners. An open TCP socket
   is only preliminary evidence. Bound the complete probe and each attempt using
   a monotonic deadline; retry identified transient failures, not arbitrary
   exceptions or configuration/authentication defects. Redact diagnostics.

6. **Separate service lifetime from test state.** Put migrations, seeding, and
   cleanup SQL in existing fixture/support methods or a small administrative owner.
   A new Manager class is optional; moving unrestricted `TRUNCATE ... CASCADE`
   behind a method does not establish isolation. Initialize only a dedicated test
   database/schema/allocation. Route application workers into that same allocation.
   Rollback is sufficient only if all relevant writes participate in its transaction;
   workers committing on other connections need their own bounded cleanup.
   Define per-test reset separately from session teardown: closing connections or
   dropping the container at session end does not isolate earlier tests. Establish
   the required starting state for each test, and do not reuse an allocation whose
   cleanup failed without restoring that state.

7. **Protect every acquisition, including failed setup.** Use `yield` with
   `try/finally`, context managers, or correctly registered finalizers. Code after
   `yield` does not run if setup fails before reaching it. Verify partial-start
   cleanup of a context manager whose entry can fail. Stop and join test workers,
   clean only owned state, close clients/pools, then release owned containers.
   Close borrowed-service clients too, but leave the borrowed service running.
   Pure immutable metadata fixtures may simply return a value.

8. **Keep live async objects on their owning loop.** Prefer synchronous session
   provisioning and function-scoped `pytest_asyncio` clients/managers. Do not retain
   a pool/task created by `asyncio.run()` after that call closes its loop. If sharing
   a live async client is necessary, align fixture and consumer loop scopes with the
   installed pytest-asyncio version and close it on that loop. Check fake responses
   against inspected production types/serialization rather than an assumed schema.

## PROVE THE TRANSFORMATION

Choose checks from the supported contract before editing. Exercise the applicable
local, external, and mixed paths with the same behavioral assertions. Include the
boundaries that could invalidate the change:

- external-only selection without Docker imports, probes, or startup;
- explicit endpoint failure without container fallback;
- readiness/initialization failure after acquisition, with cleanup observed;
- isolated tests/workers and unchanged borrowed data outside the allocation;
- settings restoration and async client shutdown on the correct loop.

Apply the reference's code-level speed choices directly. Do not make timing runs,
benchmarks, counters, or performance reports prerequisites for these improvements.
Verify the changed fixture behavior and preserve test coverage and assertions.
Separate helper/fake checks from real service runs. If Docker, credentials, or a
dedicated external allocation are unavailable, complete the inspectable work and
report those modes as unverified; never infer parity from one passing mode.

## DO NOT TRANSFORM

Do not broaden this task into general test or production architecture cleanup.
Keep deliberate lifecycle tests, legitimate function-scoped resources, direct
configuration injection, and existing safe administrative helpers. Do not add a
container to a unit test or invent a Manager hierarchy solely for naming uniformity.

This construction workflow is standalone; neighboring reviews are optional.
`repeated-test-setup-review` owns unnecessary construction cost;
`test-state-contamination-review` owns cross-test state leaks;
`test-isolation-boundary-review` owns unrelated effects forced into local tests;
`resource-lifetime-review` owns general acquire/use/release defects.
Use `event-driven-test-verification` to construct completion observations after
service provisioning is correct. Reconcile a shared cause into one correction.

## OUTPUT

Report the inspected fixture/consumer scope, endpoint-selection rules, ownership
and namespace boundary, repeated work removed, changes made, and functional
validation by mode with actual results.
For inspection-only requests, return a bounded `FINDING`, `CLEAN`, `LEAVE ALONE`,
or `INSUFFICIENT EVIDENCE`: prove a contract violation before reporting a finding;
support clean/leave-alone conclusions from the complete declared scope; preserve
uninspected paths as unknown. For implementation, distinguish completed edits from
verified behavior and unresolved modes. Describe the implemented optimizations
without inventing speedup figures; keep unverified environments explicit.
