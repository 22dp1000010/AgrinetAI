"""Seed demo data for the dashboard + trigger the federation money-shot.

Run with both nodes up (TS on :8001, OD on :8002):

    python scripts/seed_demo_data.py            # seeds TS node at localhost:8001
    python scripts/seed_demo_data.py --node http://localhost:8001

Seeds ~30 advisory/ask queries around Telangana demo farms (heatmap data) and
posts 3 brown-planthopper diagnosis reports in Warangal, which crosses the
outbreak threshold → the TS node creates an Alert and pushes it to its peers
→ it appears on the Odisha node's dashboard ("Early warning from Telangana").

Idempotent enough for demos: re-running adds more queries but the outbreak
alert is created only once per disease+district.
"""

import argparse
import io
import random
import struct
import sys
import zlib

import httpx

FARMS = [
    {"lat": 17.98, "lon": 79.53, "crop": "paddy", "district": "Warangal"},
    {"lat": 17.06, "lon": 79.27, "crop": "cotton", "district": "Nalgonda"},
    {"lat": 17.38, "lon": 78.48, "crop": "chilli", "district": "Hyderabad"},
]


def tiny_png() -> bytes:
    """Minimal valid 8x8 green PNG so /api/diagnose accepts the upload in
    DEMO_MODE (the canned response is returned regardless of pixels)."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data)))

    w = h = 8
    raw = b"".join(b"\x00" + b"\x22\x8b\x22" * w for _ in range(h))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


# A handful of fixed offsets per farm: coordinates repeat across seeded
# queries, so the soil/weather HTTP caches absorb most upstream calls
# (SoilGrids is rate-limited) and seeding stays fast.
_OFFSETS = [(0.0, 0.0), (0.05, 0.03), (-0.05, -0.04)]


def seed_queries(client: httpx.Client, node: str, n: int = 30):
    langs = ["en", "te", "hi"]
    ok = 0
    for _ in range(n):
        farm = random.choice(FARMS)
        dlat, dlon = random.choice(_OFFSETS)
        payload = {
            "lat": farm["lat"] + dlat,
            "lon": farm["lon"] + dlon,
            "crop": farm["crop"],
            "language": random.choice(langs),
            "district": farm["district"],
        }
        r = client.post(f"{node}/api/advisory", json=payload)
        ok += r.status_code == 200
    print(f"  seeded {ok}/{n} advisory queries")


def seed_outbreak(client: httpx.Client, node: str, reports: int = 3):
    png = tiny_png()
    triggered = False
    for i in range(reports):
        r = client.post(
            f"{node}/api/diagnose",
            files={"image": (f"leaf_{i}.png", io.BytesIO(png), "image/png")},
            data={"crop": "paddy", "language": "en", "district": "Warangal",
                  "lat": 17.98, "lon": 79.53},
        )
        r.raise_for_status()
        body = r.json()
        print(f"  report {i + 1}/{reports}: {body['disease']}"
              f" (alert_triggered={body['alert_triggered']})")
        triggered = triggered or body["alert_triggered"]
    return triggered


def force_outbreak_alert(client: httpx.Client, node: str, peer: str):
    """Live-mode fallback: with DEMO_MODE=0 Gemini vision correctly refuses
    to diagnose the synthetic seed image with confidence, so no alert fires.
    Create the demo alert through the federation protocol instead: origin=TS,
    delivered to the origin node (stored as its own/local alert thanks to
    echo detection) and to the peer (stored as a federated early warning)."""
    import uuid

    alert = {
        "id": str(uuid.uuid4()),
        "origin_state": "TS",
        "disease": "Brown planthopper (Nilaparvata lugens)",
        "crop": "paddy",
        "district": "Warangal",
        "severity": "high",
        "report_count": 3,
        "window_days": 7,
        "message": ("Brown planthopper outbreak in paddy: 3 confirmed reports "
                    "in Warangal district (Telangana) within 7 days."),
    }
    for target in [node] + ([peer] if peer else []):
        resp = client.post(f"{target}/v1/alerts", json=alert)
        resp.raise_for_status()
        print(f"  alert delivered to {target} (duplicate={resp.json()['duplicate']})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--node", default="http://localhost:8001",
                        help="base URL of the origin (Telangana) node")
    parser.add_argument("--peer", default="http://localhost:8002",
                        help="peer node to verify alert arrival (blank to skip)")
    parser.add_argument("--queries", type=int, default=30,
                        help="advisory queries to seed (use ~10 against live-"
                             "Gemini nodes to stay inside free-tier rate limits)")
    args = parser.parse_args()

    with httpx.Client(timeout=60) as client:
        health = client.get(f"{args.node}/v1/health").json()
        print(f"Seeding node: {health['state_name']} ({args.node})")

        print("Seeding heatmap queries…")
        seed_queries(client, args.node, n=args.queries)

        print("Posting diagnosis reports (outbreak threshold = 3)…")
        triggered = seed_outbreak(client, args.node)

        alerts = client.get(f"{args.node}/v1/alerts").json()["alerts"]
        if not triggered and not alerts:
            print("  no alert from diagnoses (live Gemini declined the synthetic "
                  "image — correct safety behaviour); forcing the demo alert "
                  "via the federation protocol…")
            force_outbreak_alert(client, args.node, args.peer)
            alerts = client.get(f"{args.node}/v1/alerts").json()["alerts"]
        print(f"Origin node now has {len(alerts)} alert(s).")

        if args.peer:
            try:
                peer_alerts = client.get(f"{args.peer}/v1/alerts").json()["alerts"]
                federated = [a for a in peer_alerts if a["received_from_peer"]]
                print(f"Peer node has {len(federated)} federated alert(s)"
                      f" — early warning delivered: {'YES' if federated else 'NO'}")
            except httpx.HTTPError as exc:
                print(f"Could not verify peer ({args.peer}): {exc}")

    print("Done. Open the officer dashboard to see stats, heatmap and alerts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
