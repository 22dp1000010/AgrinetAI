"""Federation endpoints + peer push logic."""

import httpx
import respx

from app import db
from app.models.protocol import Alert
from app.services.federation import FederationService
from tests.conftest import make_settings


def _alert_payload(**overrides):
    payload = {
        "id": "11111111-1111-1111-1111-111111111111",
        "origin_state": "TS",
        "disease": "brown planthopper",
        "crop": "paddy",
        "district": "Warangal",
        "severity": "high",
        "report_count": 3,
        "window_days": 7,
        "message": "outbreak",
        "created_at": "2026-08-20T10:00:00+00:00",
    }
    payload.update(overrides)
    return payload


def test_health_reports_state_and_protocol(client):
    body = client.get("/v1/health").json()
    assert body == {"status": "ok", "state_id": "TS",
                    "state_name": "Telangana", "protocol_version": "1.0"}


def test_receive_alert_and_list(client):
    r = client.post("/v1/alerts", json=_alert_payload())
    assert r.status_code == 202
    assert r.json() == {"accepted": True, "duplicate": False,
                        "id": _alert_payload()["id"]}
    alerts = client.get("/v1/alerts").json()["alerts"]
    assert len(alerts) == 1
    assert alerts[0]["received_from_peer"] is True
    assert alerts[0]["origin_state"] == "TS"


def test_receive_alert_is_idempotent(client):
    client.post("/v1/alerts", json=_alert_payload())
    r = client.post("/v1/alerts", json=_alert_payload())
    assert r.json()["duplicate"] is True
    assert len(client.get("/v1/alerts").json()["alerts"]) == 1


def test_receive_alert_rejects_invalid_payload(client):
    r = client.post("/v1/alerts", json=_alert_payload(severity="apocalyptic"))
    assert r.status_code == 422
    r = client.post("/v1/alerts", json={"origin_state": "TS"})
    assert r.status_code == 422


def test_peers_and_model_registry(tmp_path):
    from app.main import create_app
    from fastapi.testclient import TestClient
    settings = make_settings(tmp_path, peers="http://localhost:8002")
    client = TestClient(create_app(settings))
    peers = client.get("/v1/peers").json()
    assert peers == [{"state_id": "OD", "name": "Odisha State Node",
                      "base_url": "http://localhost:8002", "last_sync": None}]
    models = client.get("/v1/models").json()
    assert models and models[0]["task"].startswith("leaf-image")


@respx.mock
def test_push_alert_to_peers_delivers(tmp_path):
    settings = make_settings(tmp_path, peers="http://peer-od:8002")
    conn = db.connect(settings.database_path)
    route = respx.post("http://peer-od:8002/v1/alerts").mock(
        return_value=httpx.Response(202, json={"accepted": True}))
    service = FederationService(settings, conn)
    alert = Alert(**{k: v for k, v in _alert_payload().items()
                     if k not in ("created_at",)})
    results = service.push_alert_to_peers(alert)
    assert results == {"http://peer-od:8002": True}
    assert route.called


@respx.mock
def test_push_alert_retries_then_gives_up(tmp_path):
    settings = make_settings(tmp_path, peers="http://peer-down:8002")
    conn = db.connect(settings.database_path)
    route = respx.post("http://peer-down:8002/v1/alerts").mock(
        side_effect=httpx.ConnectError("down"))
    service = FederationService(settings, conn)
    alert = Alert(origin_state="TS", disease="blast", report_count=3, window_days=7)
    results = service.push_alert_to_peers(alert)
    assert results == {"http://peer-down:8002": False}
    assert route.call_count == 3  # _PUSH_ATTEMPTS
