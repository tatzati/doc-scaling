# Experiment: Phase 1 Baseline Stress Test

## Date

2026-09-06

## Hypothesis

The first Phase 1 bottleneck will appear in synchronous request handling or the
SQLAlchemy database connection pool before application CPU is saturated.

## System Under Test

- FastAPI application served by one Uvicorn process.
- macOS host with Apple M2 and 8 logical CPUs.
- Python 3.14.2.
- SQLite database at `scalability.db`.
- SQLAlchemy default connection pool: size 5, overflow 10.
- `PROCESSING_DELAY_SECONDS=0.25`.
- No Redis, RabbitMQ, MinIO, PostgreSQL container, or load balancer.
- The test client used `httpx.AsyncClient` with a 10-second request timeout.

This is a local Phase 1 stress test, not a production-capacity benchmark.

## Workload

The reusable harness is `loadtests/stress_test.py`.

For each concurrency level, it ran for 5 seconds after a 2-second warmup at
concurrency 1:

```sh
.venv/bin/python loadtests/stress_test.py \
  --duration 5 \
  --warmup 2 \
  --concurrency 1 10 25 50 100 \
  --path /health
```

The same sweep was then run against `GET /documents/1` after creating one
document.

A separate 50-request concurrent `POST /documents/1/process` workload measured
job submission behavior.

## Results: Health Endpoint

| Concurrency |    RPS | Success rate |       p50 |         p95 |         p99 |         Max |
| ----------: | -----: | -----------: | --------: | ----------: | ----------: | ----------: |
|           1 | 931.29 |         100% |   1.01 ms |     1.19 ms |     1.57 ms |    28.68 ms |
|          10 | 945.07 |         100% |   5.98 ms |    26.67 ms |    71.00 ms |   837.62 ms |
|          25 | 399.64 |         100% |  43.11 ms |   176.60 ms |   258.02 ms |   484.45 ms |
|          50 | 198.51 |         100% | 184.19 ms |   697.41 ms | 1,003.16 ms | 1,618.40 ms |
|         100 |  99.54 |         100% | 646.08 ms | 3,048.46 ms | 4,634.23 ms | 5,056.21 ms |

## Results: Database-Backed Read

| Concurrency |    RPS | Success rate |          p50 |          p95 |          p99 |          Max |
| ----------: | -----: | -----------: | -----------: | -----------: | -----------: | -----------: |
|           1 | 696.80 |         100% |      1.37 ms |      1.60 ms |      2.30 ms |     28.77 ms |
|          10 | 712.81 |         100% |      6.36 ms |     28.18 ms |    233.40 ms |    823.80 ms |
|          25 | 380.88 |         100% |     42.50 ms |    192.33 ms |    302.93 ms |    484.55 ms |
|          50 | 189.19 |         100% |    191.96 ms |    743.55 ms |  1,225.18 ms |  2,219.38 ms |
|         100 |  10.23 |        2.91% | 10,050.45 ms | 10,054.19 ms | 10,054.39 ms | 10,054.45 ms |

At concurrency 100, 100 requests timed out and only 3 returned status 200.

## Results: Job Submission

With 50 concurrent requests to `POST /documents/1/process`:

- 12 requests returned `202`.
- 38 requests timed out at the 10-second client timeout.
- The successful submissions had p50 latency of 100.68 ms.
- The successful submissions had maximum latency of 139.39 ms.
- Follow-up job polling also timed out during saturation.

## Observations

The API process stayed alive and recovered after load. A process sample after
the high-concurrency test showed approximately 0.2% CPU and 9.7 MiB RSS. This
was not a CPU-bound failure.

The Uvicorn process accumulated approximately 53 threads during the test. The
synchronous FastAPI handlers run through AnyIO's worker thread pool. Database
requests and in-process background jobs compete for this execution and database
capacity.

The decisive server-side evidence was this exception in the Uvicorn log:

```text
sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached,
connection timed out
```

The exception occurred while handling `GET /jobs/{job_id}`. The default pool
therefore allowed at most 15 checked-out connections before requests waited for
one and eventually timed out.

## Bottleneck

The first observed bottleneck is database connection-pool saturation under
concurrent database-backed work. The high-concurrency health results also show
request/threadpool queueing, but the database-backed endpoint fails much more
severely and emits a direct pool exhaustion error.

## Root Cause

Phase 1 uses synchronous SQLAlchemy sessions inside synchronous FastAPI
handlers, with the default SQLAlchemy pool configuration. At high concurrency,
requests accumulate in the thread pool and compete for a small SQLite connection
pool. The in-process background processing path adds more database sessions and
commits while jobs are running.

## What This Does Not Prove

- It does not establish PostgreSQL performance.
- It does not establish sustained production throughput.
- It does not compare multiple Uvicorn workers or horizontal instances.
- It does not prove that increasing the pool is the correct production fix.
- The PostgreSQL Docker comparison was not completed because the image pull was
  still in progress during this run.

SQLite is useful for this first reproducible local experiment, but the next
benchmark must use PostgreSQL and record pool settings explicitly.

## Next Experiment

Repeat the workload against PostgreSQL with:

1. A recorded SQLAlchemy pool size and overflow limit.
2. PostgreSQL connection and CPU metrics.
3. A bounded request load profile instead of an unbounded concurrency loop.
4. Separate measurements for API reads, document writes, and job submission.
5. A comparison of one Uvicorn worker versus multiple workers.

Then test whether pool tuning, async database access, or moving processing to a
real worker queue changes the limiting resource.
