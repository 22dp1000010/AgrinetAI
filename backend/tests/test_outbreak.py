"""Outbreak-threshold logic: N reports of the same disease in the same
district within the window raises exactly one alert."""

from app import db
from app.services.federation import FederationService
from tests.conftest import make_settings


def make_service(tmp_path, **overrides) -> FederationService:
    settings = make_settings(tmp_path, **overrides)
    conn = db.connect(settings.database_path)
    return FederationService(settings, conn)


def test_below_threshold_no_alert(tmp_path):
    svc = make_service(tmp_path)
    assert svc.record_report_and_check_outbreak("BPH", "paddy", "Warangal") is None
    assert svc.record_report_and_check_outbreak("BPH", "paddy", "Warangal") is None
    assert svc.list_alerts() == []


def test_threshold_crossed_creates_alert(tmp_path):
    svc = make_service(tmp_path)
    svc.record_report_and_check_outbreak("BPH", "paddy", "Warangal")
    svc.record_report_and_check_outbreak("BPH", "paddy", "Warangal")
    alert = svc.record_report_and_check_outbreak("BPH", "paddy", "Warangal")
    assert alert is not None
    assert alert.report_count == 3
    assert alert.origin_state == "TS"
    assert alert.severity == "high"
    assert "Warangal" in alert.message
    assert len(svc.list_alerts()) == 1


def test_no_duplicate_alert_for_same_outbreak(tmp_path):
    svc = make_service(tmp_path)
    for _ in range(3):
        svc.record_report_and_check_outbreak("BPH", "paddy", "Warangal")
    # A 4th report must not raise a second alert for the same outbreak.
    assert svc.record_report_and_check_outbreak("BPH", "paddy", "Warangal") is None
    assert len(svc.list_alerts()) == 1


def test_different_district_counts_separately(tmp_path):
    svc = make_service(tmp_path)
    svc.record_report_and_check_outbreak("BPH", "paddy", "Warangal")
    svc.record_report_and_check_outbreak("BPH", "paddy", "Warangal")
    assert svc.record_report_and_check_outbreak("BPH", "paddy", "Nalgonda") is None
    assert svc.list_alerts() == []


def test_different_disease_counts_separately(tmp_path):
    svc = make_service(tmp_path)
    svc.record_report_and_check_outbreak("BPH", "paddy", "Warangal")
    svc.record_report_and_check_outbreak("BPH", "paddy", "Warangal")
    assert svc.record_report_and_check_outbreak("blast", "paddy", "Warangal") is None


def test_configurable_threshold(tmp_path):
    svc = make_service(tmp_path, outbreak_threshold=2)
    svc.record_report_and_check_outbreak("BPH", "paddy", "Warangal")
    alert = svc.record_report_and_check_outbreak("BPH", "paddy", "Warangal")
    assert alert is not None and alert.report_count == 2
