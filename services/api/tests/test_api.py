import app.main as main
import httpx
import respx
from fastapi.testclient import TestClient

client = TestClient(main.app)
PROCESS_URL = f"{main.WORKER_URL}/process"


def test_healthz_does_not_need_worker():
    with respx.mock:  # any outbound call would raise, since no route is registered
        r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@respx.mock
def test_compute_forwards_to_worker():
    route = respx.post(PROCESS_URL).mock(
        return_value=httpx.Response(200, json={"value": 3, "result": 14})
    )
    r = client.get("/compute", params={"n": 3})
    assert r.status_code == 200
    assert r.json() == {"n": 3, "result": 14}
    assert route.calls.last.request.content == b'{"value":3}'


@respx.mock
def test_compute_returns_502_when_worker_errors():
    respx.post(PROCESS_URL).mock(return_value=httpx.Response(500))
    assert client.get("/compute", params={"n": 3}).status_code == 502


@respx.mock
def test_compute_returns_502_when_worker_unreachable():
    respx.post(PROCESS_URL).mock(side_effect=httpx.ConnectError("refused"))
    r = client.get("/compute", params={"n": 3})
    assert r.status_code == 502
    assert "ConnectError" in r.json()["detail"]


def test_compute_validates_input():
    assert client.get("/compute", params={"n": -1}).status_code == 422
    assert client.get("/compute").status_code == 422


@respx.mock
def test_metrics_record_requests_and_worker_calls():
    respx.post(PROCESS_URL).mock(return_value=httpx.Response(200, json={"value": 1, "result": 1}))
    client.get("/compute", params={"n": 1})
    body = client.get("/metrics").text
    assert 'http_requests_total{method="GET",path="/compute",status="200"}' in body
    assert 'worker_calls_total{outcome="ok"}' in body
