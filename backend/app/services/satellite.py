"""Satellite feature providers.

`SatelliteProvider` is the interface the advisory pipeline depends on.
Two implementations:

- `CachedSatelliteProvider` (default): serves pre-computed Sentinel-2 NDVI
  features from backend/data/satellite_cache/ — the demo never depends on
  live Earth Engine auth.
- `EarthEngineProvider` (behind EE_ENABLED=1): computes the same features
  live via the Earth Engine Python API. Requires `pip install earthengine-api`
  and an authenticated noncommercial project.

Both return: { ndvi_mean, ndvi_trend, ndwi_mean, window_days, source }.
"""

import json
import logging
import math
from abc import ABC, abstractmethod
from pathlib import Path

from ..config import DATA_DIR

log = logging.getLogger(__name__)

CACHE_DIR = DATA_DIR / "satellite_cache"


class SatelliteProvider(ABC):
    @abstractmethod
    def get_features(self, lat: float, lon: float) -> dict:
        """Return NDVI/NDWI features for the 30 days preceding the snapshot."""


class CachedSatelliteProvider(SatelliteProvider):
    """Nearest-neighbour lookup over pre-computed snapshots (one JSON per
    demo farm plus regional fallbacks)."""

    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self._snapshots = self._load()

    def _load(self) -> list[dict]:
        snaps = []
        for f in sorted(self.cache_dir.glob("*.json")):
            try:
                snaps.append(json.loads(f.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError) as exc:
                log.warning("Skipping bad satellite snapshot %s: %s", f, exc)
        return snaps

    def get_features(self, lat: float, lon: float) -> dict:
        if not self._snapshots:
            return {
                "ndvi_mean": None, "ndvi_trend": "unknown", "ndwi_mean": None,
                "window_days": 30, "source": "no satellite data available",
            }
        best = min(
            self._snapshots,
            key=lambda s: math.hypot(s["lat"] - lat, s["lon"] - lon),
        )
        features = dict(best["features"])
        features["window_days"] = best.get("window_days", 30)
        features["source"] = (
            f"Sentinel-2 via Earth Engine (cached {best.get('computed_on', 'n/a')})"
        )
        return features


class EarthEngineProvider(SatelliteProvider):
    """Live Sentinel-2 NDVI via Earth Engine. Import is deferred so the
    dependency is only needed when EE_ENABLED=1."""

    def __init__(self, project: str = ""):
        import ee  # noqa: PLC0415 — optional dependency, deferred on purpose

        ee.Initialize(project=project or None)
        self._ee = ee

    def get_features(self, lat: float, lon: float) -> dict:
        ee = self._ee
        point = ee.Geometry.Point(lon, lat).buffer(250)
        import datetime
        today = datetime.date.today()
        start = (today - datetime.timedelta(days=30)).isoformat()
        mid = (today - datetime.timedelta(days=15)).isoformat()

        col = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(point)
            .filterDate(start, today.isoformat())
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
        )

        def _ndvi_mean(collection):
            img = collection.map(
                lambda i: i.normalizedDifference(["B8", "B4"]).rename("NDVI")
            ).mean()
            val = img.reduceRegion(ee.Reducer.mean(), point, 10).get("NDVI")
            return val.getInfo() if val else None

        first_half = _ndvi_mean(col.filterDate(start, mid))
        second_half = _ndvi_mean(col.filterDate(mid, today.isoformat()))
        ndvi_mean = _ndvi_mean(col)

        trend = "stable"
        if first_half is not None and second_half is not None:
            delta = second_half - first_half
            trend = "improving" if delta > 0.03 else "declining" if delta < -0.03 else "stable"

        ndwi_img = col.map(
            lambda i: i.normalizedDifference(["B3", "B8"]).rename("NDWI")
        ).mean()
        ndwi_val = ndwi_img.reduceRegion(ee.Reducer.mean(), point, 10).get("NDWI")
        ndwi_mean = ndwi_val.getInfo() if ndwi_val else None

        return {
            "ndvi_mean": round(ndvi_mean, 3) if ndvi_mean is not None else None,
            "ndvi_trend": trend,
            "ndwi_mean": round(ndwi_mean, 3) if ndwi_mean is not None else None,
            "window_days": 30,
            "source": "Sentinel-2 via Earth Engine (live)",
        }


def build_provider(ee_enabled: bool, ee_project: str = "") -> SatelliteProvider:
    if ee_enabled:
        try:
            return EarthEngineProvider(project=ee_project)
        except Exception as exc:
            log.warning("Earth Engine init failed (%s); falling back to cache", exc)
    return CachedSatelliteProvider()
