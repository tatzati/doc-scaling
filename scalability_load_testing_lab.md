# Scalable Web System Load-Testing Lab

## Purpose

Build a serious, reproducible GitHub project whose primary goal is to learn and demonstrate real scalability engineering.

This is **not** a CRUD portfolio app. The project should intentionally create bottlenecks, measure them, fix them, and document the results.

The final repository should let another engineer reproduce experiments such as:

- increasing request throughput from hundreds to thousands of requests/second
- identifying database connection exhaustion
- measuring p50/p95/p99 latency
- observing CPU, memory, database, queue, and cache behavior
- introducing asynchronous processing and backpressure
- testing horizontal scaling
- comparing system behavior before and after optimizations
- documenting failures and the engineering decisions used to resolve them

The project should prioritize **measured evidence over impressive-sounding claims**.

---

# 1. Core Project Idea

Build a small but realistic document-processing API.

The system should support:

1. Creating a document-processing job.
2. Uploading or registering a document.
3. Querying document/job status.
4. Performing synchronous API operations.
5. Performing asynchronous background processing.
6. Persisting metadata in PostgreSQL.
7. Using Redis for caching.
8. Using RabbitMQ for background jobs.
9. Storing document artifacts in object storage locally via an S3-compatible service such as MinIO.
10. Exposing metrics and traces.
11. Running repeatable load tests.
12. Producing benchmark reports.

The application itself is deliberately simple.

The engineering laboratory around it is the real project.

---

# 2. Initial Architecture

Start with:

```text
                    ┌───────────────┐
                    │    k6 /       │
                    │ Load Generator│
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │     API       │
                    │   FastAPI     │
                    └───────┬───────┘
                            │
              ┌─────────────┼──────────────┐
              │             │              │
              ▼             ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │PostgreSQL│  │  Redis   │  │ RabbitMQ │
        └──────────┘  └──────────┘  └────┬─────┘
                                         │
                                         ▼
                                   ┌───────────┐
                                   │  Workers  │
                                   └─────┬─────┘
                                         │
                                         ▼
                                    ┌─────────┐
                                    │  MinIO  │
                                    └─────────┘


Observability:

Application
    │
    ├── Prometheus metrics ──► Prometheus ──► Grafana
    │
    └── OpenTelemetry traces ─► Tempo
```

Do not introduce Kubernetes initially.

Do not introduce microservices initially.

Do not optimize prematurely.

The first objective is to establish a measurable baseline.

---

# 3. Recommended Technology Stack

## Application

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- Uvicorn/Gunicorn as appropriate

## Data

- PostgreSQL

## Cache

- Redis

## Messaging

- RabbitMQ

## Object Storage

- MinIO

## Load Testing

- k6

## Metrics

- Prometheus

## Dashboards

- Grafana

## Distributed Tracing

- OpenTelemetry
- Grafana Tempo

## Logs

Start with structured JSON application logs.

Later consider Loki if it provides useful learning value.

## Local orchestration

- Docker
- Docker Compose

---

# 4. Repository Structure

Aim for something approximately like:

```text
scalability-lab/
│
├── app/
│   ├── api/
│   ├── db/
│   ├── models/
│   ├── services/
│   ├── workers/
│   ├── cache/
│   ├── messaging/
│   ├── storage/
│   ├── telemetry/
│   └── main.py
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── loadtests/
│   ├── scenarios/
│   ├── datasets/
│   └── results/
│
├── infrastructure/
│   ├── docker/
│   ├── prometheus/
│   ├── grafana/
│   ├── tempo/
│   └── rabbitmq/
│
├── benchmarks/
│   ├── baseline/
│   ├── experiments/
│   └── reports/
│
├── docs/
│   ├── architecture/
│   ├── experiments/
│   ├── incidents/
│   └── decisions/
│
├── docker-compose.yml
├── Makefile
├── README.md
└── pyproject.toml
```

Keep infrastructure configuration version-controlled.

Every meaningful experiment should eventually have a corresponding document under `docs/experiments/`.

---

# 5. Phase 1 — Build the Smallest Working System

Create a minimal FastAPI service with PostgreSQL.

Implement endpoints such as:

```text
POST   /documents
GET    /documents/{id}
GET    /documents
POST   /documents/{id}/process
GET    /jobs/{id}
GET    /health
GET    /ready
```

Initially, document processing can be artificial.

For example:

```text
POST /documents/{id}/process
```

creates a job that performs simulated CPU/I/O work.

The goal is not realistic document extraction yet.

The goal is to create a controllable workload.

---

# 6. Instrument Everything From the Beginning

Observability is a first-class requirement.

Do not add it after load testing.

## Metrics

Expose Prometheus metrics for at least:

### HTTP

- request count
- request duration
- request rate
- response status
- request size
- response size

Break down latency by:

- endpoint
- HTTP method
- status code

Avoid high-cardinality labels such as user ID or request ID.

### Database

Track:

- connection pool utilization
- active connections
- waiting connections
- query duration
- transaction duration
- query errors

### Redis

Track:

- cache hits
- cache misses
- command latency
- connection count

### RabbitMQ

Track:

- queue depth
- messages published
- messages consumed
- consumer count
- processing duration
- failed jobs
- retry count

### Workers

Track:

- active workers
- jobs processed
- jobs failed
- job duration
- queue wait time

### System

Track:

- CPU
- memory
- disk
- network

---

# 7. Latency Percentiles

Never rely only on averages.

Every load-testing report should include:

```text
p50
p90
p95
p99
max
```

Example:

```text
                 Baseline
p50                85 ms
p90               140 ms
p95               210 ms
p99               480 ms
max             1,920 ms
```

The tail matters.

A system with a 100ms average but a 5-second p99 can feel terrible to users.

---

# 8. Distributed Tracing

Instrument requests with OpenTelemetry.

A request should be traceable approximately like:

```text
HTTP Request
    │
    ├── FastAPI handler
    │
    ├── PostgreSQL query
    │
    ├── Redis lookup
    │
    └── RabbitMQ publish
```

For asynchronous jobs:

```text
POST /documents/{id}/process
        │
        ▼
RabbitMQ publish
        │
        ▼
Worker receives message
        │
        ├── PostgreSQL
        ├── MinIO
        └── processing
```

The goal is to answer:

> "Why did this request take 1.8 seconds?"

without guessing.

---

# 9. Structured Logging

Use JSON logs.

Include fields such as:

```json
{
  "timestamp": "...",
  "level": "INFO",
  "service": "api",
  "environment": "local",
  "request_id": "...",
  "trace_id": "...",
  "method": "GET",
  "path": "/documents/123",
  "status_code": 200,
  "duration_ms": 42
}
```

Never log secrets.

Never log sensitive document contents.

---

# 10. Grafana Dashboard

Create dashboards that answer:

## API

- Requests/sec
- Error rate
- p50 latency
- p95 latency
- p99 latency

## PostgreSQL

- CPU
- connections
- pool saturation
- slow queries
- transactions/sec

## Redis

- hit rate
- misses
- latency

## RabbitMQ

- queue depth
- consumer count
- processing rate
- oldest message age

## Workers

- active workers
- jobs/sec
- processing latency
- failures

## Host

- CPU
- memory
- disk
- network

The dashboard should make bottlenecks visually obvious.

---

# 11. Establish a Baseline

Before optimizing anything, run a controlled test.

Example k6 scenario:

```text
1 minute   10 VUs
2 minutes  25 VUs
2 minutes  50 VUs
2 minutes  100 VUs
```

Record:

```text
RPS
p50
p95
p99
error rate
CPU
memory
DB connections
DB CPU
queue depth
```

Store the result.

Do not change the system before establishing this baseline.

---

# 12. Experiment 1 — Find the First Bottleneck

Increase load gradually.

For example:

```text
100 RPS
250 RPS
500 RPS
750 RPS
1,000 RPS
```

At each stage record the same measurements.

Determine what fails first.

Possibilities:

- application CPU
- database CPU
- database connections
- slow queries
- Redis
- RabbitMQ
- network
- worker capacity

Do not assume the answer beforehand.

---

# 13. Experiment 2 — Database Connection Exhaustion

Intentionally create a constrained connection pool.

Example:

```text
pool size = 5
max overflow = 0
```

Load the application.

Observe:

```text
request latency ↑
waiting connections ↑
timeouts ↑
```

Then increase capacity and/or fix query behavior.

Document:

```text
Problem
Evidence
Root cause
Change
Result
Trade-offs
```

This is an important engineering exercise because it mirrors real production failures.

---

# 14. Experiment 3 — N+1 Query Problem

Create an endpoint that intentionally performs N+1 queries.

Measure:

```text
query count
DB CPU
request latency
```

Then replace it with an efficient query strategy.

Document the before/after result.

Example target format:

```text
Requests/query:
101 → 2

p95:
850ms → 120ms

DB CPU:
78% → 31%
```

Do not fabricate numbers.

The actual experiment determines the numbers.

---

# 15. Experiment 4 — Add Redis Caching

Select a read-heavy endpoint.

Measure:

```text
without cache
with cache
```

Track:

- p95 latency
- DB queries
- DB CPU
- cache hit ratio
- memory usage

Then discuss cache invalidation and stale data.

---

# 16. Experiment 5 — Synchronous vs Asynchronous Processing

Create a deliberately expensive operation.

Version A:

```text
HTTP request
    ↓
processing
    ↓
response
```

Version B:

```text
HTTP request
    ↓
RabbitMQ
    ↓
202 Accepted
    ↓
worker
    ↓
processing
```

Compare:

- API latency
- throughput
- queue depth
- worker utilization
- failure behavior
- user-facing response time

This experiment should demonstrate why asynchronous systems exist.

---

# 17. Experiment 6 — Horizontal Scaling

Run:

```text
1 API instance
2 API instances
4 API instances
```

Load test each configuration.

Measure:

```text
maximum sustainable RPS
p95 latency
CPU per instance
total resource usage
error rate
```

Look for diminishing returns.

For example:

```text
1 instance → 700 RPS
2 instances → 1,350 RPS
4 instances → 2,100 RPS
```

The important lesson is that doubling application servers does not necessarily double throughput.

Find out why.

---

# 18. Experiment 7 — Queue Backpressure

Make workers intentionally slower than incoming jobs.

Example:

```text
incoming = 500 jobs/sec
processing = 300 jobs/sec
```

Watch the queue grow.

Measure:

- queue depth
- job wait time
- processing time
- memory
- failure rate

Then add worker capacity.

Determine the point at which the system becomes stable.

This is a core distributed-systems concept.

---

# 19. Experiment 8 — Failure Testing

Introduce controlled failures.

Examples:

- kill a worker
- restart PostgreSQL
- stop Redis
- pause RabbitMQ
- introduce artificial latency
- force database timeouts
- make an external dependency return errors

Observe:

- error rates
- retries
- recovery time
- queue behavior
- data consistency

Document the incident as a mini postmortem.

---

# 20. Experiment 9 — Retry Storm / Thundering Herd

Create a dependency that becomes slow or unavailable.

Allow naive retries.

Observe what happens.

Then implement:

- exponential backoff
- jitter
- retry limits
- circuit breaking where appropriate

Measure the difference.

This is an especially valuable interview discussion because it demonstrates understanding of failure amplification.

---

# 21. Experiment 10 — Capacity Planning

Once the system is stable, determine:

> How much traffic can one instance handle while maintaining a chosen SLO?

Define an example SLO:

```text
99% of requests < 500ms
error rate < 1%
```

Then determine:

```text
maximum sustainable RPS
```

Use that to estimate required capacity.

Example:

```text
1 instance = 700 sustainable RPS

Expected traffic = 4,000 RPS

Required theoretical capacity:
4000 / 700 = 5.7

Therefore:
6 instances minimum
7+ recommended for headroom
```

The numbers should come from your actual benchmarks.

---

# 22. Benchmarking Rules

Every benchmark should specify:

```text
Git commit
machine configuration
Docker configuration
database configuration
dataset size
test duration
load profile
concurrency
environment
```

Do not compare two results if the test conditions changed significantly.

Whenever possible, repeat each test multiple times.

Record:

```text
median
best
worst
```

---

# 23. What Counts as a Real Achievement?

Only claim metrics that have a reproducible basis.

Good:

> Increased sustained throughput from 620 RPS to 1,850 RPS during controlled k6 load testing.

Better:

> Increased sustained throughput 3× while maintaining p95 latency below 500ms.

Excellent:

> Increased sustained throughput 3× (620 → 1,850 RPS) while maintaining p95 latency below 500ms by eliminating N+1 queries and introducing Redis caching.

Bad:

> Built a highly scalable API capable of millions of requests.

unless you actually demonstrated it.

---

# 24. The Experiment Record

Every major experiment should use this structure:

```markdown
# Experiment: Database Connection Pool Exhaustion

## Hypothesis

## Initial Configuration

## Load Profile

## Baseline

## Observations

## Bottleneck

## Root Cause

## Change

## Result

## Trade-offs

## What I Learned

## Reproduction

## Metrics
```

The goal is to create a history of engineering decisions.

---

# 25. Incident Reports

When something breaks, document it.

Example:

```markdown
# Incident: PostgreSQL Connection Exhaustion

## Symptoms

API p99 latency increased dramatically.

## Impact

Requests began timing out above X RPS.

## Detection

Grafana showed connection-pool saturation.

## Investigation

...

## Root Cause

...

## Resolution

...

## Prevention

...

## Metrics

Before:
...

After:
...
```

These documents may become some of the strongest material in the repository.

---

# 26. GitHub README

The README should eventually contain:

## Project

One-paragraph explanation.

## Architecture

Architecture diagram.

## Stack

Technology list.

## Observability

Explain:

- Prometheus
- Grafana
- OpenTelemetry
- Tempo
- structured logs

## Load Testing

Explain how tests are executed.

## Results

Show benchmark tables.

Example:

| Experiment         |  Before |     After | Improvement |
| ------------------ | ------: | --------: | ----------: |
| API p95            |   850ms |     190ms |         78% |
| Throughput         | 620 RPS | 1,850 RPS |        3.0× |
| DB queries/request |     101 |         2 |         98% |
| Deployment time    |     12m |        4m |         67% |

Only populate this table with actual measured results.

## Failure Experiments

Link to incident reports.

## Lessons Learned

Summarize the most important engineering findings.

---

# 27. What NOT to Do

Do not:

- start with Kubernetes
- build 10 microservices
- spend weeks building a frontend
- optimize without measurements
- claim traffic you didn't generate
- use fake benchmark numbers
- benchmark on different hardware and pretend the results are directly comparable
- add every observability product available
- turn the project into a generic e-commerce clone
- focus on making the codebase huge

The project should remain relatively small.

The complexity should come from **load, concurrency, failure, and measurement**.

---

# 28. Definition of Done

The project is successful when you can demonstrate all of the following:

Phase 1 is complete for the items marked below. The current baseline intentionally
uses in-process background processing and does not yet include Redis, RabbitMQ,
MinIO, distributed tracing, dashboards, or k6-based load testing. A local SQLite
baseline stress test and initial database connection-pool bottleneck experiment
are documented separately. The Phase 1 test suite passes 5 tests, and the
project installs reproducibly with `pip install -e '.[test]'`.

### Application

- [x] FastAPI application works, including document and job endpoints
- [x] PostgreSQL persistence is configured in Docker Compose
- [ ] Redis works
- [ ] RabbitMQ works
- [ ] MinIO works
- [x] In-process background document processing works
- [ ] RabbitMQ background workers work

### Observability

- [x] Prometheus HTTP and job metrics
- [ ] Grafana dashboards
- [ ] OpenTelemetry instrumentation
- [ ] Distributed traces
- [x] Structured JSON application logs
- [ ] Request correlation

### Load Testing

- [ ] k6 test suite
- [x] Local baseline stress benchmark with p50, p95, p99, max, RPS, and error rate
- [x] Increasing-concurrency benchmark from 1 to 100 concurrent requests
- [x] Initial database connection-pool bottleneck experiment
- [ ] Cache experiment
- [ ] Async processing experiment
- [ ] Horizontal scaling experiment
- [ ] Queue/backpressure experiment
- [ ] Failure experiment
- [ ] Retry/thundering-herd experiment

### Documentation

- [ ] Architecture diagram
- [x] Benchmark methodology recorded for the local stress experiment
- [x] Initial experiment report
- [ ] Incident reports
- [ ] Capacity analysis
- [x] Phase 1 README with setup and API documentation
- [ ] Final README with benchmark results and experiment links

---

# 29. Final Goal

The finished repository should allow you to have conversations like:

> "I started with a single FastAPI instance backed by PostgreSQL. Under load, I discovered database connection saturation before the application CPU became the limiting factor. I instrumented the system with Prometheus and OpenTelemetry, identified the bottleneck using traces and connection-pool metrics, optimized the query path, and then introduced Redis. That moved the bottleneck to a different part of the system. I then introduced RabbitMQ and worker scaling to handle asynchronous workloads. Eventually I load-tested horizontal scaling and determined the sustainable capacity of the system under a defined latency SLO."

That is the level of understanding this project is designed to produce.

The objective is **not** to prove that you can build a website.

The objective is to develop the ability to answer:

> **"What happens when this system gets pushed beyond its limits, how do I know what broke, and what engineering change actually fixes it?"**

That is the core of the scalability experience this project is intended to build.
