"""
Load test script for the baseline FastAPI service.

- Sends 200-300 requests, randomly distributed across the three endpoints.
- Uses a thread pool to simulate concurrent load.
- Reports p50/p95/p99 latency per endpoint and overall,
  plus achieved RPS -- useful for capacity estimation.

Usage:
    python load_test.py --base-url http://localhost:8000 --requests 250 --concurrency 20
"""

import argparse
import random
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

ENDPOINTS = [
    "/api/v1/fast",
    "/api/v1/slow",
    "/api/v1/average",
]


def hit_endpoint(client: httpx.Client, base_url: str, path: str) -> dict:
    start = time.perf_counter()
    try:
        resp = client.get(base_url + path, timeout=10.0)
        ok = resp.status_code == 200
    except Exception:
        ok = False
    elapsed_ms = (time.perf_counter() - start) * 1000
    return {"path": path, "ok": ok, "latency_ms": elapsed_ms}


def percentile(data: list, pct: float) -> float:
    if not data:
        return float("nan")
    data_sorted = sorted(data)
    k = (len(data_sorted) - 1) * (pct / 100)
    f = int(k)
    c = min(f + 1, len(data_sorted) - 1)
    if f == c:
        return data_sorted[f]
    return data_sorted[f] + (data_sorted[c] - data_sorted[f]) * (k - f)


def run_load_test(base_url: str, total_requests: int, concurrency: int):
    plan = [random.choice(ENDPOINTS) for _ in range(total_requests)]

    results = []
    wall_start = time.perf_counter()

    with httpx.Client() as client:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(hit_endpoint, client, base_url, path) for path in plan]
            for fut in as_completed(futures):
                results.append(fut.result())

    wall_elapsed = time.perf_counter() - wall_start
    return results, wall_elapsed


def report(results: list, wall_elapsed: float):
    total = len(results)
    ok_count = sum(1 for r in results if r["ok"])
    print(f"\nTotal requests: {total}  (success: {ok_count}, failed: {total - ok_count})")
    print(f"Wall time: {wall_elapsed:.2f}s  ->  achieved RPS: {total / wall_elapsed:.1f}\n")

    print(f"{'Endpoint':<20}{'count':<8}{'p50 ms':<10}{'p95 ms':<10}{'p99 ms':<10}{'avg ms':<10}")
    print("-" * 68)

    all_latencies = [r["latency_ms"] for r in results if r["ok"]]
    for ep in ENDPOINTS:
        lat = [r["latency_ms"] for r in results if r["ok"] and r["path"] == ep]
        if not lat:
            continue
        print(
            f"{ep:<20}{len(lat):<8}"
            f"{percentile(lat, 50):<10.1f}"
            f"{percentile(lat, 95):<10.1f}"
            f"{percentile(lat, 99):<10.1f}"
            f"{statistics.mean(lat):<10.1f}"
        )

    print("-" * 68)
    print(
        f"{'OVERALL':<20}{len(all_latencies):<8}"
        f"{percentile(all_latencies, 50):<10.1f}"
        f"{percentile(all_latencies, 95):<10.1f}"
        f"{percentile(all_latencies, 99):<10.1f}"
        f"{statistics.mean(all_latencies):<10.1f}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--requests", type=int, default=random.randint(200, 300))
    parser.add_argument("--concurrency", type=int, default=20)
    args = parser.parse_args()

    print(f"Running {args.requests} requests against {args.base_url} (concurrency={args.concurrency})")
    results, wall_elapsed = run_load_test(args.base_url, args.requests, args.concurrency)
    report(results, wall_elapsed)