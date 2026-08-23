"""AgriNet Protocol schema validation — the federation contract must reject
malformed payloads and default sensibly."""

import pytest
from pydantic import ValidationError

from app.models.protocol import Alert, Insight, Peer


def test_alert_minimal_valid():
    alert = Alert(origin_state="TS", disease="brown planthopper",
                  report_count=3, window_days=7)
    assert alert.id  # auto-generated
    assert alert.severity == "medium"
    assert alert.created_at is not None


def test_alert_rejects_bad_severity():
    with pytest.raises(ValidationError):
        Alert(origin_state="TS", disease="x", report_count=3,
              window_days=7, severity="catastrophic")


def test_alert_rejects_zero_reports():
    with pytest.raises(ValidationError):
        Alert(origin_state="TS", disease="x", report_count=0, window_days=7)


def test_alert_rejects_missing_disease():
    with pytest.raises(ValidationError):
        Alert(origin_state="TS", report_count=3, window_days=7)


def test_insight_valid_and_type_constrained():
    insight = Insight(state_id="OD", type="pest", summary="BPH pressure rising")
    assert insight.id
    with pytest.raises(ValidationError):
        Insight(state_id="OD", type="astrology", summary="nope")


def test_peer_roundtrip():
    peer = Peer(state_id="OD", name="Odisha State Node",
                base_url="http://localhost:8002")
    assert peer.last_sync is None
    assert Peer.model_validate(peer.model_dump()) == peer
