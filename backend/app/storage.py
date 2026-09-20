"""Storage backends behind one interface.

- `SQLiteStore` (default): wraps the repository functions in db.py — zero
  external dependencies, used for local dev and tests. Data lives in a file.
- `FirestoreStore`: persistent, serverless — survives Cloud Run instance
  restarts. Selected with DB_BACKEND=firestore; uses Application Default
  Credentials (the Cloud Run service account). Collections are prefixed with
  the state id so both nodes can share one Firestore database.

Aggregations in FirestoreStore are done client-side: at advisory-network
scale per node this is thousands of small documents, and it avoids composite
index management entirely.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import db
from .config import Settings

log = logging.getLogger(__name__)


class Store(ABC):
    """The persistence contract every backend implements."""

    @abstractmethod
    def log_query(self, kind, lat, lon, crop, district, language): ...

    @abstractmethod
    def query_stats(self) -> dict: ...

    @abstractmethod
    def heatmap_points(self) -> list[dict]: ...

    @abstractmethod
    def add_disease_report(self, disease, crop, district, confidence): ...

    @abstractmethod
    def count_recent_reports(self, disease, district, window_days) -> int: ...

    @abstractmethod
    def upsert_alert(self, alert: dict, received_from_peer: bool) -> bool: ...

    @abstractmethod
    def list_alerts(self) -> list[dict]: ...

    @abstractmethod
    def upsert_insight(self, insight: dict) -> bool: ...

    @abstractmethod
    def list_insights(self) -> list[dict]: ...

    @abstractmethod
    def cache_get(self, prompt_hash: str, ttl_hours: int = 24) -> str | None: ...

    @abstractmethod
    def cache_put(self, prompt_hash: str, response: str): ...


class SQLiteStore(Store):
    def __init__(self, db_path: Path):
        self.conn = db.connect(db_path)

    def log_query(self, kind, lat, lon, crop, district, language):
        db.log_query(self.conn, kind, lat, lon, crop, district, language)

    def query_stats(self):
        return db.query_stats(self.conn)

    def heatmap_points(self):
        return db.heatmap_points(self.conn)

    def add_disease_report(self, disease, crop, district, confidence):
        db.add_disease_report(self.conn, disease, crop, district, confidence)

    def count_recent_reports(self, disease, district, window_days):
        return db.count_recent_reports(self.conn, disease, district, window_days)

    def upsert_alert(self, alert, received_from_peer):
        return db.upsert_alert(self.conn, alert, received_from_peer)

    def list_alerts(self):
        return db.list_alerts(self.conn)

    def upsert_insight(self, insight):
        return db.upsert_insight(self.conn, insight)

    def list_insights(self):
        return db.list_insights(self.conn)

    def cache_get(self, prompt_hash, ttl_hours=24):
        return db.cache_get(self.conn, prompt_hash, ttl_hours)

    def cache_put(self, prompt_hash, response):
        db.cache_put(self.conn, prompt_hash, response)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class FirestoreStore(Store):
    def __init__(self, state_id: str, project: str = ""):
        from google.cloud import firestore  # deferred: cloud-only dependency

        self._fs = firestore.Client(project=project or None)
        self._prefix = state_id.lower()

    def _col(self, name: str):
        return self._fs.collection(f"{self._prefix}_{name}")

    # --- queries ---

    def log_query(self, kind, lat, lon, crop, district, language):
        self._col("queries").add({
            "kind": kind,
            "lat": round(lat, 2) if lat is not None else None,
            "lon": round(lon, 2) if lon is not None else None,
            "crop": crop, "district": district, "language": language,
            "created_at": _utcnow_iso(),
        })

    def _all_queries(self) -> list[dict]:
        return [d.to_dict() for d in self._col("queries").stream()]

    def query_stats(self):
        queries = self._all_queries()
        today_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        crops: dict[str, int] = {}
        for q in queries:
            if q.get("crop"):
                crops[q["crop"]] = crops.get(q["crop"], 0) + 1
        diseases: dict[str, int] = {}
        for r in self._col("disease_reports").stream():
            d = r.to_dict().get("disease")
            if d:
                diseases[d] = diseases.get(d, 0) + 1
        top = lambda counts, key: [  # noqa: E731
            {key: k, "count": v}
            for k, v in sorted(counts.items(), key=lambda kv: -kv[1])[:5]
        ]
        return {
            "total_queries": len(queries),
            "queries_today": sum(
                1 for q in queries if (q.get("created_at") or "").startswith(today_prefix)
            ),
            "top_crops": top(crops, "crop"),
            "top_diseases": top(diseases, "disease"),
        }

    def heatmap_points(self):
        buckets: dict[tuple, int] = {}
        for q in self._all_queries():
            if q.get("lat") is None:
                continue
            key = (q["lat"], q["lon"])
            buckets[key] = buckets.get(key, 0) + 1
        return [{"lat": k[0], "lon": k[1], "count": v} for k, v in buckets.items()]

    # --- disease reports ---

    def add_disease_report(self, disease, crop, district, confidence):
        self._col("disease_reports").add({
            "disease": disease, "crop": crop, "district": district,
            "confidence": confidence, "created_at": _utcnow_iso(),
        })

    def count_recent_reports(self, disease, district, window_days):
        since = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()
        docs = (self._col("disease_reports")
                .where("disease", "==", disease)
                .where("district", "==", district).stream())
        return sum(1 for d in docs if d.to_dict().get("created_at", "") >= since)

    # --- alerts ---

    def upsert_alert(self, alert, received_from_peer):
        ref = self._col("alerts").document(alert["id"])
        if ref.get().exists:
            return False
        ref.set({**alert,
                 "received_from_peer": bool(received_from_peer),
                 "created_at": alert.get("created_at") or _utcnow_iso()})
        return True

    def list_alerts(self):
        alerts = [d.to_dict() for d in self._col("alerts").stream()]
        alerts.sort(key=lambda a: a.get("created_at", ""), reverse=True)
        return alerts

    # --- insights ---

    def upsert_insight(self, insight):
        ref = self._col("insights").document(insight["id"])
        if ref.get().exists:
            return False
        ref.set({**insight,
                 "created_at": insight.get("created_at") or _utcnow_iso()})
        return True

    def list_insights(self):
        insights = [d.to_dict() for d in self._col("insights").stream()]
        insights.sort(key=lambda i: i.get("created_at", ""), reverse=True)
        return insights

    # --- gemini cache ---

    def cache_get(self, prompt_hash, ttl_hours=24):
        doc = self._col("gemini_cache").document(prompt_hash).get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        created = datetime.fromisoformat(data["created_at"])
        if datetime.now(timezone.utc) - created > timedelta(hours=ttl_hours):
            return None
        return data["response"]

    def cache_put(self, prompt_hash, response):
        self._col("gemini_cache").document(prompt_hash).set({
            "response": response, "created_at": _utcnow_iso(),
        })


def build_store(settings: Settings) -> Store:
    if settings.db_backend == "firestore":
        try:
            store = FirestoreStore(settings.state_id, settings.firestore_project)
            log.info("Using Firestore backend (prefix %s_)", settings.state_id.lower())
            return store
        except Exception as exc:
            log.warning("Firestore init failed (%s); falling back to SQLite", exc)
    return SQLiteStore(settings.database_path)
