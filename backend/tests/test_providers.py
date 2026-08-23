"""Weather/soil clients against mocked HTTP: normalization, cache hits,
offline fallback. The satellite cached provider is exercised on real repo data."""

import httpx
import respx

from app.services.satellite import CachedSatelliteProvider
from app.services.soil import SoilClient
from app.services.weather import WeatherClient

_OPEN_METEO_BODY = {
    "daily": {
        "time": ["2026-08-22", "2026-08-23"],
        "temperature_2m_max": [33.1, 34.0],
        "temperature_2m_min": [24.0, 23.5],
        "precipitation_sum": [8.0, 4.0],
        "relative_humidity_2m_mean": [78, 82],
        "wind_speed_10m_max": [14.0, 19.0],
    }
}

_SOILGRIDS_BODY = {
    "properties": {
        "layers": [
            {"name": "phh2o", "depths": [{"values": {"mean": 61}}]},
            {"name": "soc", "depths": [{"values": {"mean": 98}}]},
            {"name": "clay", "depths": [{"values": {"mean": 320}}]},
            {"name": "sand", "depths": [{"values": {"mean": 410}}]},
        ]
    }
}


@respx.mock
def test_weather_normalizes_and_caches(tmp_path):
    route = respx.get(url__startswith="https://api.open-meteo.com").mock(
        return_value=httpx.Response(200, json=_OPEN_METEO_BODY))
    client = WeatherClient(cache_dir=tmp_path)

    first = client.get_forecast(17.98, 79.53)
    assert first["rain_next_7d_mm"] == 12.0
    assert first["max_temp_c"] == 34.0
    assert first["mean_humidity_pct"] == 80
    assert first["source"] == "Open-Meteo (live)"
    assert len(first["daily"]) == 2

    second = client.get_forecast(17.98, 79.53)
    assert second["source"] == "Open-Meteo (cached today)"
    assert route.call_count == 1  # cache hit, no second HTTP call


@respx.mock
def test_weather_offline_fallback(tmp_path):
    respx.get(url__startswith="https://api.open-meteo.com").mock(
        side_effect=httpx.ConnectError("no network"))
    client = WeatherClient(cache_dir=tmp_path)
    result = client.get_forecast(17.98, 79.53)
    assert result["rain_next_7d_mm"] == 42.0
    assert "offline default" in result["source"]


@respx.mock
def test_soil_normalizes_scaled_values_and_caches(tmp_path):
    route = respx.get(url__startswith="https://rest.isric.org").mock(
        return_value=httpx.Response(200, json=_SOILGRIDS_BODY))
    client = SoilClient(cache_dir=tmp_path)

    first = client.get_properties(17.98, 79.53)
    assert first["ph"] == 6.1          # 61 / 10
    assert first["soc_g_per_kg"] == 9.8
    assert first["clay_pct"] == 32.0
    assert first["source"] == "SoilGrids/ISRIC (live)"

    second = client.get_properties(17.98, 79.53)
    assert second["source"] == "SoilGrids/ISRIC (cached)"
    assert route.call_count == 1


@respx.mock
def test_soil_offline_fallback(tmp_path):
    respx.get(url__startswith="https://rest.isric.org").mock(
        side_effect=httpx.ConnectError("no network"))
    client = SoilClient(cache_dir=tmp_path)
    result = client.get_properties(17.98, 79.53)
    assert result["ph"] == 6.4
    assert "offline default" in result["source"]


def test_cached_satellite_nearest_neighbour():
    provider = CachedSatelliteProvider()  # real repo snapshots
    near_warangal = provider.get_features(17.9, 79.6)
    assert near_warangal["ndvi_mean"] == 0.62
    assert near_warangal["ndvi_trend"] == "declining"
    assert "Sentinel-2" in near_warangal["source"]
    near_bargarh = provider.get_features(21.4, 83.5)
    assert near_bargarh["ndvi_trend"] == "improving"


def test_cached_satellite_empty_dir(tmp_path):
    provider = CachedSatelliteProvider(cache_dir=tmp_path)
    result = provider.get_features(17.98, 79.53)
    assert result["ndvi_mean"] is None
    assert result["ndvi_trend"] == "unknown"
