"""Federation service — the interoperability layer (spec §5.4).

Handles outbreak detection, alert creation, idempotent receipt of peer
alerts, and pushing alerts to all configured peers with retry. Peer push is
best-effort: a down peer never breaks the farmer-facing request.
"""

import logging
from sqlite3 import Connection

import httpx

from .. import db
from ..config import Settings
from ..models.protocol import Alert, Insight, ModelRegistryEntry, Peer

log = logging.getLogger(__name__)

_PUSH_ATTEMPTS = 3
_PUSH_TIMEOUT_S = 5.0


class FederationService:
    def __init__(self, settings: Settings, conn: Connection,
                 http_client: httpx.Client | None = None):
        self.settings = settings
        self.conn = conn
        # Injectable for tests; created lazily otherwise.
        self._http = http_client

    @property
    def http(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(timeout=_PUSH_TIMEOUT_S)
        return self._http

    # --- outbreak detection ---

    def record_report_and_check_outbreak(self, disease: str, crop: str | None,
                                         district: str,
                                         confidence: str = "high") -> Alert | None:
        """Store an anonymized disease report; if it crosses the outbreak
        threshold, create an alert and push it to peers."""
        db.add_disease_report(self.conn, disease, crop, district, confidence)
        count = db.count_recent_reports(
            self.conn, disease, district, self.settings.outbreak_window_days
        )
        if count < self.settings.outbreak_threshold:
            return None
        if self._recent_alert_exists(disease, district):
            return None

        alert = Alert(
            origin_state=self.settings.state_id,
            disease=disease,
            crop=crop,
            district=district,
            severity="high",
            report_count=count,
            window_days=self.settings.outbreak_window_days,
            message=(
                f"{disease} outbreak in {crop or 'crops'}: {count} confirmed reports "
                f"in {district} district ({self.settings.state_name}) within "
                f"{self.settings.outbreak_window_days} days."
            ),
        )
        db.upsert_alert(self.conn, alert.model_dump(mode="json"), received_from_peer=False)
        self.push_alert_to_peers(alert)
        return alert

    def _recent_alert_exists(self, disease: str, district: str) -> bool:
        return any(
            a["disease"] == disease and a["district"] == district
            and not a["received_from_peer"]
            for a in db.list_alerts(self.conn)
        )

    # --- protocol operations ---

    def receive_alert(self, alert: Alert) -> bool:
        """Idempotent receipt of an alert pushed by a peer node."""
        return db.upsert_alert(self.conn, alert.model_dump(mode="json"),
                               received_from_peer=True)

    def push_alert_to_peers(self, alert: Alert) -> dict[str, bool]:
        results = {}
        payload = alert.model_dump(mode="json")
        for base_url in self.settings.peer_urls:
            results[base_url] = self._push_one(base_url, payload)
        return results

    def _push_one(self, base_url: str, payload: dict) -> bool:
        url = f"{base_url}/v1/alerts"
        for attempt in range(_PUSH_ATTEMPTS):
            try:
                resp = self.http.post(url, json=payload)
                if resp.status_code < 300:
                    log.info("Alert %s delivered to %s", payload["id"], base_url)
                    return True
                log.warning("Peer %s rejected alert (%s)", base_url, resp.status_code)
            except httpx.HTTPError as exc:
                log.warning("Push to %s failed (attempt %d): %s",
                            base_url, attempt + 1, exc)
        return False

    def list_alerts(self) -> list[dict]:
        return db.list_alerts(self.conn)

    def list_insights(self) -> list[dict]:
        return db.list_insights(self.conn)

    def add_insight(self, insight: Insight) -> bool:
        return db.upsert_insight(self.conn, insight.model_dump(mode="json"))

    def peers(self) -> list[Peer]:
        peers = []
        for url in self.settings.peer_urls:
            state_id, name = self._identify_peer(url)
            peers.append(Peer(state_id=state_id, name=name, base_url=url))
        return peers

    @staticmethod
    def _identify_peer(url: str) -> tuple[str, str]:
        # Best-effort identity from URL; a production registry would resolve
        # this via each peer's /v1/health.
        lowered = url.lower()
        if "od" in lowered or "8002" in lowered:
            return "OD", "Odisha State Node"
        if "ts" in lowered or "8001" in lowered:
            return "TS", "Telangana State Node"
        return "??", url

    def model_registry(self) -> list[ModelRegistryEntry]:
        """Stub registry proving the protocol supports model sharing —
        states can publish fine-tuned Gemma disease models here."""
        return [
            ModelRegistryEntry(
                name="gemma-paddy-disease-classifier",
                version="0.1.0-roadmap",
                task="leaf-image disease classification (paddy)",
                trained_by=self.settings.state_id,
                artifact_url=None,
            )
        ]
