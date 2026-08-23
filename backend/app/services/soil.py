"""SoilGrids (ISRIC) client — free, no key — with file cache + offline fallback.

Extracts topsoil (0–5 cm) pH, soil organic carbon and texture fractions.
Soil properties change slowly, so the cache has no TTL.
"""

import json
import logging
from pathlib import Path

import httpx

from ..config import DATA_DIR

log = logging.getLogger(__name__)

SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
CACHE_DIR = DATA_DIR / "http_cache" / "soil"

# Typical Deccan-plateau values used only if the API and cache both fail.
_OFFLINE_DEFAULT = {
    "ph": 6.4,
    "soc_g_per_kg": 9.8,
    "clay_pct": 32.0,
    "sand_pct": 41.0,
    "source": "offline default (network unavailable)",
}

_PROPERTIES = ["phh2o", "soc", "clay", "sand"]
# SoilGrids returns scaled integers; divide by these to get real units.
_D_FACTORS = {"phh2o": 10, "soc": 10, "clay": 10, "sand": 10}


class SoilClient:
    def __init__(self, cache_dir: Path = CACHE_DIR, timeout: float = 15.0):
        self.cache_dir = cache_dir
        self.timeout = timeout

    def _cache_path(self, lat: float, lon: float) -> Path:
        return self.cache_dir / f"{round(lat, 2)}_{round(lon, 2)}.json"

    def get_properties(self, lat: float, lon: float) -> dict:
        cache_path = self._cache_path(lat, lon)
        if cache_path.exists():
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            data["source"] = "SoilGrids/ISRIC (cached)"
            return data
        try:
            raw = self._fetch(lat, lon)
            features = self._normalize(raw)
        except Exception as exc:
            log.warning("SoilGrids fetch failed (%s); using offline default", exc)
            return dict(_OFFLINE_DEFAULT)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(features), encoding="utf-8")
        features["source"] = "SoilGrids/ISRIC (live)"
        return features

    def _fetch(self, lat: float, lon: float) -> dict:
        params = [("lon", lon), ("lat", lat), ("depth", "0-5cm"), ("value", "mean")]
        params += [("property", p) for p in _PROPERTIES]
        resp = httpx.get(SOILGRIDS_URL, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _normalize(raw: dict) -> dict:
        values: dict[str, float | None] = {}
        for layer in raw.get("properties", {}).get("layers", []):
            name = layer.get("name")
            if name not in _PROPERTIES:
                continue
            depths = layer.get("depths", [])
            mean = depths[0].get("values", {}).get("mean") if depths else None
            values[name] = (mean / _D_FACTORS[name]) if mean is not None else None
        return {
            "ph": values.get("phh2o"),
            "soc_g_per_kg": values.get("soc"),
            "clay_pct": values.get("clay"),
            "sand_pct": values.get("sand"),
        }
