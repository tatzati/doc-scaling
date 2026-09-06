# Scalability Lab

A reproducible document-processing API used to study throughput, latency, bottlenecks, and failure behavior.

Phase 1 establishes the smallest measurable system:

- FastAPI HTTP API
- SQLAlchemy persistence
- PostgreSQL in Docker Compose
- In-process background processing with a controllable delay
- Prometheus HTTP and job metrics
- JSON request logs
- API tests using the local SQLite fallback

The in-process worker is intentional. RabbitMQ, Redis, MinIO, OpenTelemetry, Grafana, and k6 are later experiment steps; adding them now would make the first baseline harder to attribute.

## Run locally

Requires Python 3.12+ and Docker.

```sh
cp .env.example .env
python3 -m venv .venv
. .venv/bin/activate
make install
make test
```

Start PostgreSQL and the API together:

```sh
make up
```

The API is available at `http://localhost:8000`. OpenAPI documentation is at `/docs`, and Prometheus metrics are at `/metrics`.

Stop the stack with:

```sh
make down
```

## Phase 1 API

| Method | Path                      | Purpose                               |
| ------ | ------------------------- | ------------------------------------- |
| `POST` | `/documents`              | Register document metadata            |
| `GET`  | `/documents`              | List documents with pagination        |
| `GET`  | `/documents/{id}`         | Fetch document metadata               |
| `POST` | `/documents/{id}/process` | Create an asynchronous processing job |
| `GET`  | `/jobs/{id}`              | Fetch job status                      |
| `GET`  | `/health`                 | Process health check                  |
| `GET`  | `/ready`                  | Database readiness check              |
| `GET`  | `/metrics`                | Prometheus exposition endpoint        |

## Measurement rule

No benchmark results belong in the README until they are generated under recorded conditions. The next phase should add a baseline load profile and capture p50, p95, p99, error rate, CPU, memory, and database connection behavior.
