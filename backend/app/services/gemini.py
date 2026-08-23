"""Single choke point for every Gemini call.

Guardrails (spec §7):
- SQLite response cache keyed by prompt hash (24h TTL) — protects free-tier quota.
- Retry with exponential backoff on 429/5xx.
- DEMO_MODE=1 serves realistic canned JSON from data/demo_responses/ so the
  whole app works end-to-end with no API key and zero quota risk.

The rest of the codebase only calls `generate_json(task, prompt, ...)` and
never imports the google-genai SDK directly.
"""

import hashlib
import json
import logging
import re
import time
from pathlib import Path
from sqlite3 import Connection

from ..config import DATA_DIR, Settings
from .. import db

log = logging.getLogger(__name__)

DEMO_RESPONSES_DIR = DATA_DIR / "demo_responses"

_MAX_RETRIES = 4
_BASE_DELAY_S = 2.0


class GeminiError(RuntimeError):
    pass


class GeminiService:
    def __init__(self, settings: Settings, conn: Connection,
                 demo_dir: Path = DEMO_RESPONSES_DIR):
        self.settings = settings
        self.conn = conn
        self.demo_dir = demo_dir
        self._client = None  # lazy — only created in live mode

    # --- public API ---

    def generate_json(self, task: str, prompt: str, language: str = "en",
                      image_bytes: bytes | None = None,
                      image_mime: str = "image/jpeg") -> dict:
        """Return the model's structured-JSON response for a task.

        task: fixture name used in DEMO_MODE ("advisory" | "diagnosis" | "ask").
        """
        if self.settings.demo_mode:
            return self._demo_response(task, language)

        cache_key = self._hash(task, prompt, language, image_bytes)
        cached = db.cache_get(self.conn, cache_key, ttl_hours=24)
        if cached is not None:
            return json.loads(cached)

        try:
            text = self._call_with_retry(prompt, image_bytes, image_mime)
            parsed = self._parse_json(text)
        except GeminiError:
            # Live call exhausted its retries (quota, bad key, network).
            # With demo_fallback on, degrade gracefully to the canned
            # response so the app keeps working; the failure is logged.
            if self.settings.demo_fallback:
                log.warning(
                    "Live Gemini call for task '%s' failed; serving demo fallback",
                    task, exc_info=True,
                )
                return self._demo_response(task, language)
            raise
        db.cache_put(self.conn, cache_key, json.dumps(parsed))
        return parsed

    # --- demo mode ---

    def _demo_response(self, task: str, language: str) -> dict:
        for lang in (language, "en"):
            path = self.demo_dir / f"{task}_{lang}.json"
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        raise GeminiError(
            f"DEMO_MODE is on but no canned response exists for task '{task}'"
        )

    # --- live mode ---

    def _get_client(self):
        if self._client is None:
            if not self.settings.gemini_api_key:
                raise GeminiError(
                    "GEMINI_API_KEY is not set. Add it to .env, or set DEMO_MODE=1."
                )
            from google import genai  # deferred so DEMO_MODE needs no SDK
            self._client = genai.Client(api_key=self.settings.gemini_api_key)
        return self._client

    def _call_with_retry(self, prompt: str, image_bytes: bytes | None,
                         image_mime: str) -> str:
        from google.genai import types

        client = self._get_client()
        contents: list = [prompt]
        if image_bytes:
            contents.append(types.Part.from_bytes(data=image_bytes, mime_type=image_mime))

        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                resp = client.models.generate_content(
                    model=self.settings.gemini_model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2,
                    ),
                )
                return resp.text
            except Exception as exc:
                last_exc = exc
                if not self._is_retryable(exc) or attempt == _MAX_RETRIES - 1:
                    raise GeminiError(f"Gemini call failed: {exc}") from exc
                delay = _BASE_DELAY_S * (2 ** attempt)
                log.warning("Gemini retryable error (%s); retry in %.1fs", exc, delay)
                time.sleep(delay)
        raise GeminiError(f"Gemini call failed after retries: {last_exc}")

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        text = str(exc)
        return any(code in text for code in ("429", "500", "503", "RESOURCE_EXHAUSTED"))

    # --- helpers ---

    @staticmethod
    def _hash(task: str, prompt: str, language: str,
              image_bytes: bytes | None) -> str:
        h = hashlib.sha256()
        h.update(task.encode())
        h.update(prompt.encode())
        h.update(language.encode())
        if image_bytes:
            h.update(image_bytes)
        return h.hexdigest()

    @staticmethod
    def _parse_json(text: str) -> dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Some responses wrap JSON in markdown fences despite the mime type.
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                return json.loads(m.group(0))
            raise GeminiError(f"Gemini returned non-JSON output: {text[:200]}")
