"""Reverse geocoder: live resolution, caching, offline fallback."""

import httpx
import respx

from app.services.geocode import Geocoder

_NOMINATIM_BODY = {
    "address": {
        "state_district": "Pune District",
        "state": "Maharashtra",
        "country": "India",
    }
}


@respx.mock
def test_resolves_and_normalizes_district(tmp_path):
    route = respx.get(url__startswith="https://nominatim.openstreetmap.org").mock(
        return_value=httpx.Response(200, json=_NOMINATIM_BODY))
    geocoder = Geocoder(cache_dir=tmp_path)
    assert geocoder.district_for(18.52, 73.86) == "Pune"  # " District" stripped
    assert route.called


@respx.mock
def test_caches_per_coordinate(tmp_path):
    route = respx.get(url__startswith="https://nominatim.openstreetmap.org").mock(
        return_value=httpx.Response(200, json=_NOMINATIM_BODY))
    geocoder = Geocoder(cache_dir=tmp_path)
    geocoder.district_for(18.52, 73.86)
    geocoder.district_for(18.524, 73.858)  # same 2-decimal bucket
    assert route.call_count == 1


@respx.mock
def test_offline_falls_back_to_nearest_farm(tmp_path):
    respx.get(url__startswith="https://nominatim.openstreetmap.org").mock(
        side_effect=httpx.ConnectError("no network"))
    geocoder = Geocoder(cache_dir=tmp_path)
    # Near the Warangal demo farm → farm fallback district.
    assert geocoder.district_for(17.98, 79.53) == "Warangal"


@respx.mock
def test_empty_address_falls_back(tmp_path):
    respx.get(url__startswith="https://nominatim.openstreetmap.org").mock(
        return_value=httpx.Response(200, json={"address": {}}))
    geocoder = Geocoder(cache_dir=tmp_path)
    assert geocoder.district_for(21.33, 83.62) == "Bargarh"
