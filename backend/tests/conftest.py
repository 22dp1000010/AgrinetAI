"""Shared fixtures: an app wired with fake data providers (no network) and
DEMO_MODE Gemini (no API key), on a throwaway per-test database."""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.advisory import AdvisoryService
from app.services.ask import AskService
from app.services.planner import PlannerService
from app.services.warnings import WarningsService


class FakeSatellite:
    def get_features(self, lat, lon):
        return {"ndvi_mean": 0.62, "ndvi_trend": "declining", "ndwi_mean": -0.18,
                "window_days": 30, "source": "fake satellite"}


class FakeSoil:
    def get_properties(self, lat, lon):
        return {"ph": 6.1, "soc_g_per_kg": 9.5, "clay_pct": 30.0,
                "sand_pct": 42.0, "source": "fake soil"}


class FakeWeather:
    def get_forecast(self, lat, lon):
        return {"rain_next_7d_mm": 12.0, "max_temp_c": 33.0, "min_temp_c": 24.0,
                "mean_humidity_pct": 80, "max_wind_kmh": 15.0, "daily": [],
                "source": "fake weather"}


class FakeGeocoder:
    """No network: resolve via the demo-farm fallback, same as offline."""

    def district_for(self, lat, lon):
        from app.services.farms import infer_district
        return infer_district(lat, lon)


def make_settings(tmp_path, **overrides) -> Settings:
    defaults = dict(
        state_id="TS", demo_mode=True, peers="",
        db_path=str(tmp_path / "test.db"),
        outbreak_threshold=3, outbreak_window_days=7,
    )
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


@pytest.fixture
def settings(tmp_path):
    return make_settings(tmp_path)


@pytest.fixture
def app(settings):
    application = create_app(settings)
    c = application.state.container
    c.satellite, c.soil, c.weather = FakeSatellite(), FakeSoil(), FakeWeather()
    c.geocoder = FakeGeocoder()
    # Rebuild the pipelines over the fakes (they captured the real providers).
    c.advisory = AdvisoryService(
        c.satellite, c.soil, c.weather, c.retriever, c.gemini, c.store, c.geocoder,
    )
    c.planner = PlannerService(
        c.satellite, c.soil, c.weather, c.retriever, c.gemini, c.store, c.geocoder,
    )
    c.ask = AskService(c.retriever, c.gemini, c.store, c.geocoder)
    c.warnings = WarningsService(c.retriever, c.store, c.geocoder)
    return application


@pytest.fixture
def container(app):
    return app.state.container


@pytest.fixture
def client(app):
    return TestClient(app)
