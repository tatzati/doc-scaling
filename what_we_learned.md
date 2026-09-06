# What We Learned

This is the running learning log for the scalability lab. It records what has
actually been implemented or observed so far. No performance claims belong here
until they are backed by reproducible measurements.

## Phase 1 Lessons

### Start with a small, measurable system

The first useful version does not need every production component. A single
FastAPI application, SQLAlchemy persistence, a controllable processing delay,
Prometheus metrics, structured logs, and tests are enough to establish a system
that can be measured before it is optimized.

Adding Redis, RabbitMQ, MinIO, Grafana, OpenTelemetry, and k6 immediately would
make the first bottleneck harder to attribute. They should be introduced as
separate experiments.

### Observability belongs in the baseline

Metrics and logs were included from the beginning rather than treated as a
later enhancement. The API exposes HTTP request counters and duration metrics,
job counters and duration metrics, and JSON request logs. This gives the next
experiments a way to explain behavior instead of relying only on user-visible
latency.

### Separate production dependencies from test dependencies

PostgreSQL is configured for Docker Compose, while the API tests use a local
SQLite database fallback. This keeps the test suite fast and self-contained,
while preserving the production-shaped PostgreSQL configuration for integration
and load testing.

That distinction must remain explicit: passing SQLite tests does not prove that
PostgreSQL behavior, connection pooling, or query performance has been tested.

### Packaging configuration is part of reproducibility

The initial editable install failed because setuptools interpreted both `app`
and `loadtests` as top-level packages. Explicit package discovery with
`include = ["app*"]` fixed the problem.

A project is not reproducible if a fresh environment cannot install it with the
same command documented for contributors.

### Generated local state must stay out of git

Running the SQLite-backed tests generated `scalability.db`. The database was
removed from the repository and `*.db` was added to `.gitignore`. Test runs and
local services can create useful state without that state belonging in source
control.

### Documentation should track evidence

The Definition of Done now separates completed Phase 1 foundations from later
experiments. The README deliberately contains no benchmark numbers yet. Future
results should include the load profile, environment, configuration, commit,
and latency percentiles needed for another engineer to reproduce them.

## Evidence So Far

- Phase 1 test suite: 5 tests passing.
- Editable installation: `pip install -e '.[test]'` succeeds.
- Python source compilation: succeeds with `compileall`.
- GitHub repository: `https://github.com/tatzati/doc-scaling`.
- A local Phase 1 stress test is recorded in
  `docs/experiments/phase-1-baseline-stress-test.md`.
- The first observed bottleneck was SQLAlchemy connection-pool saturation: the
  default pool reached `size 5 + overflow 10` under concurrent database work.
- At concurrency 100, the SQLite-backed document read achieved 10.23 RPS with
  2.91% success; 100 requests hit the 10-second client timeout.
- The server stayed alive and used approximately 0.2% CPU in a post-test
  sample, so this run did not indicate CPU exhaustion.
- These are local SQLite observations, not PostgreSQL capacity claims.

## Questions for the Next Phase

- What is the baseline throughput and p50/p95/p99 latency under a recorded load
  profile?
- Which resource becomes the first bottleneck: application CPU, database CPU,
  database connections, or another dependency?
- How does the system change when asynchronous work moves from in-process tasks
  to RabbitMQ workers?
- Which metrics and traces are needed to explain the first bottleneck without
  guessing?
