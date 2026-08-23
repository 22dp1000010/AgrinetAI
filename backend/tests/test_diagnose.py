"""Diagnosis endpoint: multipart upload, validation, disease-report logging
and the outbreak → alert flow through the public API."""

import io
import struct
import zlib


def tiny_png() -> bytes:
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data)))
    raw = b"".join(b"\x00" + b"\x22\x8b\x22" * 8 for _ in range(8))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 8, 8, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def _post(client, **data):
    form = {"crop": "paddy", "language": "en", "district": "Warangal"}
    form.update(data)
    return client.post(
        "/api/diagnose",
        files={"image": ("leaf.png", io.BytesIO(tiny_png()), "image/png")},
        data=form,
    )


def test_diagnose_returns_structured_result(client):
    r = _post(client)
    assert r.status_code == 200
    body = r.json()
    assert "planthopper" in body["disease"].lower()
    assert body["confidence"] in ("high", "medium", "low")
    assert body["treatment_steps"]
    assert body["safety_note"]
    assert body["alert_triggered"] is False  # first report of three


def test_diagnose_rejects_wrong_mime(client):
    r = client.post(
        "/api/diagnose",
        files={"image": ("x.gif", io.BytesIO(b"GIF89a"), "image/gif")},
        data={"crop": "paddy"},
    )
    assert r.status_code == 415


def test_diagnose_rejects_bad_language(client):
    assert _post(client, language="xx").status_code == 422


def test_three_diagnoses_trigger_outbreak_alert(client):
    results = [_post(client).json() for _ in range(3)]
    assert [r["alert_triggered"] for r in results] == [False, False, True]
    alerts = client.get("/v1/alerts").json()["alerts"]
    assert len(alerts) == 1
    assert alerts[0]["district"] == "Warangal"
    assert alerts[0]["report_count"] == 3
    assert alerts[0]["received_from_peer"] is False


def test_diagnose_logs_anonymized_query(client, container):
    _post(client, lat="17.987654", lon="79.534321")
    row = container.conn.execute(
        "SELECT * FROM queries WHERE kind='diagnose'").fetchone()
    assert row["lat"] == 17.99 and row["lon"] == 79.53
