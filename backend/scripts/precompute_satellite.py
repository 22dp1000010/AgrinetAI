"""One-off: compute Sentinel-2 NDVI/NDWI features for the demo farms via
Earth Engine and write them to data/satellite_cache/ — so the live demo never
depends on EE auth.

Requires:  pip install earthengine-api  +  earthengine authenticate
Usage:     python scripts/precompute_satellite.py [--project YOUR_EE_PROJECT]

The repo ships with representative pre-computed snapshots already; re-run this
only to refresh them with real, current values.
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import DATA_DIR  # noqa: E402
from app.services.satellite import EarthEngineProvider  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default="", help="EE cloud project id")
    args = parser.parse_args()

    farms = json.loads((DATA_DIR / "demo_farms.json").read_text(encoding="utf-8"))["farms"]
    provider = EarthEngineProvider(project=args.project)

    out_dir = DATA_DIR / "satellite_cache"
    out_dir.mkdir(parents=True, exist_ok=True)
    for farm in farms:
        print(f"Computing features for {farm['id']}…")
        features = provider.get_features(farm["lat"], farm["lon"])
        source = features.pop("source", None)
        window = features.pop("window_days", 30)
        snapshot = {
            "farm_id": farm["id"],
            "lat": farm["lat"],
            "lon": farm["lon"],
            "computed_on": date.today().isoformat(),
            "window_days": window,
            "note": f"Computed live from {source}",
            "features": features,
        }
        path = out_dir / f"{farm['id'].replace('-', '_')}.json"
        path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        print(f"  wrote {path}")


if __name__ == "__main__":
    main()
