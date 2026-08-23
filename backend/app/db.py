"""SQLite data-access layer.

Thin repository-style functions over sqlite3 so the storage backend can be
swapped (e.g. Firestore) without touching services or routers. Every function
takes an explicit connection produced by `connect()`.
"""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,              -- advisory | diagnose | ask
    lat REAL,                        -- rounded to 2 decimals (privacy)
    lon REAL,
    crop TEXT,
    district TEXT,
    language TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS disease_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    disease TEXT NOT NULL,
    crop TEXT,
    district TEXT NOT NULL,
    confidence TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,             -- idempotency key across the federation
    origin_state TEXT NOT NULL,
    disease TEXT NOT NULL,
    crop TEXT,
    district TEXT,
    severity TEXT NOT NULL,
    report_count INTEGER NOT NULL,
    window_days INTEGER NOT NULL,
    message TEXT,
    received_from_peer INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS insights (
    id TEXT PRIMARY KEY,
    state_id TEXT NOT NULL,
    district TEXT,
    crop TEXT,
    type TEXT NOT NULL,
    summary TEXT NOT NULL,
    evidence TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gemini_cache (
    prompt_hash TEXT PRIMARY KEY,
    response TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


# --- queries (for dashboard stats / heatmap) ---

def log_query(conn, kind, lat, lon, crop, district, language):
    lat = round(lat, 2) if lat is not None else None
    lon = round(lon, 2) if lon is not None else None
    conn.execute(
        "INSERT INTO queries (kind, lat, lon, crop, district, language, created_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (kind, lat, lon, crop, district, language, utcnow_iso()),
    )
    conn.commit()


def query_stats(conn) -> dict:
    total = conn.execute("SELECT COUNT(*) c FROM queries").fetchone()["c"]
    today = conn.execute(
        "SELECT COUNT(*) c FROM queries WHERE created_at >= ?",
        (datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00"),),
    ).fetchone()["c"]
    top_crops = [
        {"crop": r["crop"], "count": r["c"]}
        for r in conn.execute(
            "SELECT crop, COUNT(*) c FROM queries WHERE crop IS NOT NULL"
            " GROUP BY crop ORDER BY c DESC LIMIT 5"
        )
    ]
    top_diseases = [
        {"disease": r["disease"], "count": r["c"]}
        for r in conn.execute(
            "SELECT disease, COUNT(*) c FROM disease_reports"
            " GROUP BY disease ORDER BY c DESC LIMIT 5"
        )
    ]
    return {
        "total_queries": total,
        "queries_today": today,
        "top_crops": top_crops,
        "top_diseases": top_diseases,
    }


def heatmap_points(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT lat, lon, COUNT(*) c FROM queries"
        " WHERE lat IS NOT NULL GROUP BY lat, lon"
    )
    return [{"lat": r["lat"], "lon": r["lon"], "count": r["c"]} for r in rows]


# --- disease reports & outbreak detection ---

def add_disease_report(conn, disease, crop, district, confidence):
    conn.execute(
        "INSERT INTO disease_reports (disease, crop, district, confidence, created_at)"
        " VALUES (?,?,?,?,?)",
        (disease, crop, district, confidence, utcnow_iso()),
    )
    conn.commit()


def count_recent_reports(conn, disease, district, window_days) -> int:
    since = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()
    row = conn.execute(
        "SELECT COUNT(*) c FROM disease_reports"
        " WHERE disease = ? AND district = ? AND created_at >= ?",
        (disease, district, since),
    ).fetchone()
    return row["c"]


# --- alerts ---

def upsert_alert(conn, alert: dict, received_from_peer: bool) -> bool:
    """Insert an alert; returns False if it already exists (idempotent)."""
    exists = conn.execute(
        "SELECT 1 FROM alerts WHERE id = ?", (alert["id"],)
    ).fetchone()
    if exists:
        return False
    conn.execute(
        "INSERT INTO alerts (id, origin_state, disease, crop, district, severity,"
        " report_count, window_days, message, received_from_peer, created_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            alert["id"], alert["origin_state"], alert["disease"], alert.get("crop"),
            alert.get("district"), alert["severity"], alert["report_count"],
            alert["window_days"], alert.get("message"),
            1 if received_from_peer else 0,
            alert.get("created_at") or utcnow_iso(),
        ),
    )
    conn.commit()
    return True


def list_alerts(conn) -> list[dict]:
    rows = conn.execute("SELECT * FROM alerts ORDER BY created_at DESC")
    return [dict(r) | {"received_from_peer": bool(r["received_from_peer"])} for r in rows]


# --- insights ---

def upsert_insight(conn, insight: dict) -> bool:
    exists = conn.execute(
        "SELECT 1 FROM insights WHERE id = ?", (insight["id"],)
    ).fetchone()
    if exists:
        return False
    conn.execute(
        "INSERT INTO insights (id, state_id, district, crop, type, summary, evidence, created_at)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (
            insight["id"], insight["state_id"], insight.get("district"),
            insight.get("crop"), insight["type"], insight["summary"],
            json.dumps(insight.get("evidence")) if insight.get("evidence") else None,
            insight.get("created_at") or utcnow_iso(),
        ),
    )
    conn.commit()
    return True


def list_insights(conn) -> list[dict]:
    rows = conn.execute("SELECT * FROM insights ORDER BY created_at DESC")
    out = []
    for r in rows:
        d = dict(r)
        d["evidence"] = json.loads(d["evidence"]) if d["evidence"] else None
        out.append(d)
    return out


# --- gemini response cache ---

def cache_get(conn, prompt_hash: str, ttl_hours: int = 24) -> str | None:
    row = conn.execute(
        "SELECT response, created_at FROM gemini_cache WHERE prompt_hash = ?",
        (prompt_hash,),
    ).fetchone()
    if not row:
        return None
    created = datetime.fromisoformat(row["created_at"])
    if datetime.now(timezone.utc) - created > timedelta(hours=ttl_hours):
        return None
    return row["response"]


def cache_put(conn, prompt_hash: str, response: str):
    conn.execute(
        "INSERT OR REPLACE INTO gemini_cache (prompt_hash, response, created_at)"
        " VALUES (?,?,?)",
        (prompt_hash, response, utcnow_iso()),
    )
    conn.commit()
