"""Worker service: does a small, deliberately CPU-bound unit of work."""
import os
import time

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field

WORK_MS = float(os.getenv("WORK_MS", "20"))  # busy-wait per request, makes CPU/HPA visible
UNTRACKED_PATHS = {"/healthz", "/metrics"}  # keep probe/scrape traffic out of request metrics

REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)

app = FastAPI(title="worker")


class Job(BaseModel):
    value: int = Field(ge=0, le=1_000_000)


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
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/process")
def process(job: Job):
    deadline = time.perf_counter() + WORK_MS / 1000
    while time.perf_counter() < deadline:  # sync endpoint runs in a threadpool, so this burns CPU
        pass
    return {"value": job.value, "result": sum(i * i for i in range(job.value + 1))}
