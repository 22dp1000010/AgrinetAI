"""Demo farm registry — lookup helpers used to attach a district to
anonymous coordinates (no farmer PII is ever stored)."""

import json
import math
from functools import lru_cache

from ..config import DATA_DIR

FARMS_FILE = DATA_DIR / "demo_farms.json"


@lru_cache
def load_farms() -> list[dict]:
    return json.loads(FARMS_FILE.read_text(encoding="utf-8"))["farms"]


def nearest_farm(lat: float, lon: float) -> dict | None:
    farms = load_farms()
    if not farms:
        return None
    return min(farms, key=lambda f: math.hypot(f["lat"] - lat, f["lon"] - lon))


def infer_district(lat: float, lon: float) -> str:
    farm = nearest_farm(lat, lon)
    return farm["district"] if farm else "Unknown"
