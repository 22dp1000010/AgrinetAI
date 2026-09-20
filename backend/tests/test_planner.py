"""Seasonal crop planner pipeline (mocked providers + DEMO_MODE Gemini)."""


def _request(client, **overrides):
    payload = {"lat": 17.98, "lon": 79.53, "current_crop": "paddy",
               "language": "en"}
    payload.update(overrides)
    return client.post("/api/planner", json=payload)


def test_planner_end_to_end_shape(client):
    r = _request(client)
    assert r.status_code == 200
    body = r.json()
    assert len(body["rotation"]) >= 2
    for step in body["rotation"]:
        assert step["season"] and step["crop"] and step["why"]
    assert body["regenerative_plan"]
    assert body["citations"], "rotation advice must be grounded"
    # Provenance comes from the (fake) providers, as with advisory.
    assert body["provenance"]["soil"]["ph"] == 6.1
    assert body["provenance"]["weather"]["rain_next_7d_mm"] == 12.0


def test_planner_language_passthrough(client):
    r = _request(client, language="hi")
    assert r.status_code == 200
    body = r.json()
    assert body["language"] == "hi"
    assert any("ऀ" <= ch <= "ॿ" for ch in body["rotation"][0]["crop"])


def test_planner_rejects_bad_input(client):
    assert _request(client, language="fr").status_code == 422
    assert _request(client, lat=999).status_code == 422
    assert client.post("/api/planner", json={"lat": 17.98, "lon": 79.53}).status_code == 422


def test_planner_logs_anonymized_query(client, container):
    _request(client, lat=17.987654, lon=79.534321)
    row = container.conn.execute(
        "SELECT * FROM queries WHERE kind='planner'").fetchone()
    assert row is not None
    assert row["lat"] == 17.99 and row["lon"] == 79.53
    assert row["crop"] == "paddy"
