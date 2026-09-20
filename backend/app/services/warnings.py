"""Farmer-facing outbreak warnings.

Surfaces active alerts (local and federation-received) to farmers at a given
location: alerts in their own district are scoped "your_district", everything
else is a "regional" early warning. Each warning carries a prevention tip
retrieved from the grounded advisory corpus — no Gemini call, so this is
instant and quota-free.
"""

from datetime import datetime, timedelta, timezone

from ..models.schemas import Prevention, WarningItem
from ..storage import Store
from .farms import infer_district
from .rag import Retriever

# Alerts older than this are no longer shown to farmers.
ACTIVE_WINDOW_DAYS = 30


class WarningsService:
    def __init__(self, retriever: Retriever, store: Store):
        self.retriever = retriever
        self.store = store

    def for_location(self, lat: float, lon: float) -> list[WarningItem]:
        district = infer_district(lat, lon)
        cutoff = datetime.now(timezone.utc) - timedelta(days=ACTIVE_WINDOW_DAYS)
        warnings: list[WarningItem] = []
        for alert in self.store.list_alerts():
            created = datetime.fromisoformat(alert["created_at"])
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if created < cutoff:
                continue
            warnings.append(WarningItem(
                disease=alert["disease"],
                crop=alert.get("crop"),
                district=alert.get("district"),
                severity=alert["severity"],
                origin_state=alert["origin_state"],
                from_peer=alert["received_from_peer"],
                scope="your_district" if alert.get("district") == district else "regional",
                message=alert.get("message"),
                created_at=alert["created_at"],
                prevention=self._prevention_tip(alert),
            ))
        # Own-district warnings first, then by recency.
        warnings.sort(key=lambda w: (w.scope != "your_district", w.created_at), reverse=False)
        return warnings

    def _prevention_tip(self, alert: dict) -> Prevention | None:
        query = f"{alert['disease']} {alert.get('crop') or ''} prevention control manage"
        chunks = self.retriever.retrieve(query, k=1)
        if not chunks:
            return None
        return Prevention(text=chunks[0].text, source=chunks[0].source)
