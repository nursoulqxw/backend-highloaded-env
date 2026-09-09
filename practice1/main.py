"""
Baseline FastAPI service for latency/capacity lab.

Endpoints mirror the Spring Boot version:
  /api/v1/fast     -> sleep (simulated quick blocking call)
  /api/v1/slow     -> print/log work (simulated slower call)
  /api/v1/average  -> do_something() (mid-weight CPU work)

Run with:
    uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
"""

import time
import random
import logging

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Baseline Service")
logger = logging.getLogger("uvicorn")

# Exposes /metrics with request count + latency histograms (buckets),
# which Prometheus scrapes and Grafana visualizes (p50/p95/p99 via
# histogram_quantile queries, no code changes needed per-endpoint).
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/api/v1/fast")
def fast():
    """Simulated quick blocking call — short fixed sleep."""
    time.sleep(0.01)  # 10ms
    return {"endpoint": "fast", "status": "ok"}


@app.get("/api/v1/slow")
def slow():
    """Simulated slower call — does logging/print work + longer sleep."""
    for i in range(50):
        logger.info(f"slow endpoint work iteration {i}")
    time.sleep(0.15)  # 150ms
    return {"endpoint": "slow", "status": "ok"}


def do_something(n: int = 100_000) -> int:
    """Mid-weight CPU-bound work: sum of squares."""
    total = 0
    for i in range(n):
        total += i * i
    return total


@app.get("/api/v1/average")
def average():
    """Mid-weight endpoint — some CPU work, no artificial sleep."""
    result = do_something()
    return {"endpoint": "average", "status": "ok", "result_checksum": result % 997}


@app.get("/health")
def health():
    return {"status": "healthy"}