# Postgres and Kafka fixture patterns

## Contents

- [Selection and lifetime scaffold](#selection-and-lifetime-scaffold)
- [Client URLs](#client-urls)
- [Readiness and administration](#readiness-and-administration)
- [Kafka and mixed environments](#kafka-and-mixed-environments)
- [Sources](#sources)

## Selection and lifetime scaffold

Adapt this scaffold to the project's pinned APIs and existing support layer.
`owned_postgres`, `DatabaseManager`, and `test_allocation` below describe project
adapters, not APIs supplied by this skill. Implement and test their stated contracts
before treating this as executable integration setup.

Keep adapter constructors side-effect free; acquire resources only inside the
protected startup methods/contexts so a constructor failure cannot bypass release.

```python
import os
from dataclasses import dataclass, field

import pytest
import pytest_asyncio


@dataclass(frozen=True)
class DatabaseEndpoint:
    url: str = field(repr=False)
    source: str  # "external" or "container"; not data-reset authority


@pytest.fixture(scope="session")
def database_endpoint():
    # Import the adapters from the project's test support module.
    raw = os.environ.get("DATABASE_URL")
    if raw is not None:
        # validate_asyncpg_url rejects blank/malformed/unsupported input;
        # it preserves credentials and compatible connection options.
        yield DatabaseEndpoint(validate_asyncpg_url(raw), "external")
        return

    # Neither this import nor Docker discovery occurs in external mode.
    from testcontainers.postgres import PostgresContainer

    # owned_postgres registers cleanup before starting and handles partial start.
    # Its context exit stops only the container it created.
    with owned_postgres(PostgresContainer, image="postgres:17-alpine") as pg:
        yield DatabaseEndpoint(validate_asyncpg_url(pg.get_connection_url()),
                               "container")


@pytest_asyncio.fixture
async def database(database_endpoint, test_allocation):
    # A settings/allocation fixture must also route application workers here.
    manager = DatabaseManager(database_endpoint.url, allocation=test_allocation)
    try:
        await manager.connect_and_check_ready(timeout=30.0)
        await manager.initialize_owned_state()
        yield manager
    finally:
        # Must tolerate connect/initialize failing midway. Internally arrange
        # cleanup in nested finally blocks so one failure cannot skip close.
        await manager.cleanup_and_close(timeout=10.0)
```

The endpoint is deliberately metadata, not a ready connection. Only the `database`
fixture yields a usable service; application consumers must depend on that readiness
boundary. No async client survives a temporary `asyncio.run()` loop. Retain the
default function loop for function clients/tests. For a genuinely shared async
pool, explicitly align fixture `scope`, fixture `loop_scope`, and consumer test
loop scope using the installed pytest-asyncio API.

Implement `owned_postgres` against the installed Testcontainers lifecycle. Register
release as soon as there is an owned Docker client/container, and handle a failure
inside `start()` or context entry. A bare `with PostgresContainer(...)` plus code
after the fixture's `yield` is not evidence of partial-start cleanup. Preserve the
original setup failure and separately surface any release failure. Use the project
image/version or digest; the image above is illustrative, not a mandated upgrade.

For immutable session metadata, `return` is also valid; `yield` is useful when its
fixture actually owns cleanup. Keep per-test workers dependent on `database` so
pytest tears workers down before removing the state they can still write.

## Client URLs

Where supported, `PostgresContainer(..., driver=None)` produces a driver-free URL.
Otherwise translate only the scheme at the adapter for the chosen client, using
an allowlist derived from project configuration. For example, a raw asyncpg
adapter can retain the exact suffix after the scheme:

```python
def asyncpg_scheme(url: str) -> str:
    scheme, marker, rest = url.partition("://")
    accepted = {
        "postgres", "postgresql", "postgresql+psycopg2",
        "postgresql+psycopg", "postgresql+asyncpg",
    }
    if not marker or scheme not in accepted or not rest:
        raise ValueError("Unsupported PostgreSQL connection URL")
    return "postgresql://" + rest
```

This is scheme translation only, not full URL or security validation. Validate
authority/database/options with the target client's contract before connecting.
Do not interpolate the URL into errors. Keep encoded passwords, bracketed IPv6,
database paths, and TLS query parameters intact; reject or deliberately translate
driver-specific options unsupported by the receiving client. A SQLAlchemy async
engine still needs its appropriate driver name, such as `postgresql+asyncpg`.

Prefer passing an immutable test settings object to the application and verifier.
If a legacy factory only reads the environment, place its construction and all
dependent cleanup within `pytest.MonkeyPatch.context()` and restore an owned
settings cache too. Do not request pytest's function-scoped `monkeypatch` fixture
from a session-scoped fixture. Do not mutate an import-time singleton after its
clients have already captured configuration.

## Readiness and administration

Readiness must check the path consumers actually use: authenticate with their
credentials, run a read-only query such as `SELECT 1`, and confirm required schema
capabilities after permitted initialization. Socket polling or `pg_isready` alone
does not prove those credentials or migrations work. Apply bounded readiness to
external services as well as containers.

The manager's contract is small and explicit:

| Operation | Required boundary |
| --- | --- |
| Connect/probe | Same DSN, credentials, TLS, and deadline as the test configuration; no secret diagnostics |
| Initialize | Use application migrations only inside the verified test allocation |
| Seed/read | Use production domain/schema contracts and the same allocation as background workers |
| Cleanup | Remove only owned state, including partial initialization; do not reset unrelated workers |
| Close | Always release clients/pools even if state cleanup fails; bound cancellation and shutdown |

An allocation must have an established test owner and namespace, not merely a
database name containing `test`. Use a provisioned dedicated database, isolated
schema, or contract-supported tenant/run identifier. Include run, worker, and test
identity where sharing can occur. A transaction rollback cannot undo independent
worker commits. Broad `TRUNCATE ... CASCADE` is acceptable only where exclusive
test ownership and its full dependency scope have been established in advance.

## Kafka and mixed environments

Resolve the project's bootstrap variable separately from `DATABASE_URL`; one
external value must not force all services into external mode. Defer
`from testcontainers.kafka import KafkaContainer` to Kafka's local branch and read
the mapped bootstrap value using the installed API (`get_bootstrap_server()` in
the documented module). Do not split a broker list with `split(":")`: multiple
brokers, IPv6, and advertised listener addresses need the Kafka client's parser.

Use the same authentication/TLS configuration for the app, admin readiness probe,
and verifier. Check broker metadata and expected topic/partition availability,
including reachable advertised endpoints. Keep topic provisioning/deletion inside
the established test allocation; do not rewrite or delete shared topics simply
because a test supplied their names. Derive application and verifier topic settings
from one test settings object. Confirm workers stop before topic cleanup.

Validate all-local and all-external configurations plus each supported mixed
configuration. Report unavailable combinations explicitly. A stub proving branch
selection cannot establish real broker/network/schema parity.

## Sources

Check these primary references against the repository's locked versions:

- [Pytest fixture teardown](https://docs.pytest.org/en/stable/how-to/fixtures.html)
- [Pytest monkeypatch context](https://docs.pytest.org/en/stable/how-to/monkeypatch.html)
- [pytest-asyncio fixture loop scope](https://pytest-asyncio.readthedocs.io/en/stable/reference/decorators/index.html)
- [pytest-xdist session fixtures and run identity](https://pytest-xdist.readthedocs.io/en/stable/how-to.html)
- [Testcontainers Postgres](https://testcontainers-python.readthedocs.io/en/latest/modules/postgres/README.html)
- [Testcontainers Kafka](https://testcontainers-python.readthedocs.io/en/latest/modules/kafka/README.html)
- [asyncpg connection options](https://magicstack.github.io/asyncpg/current/api/index.html)
- [Postgres TRUNCATE scope](https://www.postgresql.org/docs/current/sql-truncate.html)
