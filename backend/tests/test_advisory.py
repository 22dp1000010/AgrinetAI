"""Advisory pipeline with mocked providers + DEMO_MODE Gemini."""


def test_advisory_end_to_end_shape(client):
    r = client.post("/api/advisory", json={
        "lat": 17.9803, "lon": 79.5311, "crop": "paddy", "language": "en",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["advisory"], "advisory items must be present"
    for item in body["advisory"]:
        assert item["urgency"] in ("high", "medium", "low")
    assert body["citations"], "citations are mandatory (grounding)"
    assert body["citations"][0]["source"]
    # Provenance strip data comes from the (fake) providers.
    assert body["provenance"]["satellite"]["ndvi_mean"] == 0.62
    assert body["provenance"]["soil"]["ph"] == 6.1
    assert body["provenance"]["weather"]["rain_next_7d_mm"] == 12.0


def test_advisory_language_passthrough(client):
    r = client.post("/api/advisory", json={
        "lat": 17.98, "lon": 79.53, "crop": "paddy", "language": "te",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["language"] == "te"
    # DEMO_MODE serves the Telugu fixture — farmer-facing text is Telugu.
    assert any("ఀ" <= ch <= "౿" for ch in body["advisory"][0]["title"])


def test_advisory_rejects_bad_input(client):
    assert client.post("/api/advisory", json={
        "lat": 17.98, "lon": 79.53, "crop": "paddy", "language": "fr",
    }).status_code == 422
    assert client.post("/api/advisory", json={
        "lat": 999, "lon": 79.53, "crop": "paddy",
    }).status_code == 422
    assert client.post("/api/advisory", json={"crop": "paddy"}).status_code == 422


def test_advisory_logs_query_with_rounded_coords(client, container):
    client.post("/api/advisory", json={
        "lat": 17.987654, "lon": 79.534321, "crop": "paddy", "language": "en",
    })
    row = container.conn.execute("SELECT * FROM queries").fetchone()
    assert row["kind"] == "advisory"
    assert row["lat"] == 17.99  # privacy: rounded to 2 decimals
    assert row["lon"] == 79.53
    assert row["district"] == "Warangal"  # inferred from nearest demo farm
