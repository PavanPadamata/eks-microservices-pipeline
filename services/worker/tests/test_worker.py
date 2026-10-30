import app.main as main
from fastapi.testclient import TestClient

client = TestClient(main.app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_process_returns_sum_of_squares(monkeypatch):
    monkeypatch.setattr(main, "WORK_MS", 0)
    r = client.post("/process", json={"value": 3})
    assert r.status_code == 200
    assert r.json() == {"value": 3, "result": 14}  # 0 + 1 + 4 + 9


def test_process_rejects_invalid_input():
    assert client.post("/process", json={"value": -1}).status_code == 422
    assert client.post("/process", json={"value": 1_000_001}).status_code == 422
    assert client.post("/process", json={}).status_code == 422


def test_metrics_exposes_request_counter_by_route_template(monkeypatch):
    monkeypatch.setattr(main, "WORK_MS", 0)
    client.post("/process", json={"value": 1})
    body = client.get("/metrics").text
    assert 'http_requests_total{method="POST",path="/process",status="200"}' in body
    assert "http_request_duration_seconds_bucket" in body


def test_probe_traffic_is_not_counted():
    client.get("/healthz")
    assert 'path="/healthz"' not in client.get("/metrics").text
