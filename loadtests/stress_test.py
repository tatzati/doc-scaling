"""Small repeatable HTTP stress test for the Phase 1 API."""

import argparse
import asyncio
import json
import statistics
import time
from collections import Counter

import httpx


async def request_once(client: httpx.AsyncClient, path: str, method: str) -> tuple[float, int | str]:
    started = time.perf_counter()
    try:
        response = await client.request(method, path)
        return time.perf_counter() - started, response.status_code
    except httpx.HTTPError as exc:
        return time.perf_counter() - started, type(exc).__name__


async def run_level(base_url: str, path: str, method: str, concurrency: int, duration: float) -> dict:
    latencies: list[float] = []
    outcomes: Counter[int | str] = Counter()
    stop_at = time.perf_counter() + duration
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)

    async with httpx.AsyncClient(base_url=base_url, timeout=10.0, limits=limits) as client:
        async def worker() -> None:
            while time.perf_counter() < stop_at:
                latency, outcome = await request_once(client, path, method)
                latencies.append(latency)
                outcomes[outcome] += 1

        started = time.perf_counter()
        await asyncio.gather(*(worker() for _ in range(concurrency)))
        elapsed = time.perf_counter() - started

    latencies.sort()
    request_count = len(latencies)
    successful = sum(count for outcome, count in outcomes.items() if outcome == 200)

    def percentile(percent: float) -> float:
        if not latencies:
            return 0.0
        index = min(int((percent / 100) * len(latencies)), len(latencies) - 1)
        return latencies[index] * 1000

    return {
        "concurrency": concurrency,
        "duration_seconds": round(elapsed, 3),
        "requests": request_count,
        "rps": round(request_count / elapsed, 2) if elapsed else 0.0,
        "success_rate": round(successful / request_count, 4) if request_count else 0.0,
        "p50_ms": round(percentile(50), 2),
        "p95_ms": round(percentile(95), 2),
        "p99_ms": round(percentile(99), 2),
        "max_ms": round(max(latencies) * 1000, 2) if latencies else 0.0,
        "mean_ms": round(statistics.mean(latencies) * 1000, 2) if latencies else 0.0,
        "outcomes": dict(outcomes),
    }


async def main(args: argparse.Namespace) -> None:
    print(json.dumps({"warmup": await run_level(args.base_url, args.path, args.method, 1, args.warmup)}))
    for concurrency in args.concurrency:
        result = await run_level(args.base_url, args.path, args.method, concurrency, args.duration)
        print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--path", default="/health")
    parser.add_argument("--method", default="GET")
    parser.add_argument("--warmup", type=float, default=2.0)
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--concurrency", type=int, nargs="+", default=[1, 10, 50, 100])
    asyncio.run(main(parser.parse_args()))
