"""API service: public entrypoint that delegates the work to the worker over HTTP."""
import os
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Query, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

WORKER_URL = os.getenv("WORKER_URL", "http://worker:8000")
WORKER_TIMEOUT_S = float(os.getenv("WORKER_TIMEOUT_S", "2"))
UNTRACKED_PATHS = {"/healthz", "/metrics"}  # keep probe/scrape traffic out of request metrics

REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)
WORKER_CALLS = Counter("worker_calls_total", "Calls from api to worker", ["outcome"])

client = httpx.AsyncClient(timeout=WORKER_TIMEOUT_S)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await client.aclose()


app = FastAPI(title="api", lifespan=lifespan)


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    if request.url.path in UNTRACKED_PATHS:
        return await call_next(request)
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        path = route.path if route else "unmatched"  # template, not raw path: bounded cardinality
        REQUESTS.labels(request.method, path, str(status)).inc()
        LATENCY.labels(request.method, path).observe(time.perf_counter() - start)


@app.get("/healthz")
def healthz():
    # Liveness/readiness of this process only; deliberately does not depend on the worker.
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/compute")
async def compute(n: int = Query(ge=0, le=1_000_000)):
    try:
        resp = await client.post(f"{WORKER_URL}/process", json={"value": n})
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        WORKER_CALLS.labels("error").inc()
        raise HTTPException(status_code=502, detail=f"worker unavailable: {type(exc).__name__}")
    WORKER_CALLS.labels("ok").inc()
    return {"n": n, "result": resp.json()["result"]}
