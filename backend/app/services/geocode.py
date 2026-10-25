"""Reverse geocoding: coordinates → real district name.

Uses OpenStreetMap Nominatim (free, no key; requires an identifying
User-Agent). District boundaries don't move, so results are cached per
2-decimal coordinate with no TTL. Fallback chain keeps the app working
offline: file cache → live Nominatim → nearest demo farm's district.
"""

import json
import logging
from pathlib import Path

import httpx

from ..config import DATA_DIR
from .farms import infer_district as _nearest_farm_district

log = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
CACHE_DIR = DATA_DIR / "http_cache" / "geocode"
_USER_AGENT = "AgriNet/1.0 (open-source agri advisory; hackathon prototype)"

# Nominatim address keys that correspond to an Indian district, most
# specific first.
_DISTRICT_KEYS = ("state_district", "county", "district", "city_district", "city")


class Geocoder:
    def __init__(self, cache_dir: Path = CACHE_DIR, timeout: float = 8.0):
        self.cache_dir = cache_dir
        self.timeout = timeout

    def district_for(self, lat: float, lon: float) -> str:
        cache_path = self.cache_dir / f"{round(lat, 2)}_{round(lon, 2)}.json"
        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))["district"]
        try:
            district = self._fetch_district(lat, lon)
        except Exception as exc:
            log.warning("Reverse geocode failed (%s); using nearest-farm fallback", exc)
            return _nearest_farm_district(lat, lon)
        if not district:
            return _nearest_farm_district(lat, lon)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({"district": district}), encoding="utf-8")
        return district

    def _fetch_district(self, lat: float, lon: float) -> str | None:
        resp = httpx.get(
            NOMINATIM_URL,
            params={"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 8,
                    "accept-language": "en"},
            headers={"User-Agent": _USER_AGENT},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        address = resp.json().get("address", {})
        for key in _DISTRICT_KEYS:
            if address.get(key):
                # Normalize "Warangal District" → "Warangal" so outbreak
                # grouping matches districts recorded elsewhere.
                return address[key].removesuffix(" District").removesuffix(" district")
        return None
