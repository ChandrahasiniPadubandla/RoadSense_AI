import json
import re
import socket
import urllib.error

import pytest

from app.routers import voice as voice_router
from app.routers.voice import extract_route_from_voice
from app.schemas.voice import VoiceRouteExtractRequest
from app.services import geocoding
from app.services.geocoding import GeocodingError
from app.services.voice_service import (
    clean_voice_text,
    extract_location_fragments,
    extract_route_from_text,
)


def _key(text):
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def candidate(name, latitude=17.3850, longitude=78.4867, **extra):
    payload = {
        "name": name,
        "display_name": name,
        "primary_name": name,
        "secondary_name": None,
        "latitude": latitude,
        "longitude": longitude,
        "type": "location",
        "category": "place",
        "address": {},
    }
    payload.update(extra)
    return payload


class FakeGeocoder:
    """Deterministic stand-in for the geocoding provider (no real network calls)."""

    def __init__(self, mapping):
        self.mapping = {_key(k): v for k, v in mapping.items()}
        self.calls = []

    def __call__(self, query):
        self.calls.append(query)
        result = self.mapping.get(_key(query), [])
        if isinstance(result, Exception):
            raise result
        return list(result)


# ---------------------------------------------------------------------------
# The exact example from the bug report
# ---------------------------------------------------------------------------
def test_example_route_resolves_full_station_names():
    geocoder = FakeGeocoder({
        "LB Nagar Metro Station": [candidate("L. B. Nagar Metro Station")],
        "Uppal Metro Station": [
            candidate("Uppal Metro Station Parking (towards LB Nagar)"),
            candidate("Metro Bus Station Uppal"),
        ],
    })

    result = extract_route_from_text(
        "LB Nagar Metro Station to Uppal Metro Station", geocoder=geocoder
    )

    assert result["success"] is True
    assert result["start_location"] == "LB Nagar Metro Station"
    assert result["end_location"] == "Uppal Metro Station"
    assert result["start_status"] == "matched"
    assert result["end_status"] == "matched"
    assert result["method"] == "geocoding"
    assert result["start_coordinates"]["latitude"] == pytest.approx(17.3850)
    assert result["end_coordinates"]["longitude"] == pytest.approx(78.4867)


def test_example_route_fields_are_not_swapped():
    geocoder = FakeGeocoder({
        "LB Nagar Metro Station": [candidate("LB Nagar Metro Station")],
        "Uppal Metro Station": [candidate("Uppal Metro Station")],
    })

    result = extract_route_from_text(
        "LB Nagar Metro Station to Uppal Metro Station", geocoder=geocoder
    )

    assert result["start_location"] == "LB Nagar Metro Station"
    assert result["end_location"] == "Uppal Metro Station"


# ---------------------------------------------------------------------------
# A shorter place name overlapping a full station name must never be substituted
# ---------------------------------------------------------------------------
def test_shorter_overlapping_place_is_not_substituted():
    geocoder = FakeGeocoder({
        "Uppal Metro Station": [candidate("Uppal", category="suburb")],
        "Nagole": [candidate("Nagole")],
    })

    result = extract_route_from_text("Uppal Metro Station to Nagole", geocoder=geocoder)

    assert result["start_location"] is None
    assert result["start_status"] == "ambiguous"
    assert result["success"] is False
    assert result["method"] == "partial"
    assert result["end_location"] == "Nagole"
    # The shorter name is only offered as a suggestion, never auto-filled.
    assert "Uppal" not in (result["start_location"] or "")
    assert any(match["name"] == "Uppal" for match in result["start_matches"])


def test_overlapping_prefix_place_does_not_upgrade_to_full_station():
    geocoder = FakeGeocoder({
        "Uppal": [candidate("Uppal Metro Station")],
        "Nagole": [candidate("Nagole")],
    })

    result = extract_route_from_text("Uppal to Nagole", geocoder=geocoder)

    # "Uppal Metro Station" contains "uppal" so it validates the full phrase
    # "Uppal" without inventing extra words.
    assert result["start_location"] == "Uppal"
    assert result["start_status"] == "matched"


# ---------------------------------------------------------------------------
# Parsing / speech handling stays intact
# ---------------------------------------------------------------------------
def test_route_parsing_is_preserved():
    start, end = extract_location_fragments("LB Nagar Metro Station to Uppal Metro Station")
    assert start == "LB Nagar Metro Station"
    assert end == "Uppal Metro Station"


def test_destination_first_phrases_are_still_normalized():
    geocoder = FakeGeocoder({
        "Nagole": [candidate("Nagole")],
        "Uppal": [candidate("Uppal")],
    })

    result = extract_route_from_text("Navigate to Nagole from Uppal", geocoder=geocoder)

    assert result["start_location"] == "Uppal"
    assert result["end_location"] == "Nagole"


def test_conversational_prefixes_and_fillers_are_stripped():
    assert clean_voice_text("What is the traffic from Uppal to Nagole?") == "from Uppal to Nagole?"

    geocoder = FakeGeocoder({
        "Kondapur": [candidate("Kondapur")],
        "Nagole": [candidate("Nagole")],
    })

    result = extract_route_from_text("from Kondapur to Nagole right now", geocoder=geocoder)

    assert result["start_location"] == "Kondapur"
    assert result["end_location"] == "Nagole"


# ---------------------------------------------------------------------------
# Multi-word dataset locations
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("location", ["Financial District", "Banjara Hills", "Hitech City"])
def test_multiword_locations_resolve_to_the_full_phrase(location):
    geocoder = FakeGeocoder({
        location: [candidate(location)],
        "Uppal": [candidate("Uppal")],
    })

    result = extract_route_from_text(f"from {location} to Uppal", geocoder=geocoder)

    assert result["start_location"] == location
    assert result["end_location"] == "Uppal"


# ---------------------------------------------------------------------------
# Validation behavior: no result / ambiguous / timeout / rate limit
# ---------------------------------------------------------------------------
def test_no_geocoding_result_is_reported_as_not_found():
    geocoder = FakeGeocoder({"Uppal": [candidate("Uppal")]})

    result = extract_route_from_text("from Atlantis to El Dorado", geocoder=geocoder)

    assert result["success"] is False
    assert result["start_status"] == "not_found"
    assert result["end_status"] == "not_found"
    assert result["start_location"] is None
    assert result["end_location"] is None


def test_ambiguous_results_are_surfaced_without_choosing():
    geocoder = FakeGeocoder({
        "Ameerpet Area": [candidate("Ameerpet"), candidate("Ameerpet Metro Junction")],
        "Uppal": [candidate("Uppal")],
    })

    result = extract_route_from_text("from Ameerpet Area to Uppal", geocoder=geocoder)

    assert result["start_location"] is None
    assert result["start_status"] == "ambiguous"
    assert len(result["start_matches"]) >= 2
    assert result["message"] is not None


def test_rate_limited_lookup_is_reported_clearly():
    geocoder = FakeGeocoder({
        "Uppal Metro Station": GeocodingError("rate_limited", "The location service is rate limited."),
        "Nagole": [candidate("Nagole")],
    })

    result = extract_route_from_text("Uppal Metro Station to Nagole", geocoder=geocoder)

    assert result["start_status"] == "rate_limited"
    assert result["start_location"] is None
    assert "rate" in result["message"].lower()


def test_timeout_lookup_is_reported_clearly():
    geocoder = FakeGeocoder({
        "Uppal Metro Station": GeocodingError("timeout", "The location service timed out."),
        "Nagole": [candidate("Nagole")],
    })

    result = extract_route_from_text("Uppal Metro Station to Nagole", geocoder=geocoder)

    assert result["start_status"] == "timeout"
    assert result["start_location"] is None
    assert "timed out" in result["message"].lower()


def test_provider_error_does_not_substitute_a_shorter_place():
    geocoder = FakeGeocoder({
        "Uppal Metro Station": GeocodingError("error", "The location service is unreachable."),
    })

    result = extract_route_from_text("Uppal Metro Station to Nagole", geocoder=geocoder)

    assert result["start_status"] == "error"
    assert result["start_location"] is None
    assert result["end_location"] is None


# ---------------------------------------------------------------------------
# Endpoint uses the backend geocoder and preserves the contract
# ---------------------------------------------------------------------------
def test_voice_endpoint_resolves_through_geocoding(monkeypatch):
    geocoder = FakeGeocoder({
        "LB Nagar Metro Station": [candidate("LB Nagar Metro Station", latitude=17.3457, longitude=78.5522)],
        "Uppal Metro Station": [candidate("Uppal Metro Station", latitude=17.4009, longitude=78.5599)],
    })
    monkeypatch.setattr(voice_router, "extract_route_from_text", lambda text, db=None: extract_route_from_text(text, db, geocoder=geocoder))

    response = extract_route_from_voice(
        VoiceRouteExtractRequest(text="LB Nagar Metro Station to Uppal Metro Station"),
        None,
    )

    body = response.model_dump()
    assert body["success"] is True
    assert body["start_location"] == "LB Nagar Metro Station"
    assert body["end_location"] == "Uppal Metro Station"
    assert body["start_status"] == "matched"
    assert body["end_status"] == "matched"
    assert body["start_latitude"] == pytest.approx(17.3457)
    assert body["end_longitude"] == pytest.approx(78.5599)


# ---------------------------------------------------------------------------
# Provider client mapping (urlopen is mocked — no network / no paid calls)
# ---------------------------------------------------------------------------
def test_client_maps_http_429_to_rate_limited(monkeypatch):
    def _raise(*_args, **_kwargs):
        raise urllib.error.HTTPError("https://photon.komoot.io/api/", 429, "Too Many Requests", {}, None)

    monkeypatch.setattr(geocoding.urllib.request, "urlopen", _raise)

    with pytest.raises(GeocodingError) as excinfo:
        geocoding.search_geocoding_candidates("Uppal Metro Station")
    assert excinfo.value.status == "rate_limited"


def test_client_maps_socket_timeout_to_timeout(monkeypatch):
    def _raise(*_args, **_kwargs):
        raise socket.timeout("timed out")

    monkeypatch.setattr(geocoding.urllib.request, "urlopen", _raise)

    with pytest.raises(GeocodingError) as excinfo:
        geocoding.search_geocoding_candidates("Uppal Metro Station")
    assert excinfo.value.status == "timeout"


def test_client_maps_http_500_to_error(monkeypatch):
    def _raise(*_args, **_kwargs):
        raise urllib.error.HTTPError("https://photon.komoot.io/api/", 500, "Server Error", {}, None)

    monkeypatch.setattr(geocoding.urllib.request, "urlopen", _raise)

    with pytest.raises(GeocodingError) as excinfo:
        geocoding.search_geocoding_candidates("Uppal Metro Station")
    assert excinfo.value.status == "error"


def test_client_normalizes_provider_features(monkeypatch):
    payload = {
        "features": [
            {
                "geometry": {"coordinates": [78.5605, 17.3999]},
                "properties": {"name": "Uppal Metro Station", "city": "Hyderabad", "osm_key": "railway"},
            }
        ]
    }

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    monkeypatch.setattr(geocoding.urllib.request, "urlopen", lambda *_a, **_k: _Response())

    results = geocoding.search_geocoding_candidates("Uppal Metro Station")

    assert len(results) == 1
    assert results[0]["name"] == "Uppal Metro Station"
    assert results[0]["latitude"] == pytest.approx(17.3999)
    assert results[0]["longitude"] == pytest.approx(78.5605)
