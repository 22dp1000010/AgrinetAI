"""Honest-fallback behaviour: offline responses are labeled, ask answers stay
question-specific, and canned diagnoses never feed the outbreak detector."""

import io

from tests.test_diagnose import tiny_png


def _force_fallback(container):
    """Make live mode fail so DEMO_FALLBACK engages (key invalid)."""
    s = container.settings
    object.__setattr__(s, "demo_mode", False)
    object.__setattr__(s, "gemini_api_key", "")
    object.__setattr__(s, "use_vertex_ai", False)
    container.gemini._client = None


def test_ask_fallback_is_extractive_and_question_specific(client, container):
    _force_fallback(container)
    r1 = client.post("/api/ask", json={
        "question": "How do I control brown planthopper in my paddy field?",
        "language": "en"})
    r2 = client.post("/api/ask", json={
        "question": "What should I do about fall armyworm in maize whorls?",
        "language": "en"})
    a1, a2 = r1.json(), r2.json()
    assert a1["offline_guidance"] is True and a2["offline_guidance"] is True
    assert a1["answer"] != a2["answer"], "fallback answers must vary by question"
    assert "planthopper" in a1["answer"].lower()
    assert "armyworm" in a2["answer"].lower()
    assert a1["citations"] and a2["citations"]


def test_advisory_fallback_is_labeled(client, container):
    _force_fallback(container)
    body = client.post("/api/advisory", json={
        "lat": 17.98, "lon": 79.53, "crop": "paddy", "language": "en",
    }).json()
    assert body["offline_guidance"] is True
    assert "[Offline guidance]" in body["confidence_note"]
    assert body["district"] == "Warangal"  # via FakeGeocoder


def test_fallback_diagnosis_never_records_outbreak_report(client, container):
    _force_fallback(container)
    for _ in range(3):
        r = client.post(
            "/api/diagnose",
            files={"image": ("l.png", io.BytesIO(tiny_png()), "image/png")},
            data={"crop": "paddy", "language": "en", "district": "Warangal"},
        )
        body = r.json()
        assert body["offline_guidance"] is True
        assert body["alert_triggered"] is False
    # Canned (not-really-examined) diagnoses must not create alerts.
    assert client.get("/v1/alerts").json()["alerts"] == []


def test_demo_mode_is_not_labeled_offline(client):
    # Intentional DEMO_MODE (the default test config) is not a failure state.
    body = client.post("/api/advisory", json={
        "lat": 17.98, "lon": 79.53, "crop": "paddy", "language": "en",
    }).json()
    assert body["offline_guidance"] is False
