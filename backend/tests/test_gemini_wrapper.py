"""Gemini wrapper guardrails: DEMO_MODE fixtures, cache behaviour, retry."""

import json

import pytest

from app.services import gemini as gemini_module
from app.services.gemini import GeminiError, GeminiService
from app.storage import SQLiteStore
from tests.conftest import make_settings


def make_service(tmp_path, **overrides) -> GeminiService:
    settings = make_settings(tmp_path, **overrides)
    return GeminiService(settings, SQLiteStore(settings.database_path))


def test_demo_mode_serves_fixture_without_key(tmp_path):
    svc = make_service(tmp_path, demo_mode=True, gemini_api_key="")
    result = svc.generate_json("advisory", "any prompt", language="en")
    assert result["advisory"]
    assert result["citations"]


def test_demo_mode_language_fallback_to_english(tmp_path):
    svc = make_service(tmp_path, demo_mode=True)
    # 'te' fixture exists — must serve Telugu, not English.
    te = svc.generate_json("advisory", "p", language="te")
    assert any("ఀ" <= ch <= "౿" for ch in te["advisory"][0]["title"])
    # Unknown task must raise a clear error.
    with pytest.raises(GeminiError, match="no canned response"):
        svc.generate_json("nonexistent_task", "p")


def test_live_mode_without_key_raises_when_fallback_off(tmp_path):
    svc = make_service(tmp_path, demo_mode=False, gemini_api_key="",
                       demo_fallback=False)
    with pytest.raises(GeminiError, match="GEMINI_API_KEY"):
        svc.generate_json("advisory", "prompt")


def test_live_mode_without_key_falls_back_to_demo(tmp_path):
    # demo_fallback defaults to True: a dead key/quota must not break the app.
    svc = make_service(tmp_path, demo_mode=False, gemini_api_key="")
    result = svc.generate_json("advisory", "prompt", language="en")
    assert result["advisory"]  # served from the canned fixture


def test_live_failure_falls_back_to_demo(tmp_path, monkeypatch):
    svc = make_service(tmp_path, demo_mode=False, gemini_api_key="test-key")

    class FakeModels:
        def generate_content(self, **kwargs):
            raise RuntimeError("429 RESOURCE_EXHAUSTED: quota out")

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(svc, "_get_client", lambda: FakeClient())
    monkeypatch.setattr(gemini_module.time, "sleep", lambda s: None)
    result = svc.generate_json("ask", "q", language="te")
    assert "answer" in result  # Telugu canned fixture served after retries


def test_cache_key_stability_and_image_sensitivity():
    h1 = GeminiService._hash("advisory", "prompt", "en", None)
    h2 = GeminiService._hash("advisory", "prompt", "en", None)
    assert h1 == h2
    assert GeminiService._hash("advisory", "prompt", "te", None) != h1
    assert GeminiService._hash("advisory", "prompt", "en", b"img") != h1


def test_live_mode_uses_cache_and_retries_on_429(tmp_path, monkeypatch):
    svc = make_service(tmp_path, demo_mode=False, gemini_api_key="test-key")

    calls = {"n": 0}

    class FakeResponse:
        text = json.dumps({"answer": "ok", "citations": []})

    class FakeModels:
        def generate_content(self, **kwargs):
            calls["n"] += 1
            if calls["n"] < 2:
                raise RuntimeError("429 RESOURCE_EXHAUSTED: rate limit per minute")
            return FakeResponse()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(svc, "_get_client", lambda: FakeClient())
    monkeypatch.setattr(gemini_module.time, "sleep", lambda s: None)

    result = svc.generate_json("ask", "some question", language="en")
    assert result == {"answer": "ok", "citations": []}
    assert calls["n"] == 2  # one transient 429 retried, second succeeded

    # Second identical call must be served from the SQLite cache.
    result2 = svc.generate_json("ask", "some question", language="en")
    assert result2 == result
    assert calls["n"] == 2


def test_daily_quota_fails_fast_and_starts_cooldown(tmp_path, monkeypatch):
    svc = make_service(tmp_path, demo_mode=False, gemini_api_key="test-key")

    calls = {"n": 0}

    class FakeModels:
        def generate_content(self, **kwargs):
            calls["n"] += 1
            raise RuntimeError(
                "429 RESOURCE_EXHAUSTED: quotaId GenerateRequestsPerDayPerProjectPerModel-FreeTier"
            )

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(svc, "_get_client", lambda: FakeClient())
    monkeypatch.setattr(gemini_module.time, "sleep", lambda s: None)

    # First request: exactly ONE API attempt (no retries), then demo fallback.
    result = svc.generate_json("ask", "q1", language="en")
    assert "answer" in result
    assert calls["n"] == 1

    # Cooldown active: the next request never touches the API at all.
    result2 = svc.generate_json("ask", "a different question", language="en")
    assert "answer" in result2
    assert calls["n"] == 1


def test_live_mode_gives_up_on_non_retryable(tmp_path, monkeypatch):
    svc = make_service(tmp_path, demo_mode=False, gemini_api_key="test-key",
                       demo_fallback=False)

    class FakeModels:
        def generate_content(self, **kwargs):
            raise RuntimeError("400 INVALID_ARGUMENT")

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(svc, "_get_client", lambda: FakeClient())
    with pytest.raises(GeminiError, match="Gemini call failed"):
        svc.generate_json("ask", "q")


def test_parse_json_unwraps_markdown_fences():
    text = "```json\n{\"a\": 1}\n```"
    assert GeminiService._parse_json(text) == {"a": 1}
    with pytest.raises(GeminiError, match="non-JSON"):
        GeminiService._parse_json("sorry, I cannot help")
