"""Open-Meteo forecast client (free, no key) with file cache + offline fallback.

Returns a normalized feature dict consumed by the advisory pipeline and shown
in the UI provenance strip. Never raises on network failure — falls back to
the last cached response, then to a bundled static default, so the demo never
depends on connectivity.
"""

import json
import logging
from datetime import date
from pathlib import Path

import httpx

from ..config import DATA_DIR

log = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_DIR = DATA_DIR / "http_cache" / "weather"

# Realistic monsoon-season default used only if the API and cache both fail.
_OFFLINE_DEFAULT = {
    "rain_next_7d_mm": 42.0,
    "max_temp_c": 33.5,
    "min_temp_c": 24.1,
    "mean_humidity_pct": 78,
    "max_wind_kmh": 19.0,
    "daily": [],
    "source": "offline default (network unavailable)",
}


class WeatherClient:
    def __init__(self, cache_dir: Path = CACHE_DIR, timeout: float = 10.0):
        self.cache_dir = cache_dir
        self.timeout = timeout

    def _cache_path(self, lat: float, lon: float) -> Path:
        return self.cache_dir / f"{round(lat, 2)}_{round(lon, 2)}_{date.today()}.json"

    def get_forecast(self, lat: float, lon: float) -> dict:
        cache_path = self._cache_path(lat, lon)
        if cache_path.exists():
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            data["source"] = "Open-Meteo (cached today)"
            return data
        try:
            raw = self._fetch(lat, lon)
        except Exception as exc:  # network / API failure must not break the demo
            log.warning("Open-Meteo fetch failed (%s); using fallback", exc)
            return self._stale_or_default(lat, lon)
        features = self._normalize(raw)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(features), encoding="utf-8")
        features["source"] = "Open-Meteo (live)"
        return features

    def _fetch(self, lat: float, lon: float) -> dict:
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                     "relative_humidity_2m_mean,wind_speed_10m_max",
            "forecast_days": 7,
            "timezone": "auto",
        }
        resp = httpx.get(OPEN_METEO_URL, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _normalize(raw: dict) -> dict:
        daily = raw.get("daily", {})
        days = daily.get("time", [])
        precip = daily.get("precipitation_sum", []) or []
        tmax = daily.get("temperature_2m_max", []) or []
        tmin = daily.get("temperature_2m_min", []) or []
        hum = daily.get("relative_humidity_2m_mean", []) or []
        wind = daily.get("wind_speed_10m_max", []) or []
        return {
            "rain_next_7d_mm": round(sum(p for p in precip if p is not None), 1),
            "max_temp_c": max((t for t in tmax if t is not None), default=None),
            "min_temp_c": min((t for t in tmin if t is not None), default=None),
            "mean_humidity_pct": round(sum(hum) / len(hum)) if hum else None,
            "max_wind_kmh": max((w for w in wind if w is not None), default=None),
            "daily": [
                {
                    "date": days[i],
                    "rain_mm": precip[i] if i < len(precip) else None,
                    "tmax_c": tmax[i] if i < len(tmax) else None,
                }
                for i in range(len(days))
            ],
        }

    def _stale_or_default(self, lat: float, lon: float) -> dict:
        # Any older cached file for this location beats the static default.
        prefix = f"{round(lat, 2)}_{round(lon, 2)}_"
        if self.cache_dir.exists():
            stale = sorted(self.cache_dir.glob(f"{prefix}*.json"), reverse=True)
            if stale:
                data = json.loads(stale[0].read_text(encoding="utf-8"))
                data["source"] = f"Open-Meteo (stale cache {stale[0].stem.split('_')[-1]})"
                return data
        return dict(_OFFLINE_DEFAULT)
