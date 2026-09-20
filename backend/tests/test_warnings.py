"""Farmer-facing outbreak warnings: district scoping, peer flagging,
prevention grounding, staleness window."""

from datetime import datetime, timedelta, timezone


def _post_alert(client, **overrides):
    payload = {
        "id": overrides.pop("id", "aaaaaaaa-0000-0000-0000-000000000001"),
        "origin_state": "OD",
        "disease": "Brown planthopper (Nilaparvata lugens)",
        "crop": "paddy",
        "district": "Bargarh",
        "severity": "high",
        "report_count": 3,
        "window_days": 7,
        "message": "outbreak",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    payload.update(overrides)
    assert client.post("/v1/alerts", json=payload).status_code == 202
    return payload


WARANGAL = {"lat": 17.98, "lon": 79.53}


def test_no_alerts_no_warnings(client):
    assert client.get("/api/warnings", params=WARANGAL).json() == []


def test_same_district_scoped_to_farmer(client):
    _post_alert(client, district="Warangal", origin_state="TS")
    (w,) = client.get("/api/warnings", params=WARANGAL).json()
    assert w["scope"] == "your_district"
    assert w["from_peer"] is False  # own-state alert echo → local
    assert "planthopper" in w["disease"].lower()


def test_peer_alert_is_regional_warning(client):
    _post_alert(client, district="Bargarh", origin_state="OD")
    (w,) = client.get("/api/warnings", params=WARANGAL).json()
    assert w["scope"] == "regional"
    assert w["from_peer"] is True
    assert w["origin_state"] == "OD"


def test_prevention_tip_is_grounded_in_corpus(client):
    _post_alert(client, district="Warangal")
    (w,) = client.get("/api/warnings", params=WARANGAL).json()
    assert w["prevention"] is not None
    assert "ICAR" in w["prevention"]["source"]
    assert "planthopper" in w["prevention"]["text"].lower()


def test_stale_alerts_not_shown(client):
    old = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()
    _post_alert(client, created_at=old)
    assert client.get("/api/warnings", params=WARANGAL).json() == []


def test_own_district_sorts_first(client):
    _post_alert(client, id="aaaaaaaa-0000-0000-0000-000000000002",
                district="Bargarh", origin_state="OD")
    _post_alert(client, id="aaaaaaaa-0000-0000-0000-000000000003",
                district="Warangal", origin_state="TS")
    scopes = [w["scope"] for w in client.get("/api/warnings", params=WARANGAL).json()]
    assert scopes == ["your_district", "regional"]
