import json
import os
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

# These focused tests use fakes and must collect from a clean clone without a
# developer's DATABASE_URL or any database service.
os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.database.models import GeocodeSuggestionCache, Road
from app.database.connection import get_db
from app.main import app
from app.routers import geocoding as geocoding_router
from app.services import geocoding, setup_service
from app.services.hotspot_service import sync_empirical_hotspots
from app.services.ml_service import _request_or_database_value


class _Query:
    def __init__(self, session, model):
        self.session = session
        self.model = model

    def filter(self, condition):
        self.condition = condition
        return self

    def order_by(self, *_args):
        return self

    def limit(self, *_args):
        return self

    def all(self):
        return []

    def first(self):
        if self.model is GeocodeSuggestionCache:
            key = self.condition.right.value
            return self.session.cache.get(key)
        return None


class _Session:
    def __init__(self):
        self.cache = {}
        self.pending = []

    def query(self, model):
        return _Query(self, model)

    def add(self, value):
        self.pending.append(value)

    def commit(self):
        for item in self.pending:
            self.cache[item.cache_key] = item
        self.pending.clear()

    def rollback(self):
        self.pending.clear()


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def _feature(name, longitude, latitude):
    return {
        "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
        "properties": {
            "name": name,
            "city": "Hyderabad",
            "osm_key": "railway",
            "osm_value": "station",
        },
    }


def test_geocoder_uses_shared_cache_configured_provider_and_hyderabad_scope(monkeypatch):
    session = _Session()
    requests = []
    features = [
        _feature("Ameerpet Metro Station", 78.4483, 17.4375),
        _feature("Outside Hyderabad", 79.0, 18.0),
    ]

    def fake_urlopen(request, timeout):
        requests.append((request.full_url, timeout))
        return _Response({"features": features})

    monkeypatch.setattr(geocoding.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("GEOCODING_BASE_URL", "https://machine-specific.example/api")
    monkeypatch.setenv("GEOCODING_TIMEOUT_SECONDS", "3.5")
    monkeypatch.setenv("GEOCODING_BBOX", "70,5,90,30")

    first = geocoding.geocode_location(
        "Ameerpet Metro Station", city_bias="London", limit=5, db=session
    )
    second = geocoding.geocode_location(
        "Ameerpet Metro Station", city_bias="Hyderabad", limit=5, db=session
    )

    assert first == second
    assert len(requests) == 2  # full and distinctive queries; second call uses shared cache
    assert all(urlparse(url).netloc == "photon.komoot.io" for url, _timeout in requests)
    assert all(timeout == 6.0 for _url, timeout in requests)
    assert all(parse_qs(urlparse(url).query)["bbox"] == ["78.2,17.2,78.65,17.6"] for url, _ in requests)
    assert [item["primary_name"] for item in first] == ["Ameerpet Metro Station"]
    assert geocoding.get_geocoding_bbox() == geocoding.DEFAULT_HYDERABAD_BBOX
    assert not geocoding.is_within_geocoding_boundary(18.0, 79.0)


def test_public_readiness_reports_shared_sources_without_database_credentials(monkeypatch):
    monkeypatch.setattr(
        setup_service,
        "_database_report",
        lambda _db: {
            "configured": True,
            "connected": True,
            "schema_ready": True,
            "error": None,
            "migrations": [
                "001_geocode_suggestion_cache",
                "002_rebuild_hotspots_from_shared_records",
            ],
            "counts": {
                "roads": 3,
                "traffic_records": 3,
                "accidents": 2,
                "accident_hotspots": 1,
                "traffic_zones": 1,
                "geocode_suggestion_cache": 4,
            },
        },
    )
    report = setup_service.build_readiness_report(object())

    assert report["status"] == "READY"
    assert report["checks"]["shared_data_present"] is True
    assert report["checks"]["suggestion_cache_ready"] is True
    assert report["checks"]["suggestion_cache_migration_applied"] is True
    assert report["checks"]["hotspot_data_migration_applied"] is True
    assert report["traffic_data"]["source"] == "shared database traffic_records"
    serialized = json.dumps(report)
    assert "password" not in serialized.lower()
    assert "postgresql://" not in serialized


def test_geocode_search_endpoint_cannot_override_hyderabad_city(monkeypatch):
    received = {}

    def fake_geocode_location(**kwargs):
        received.update(kwargs)
        return []

    monkeypatch.setattr(geocoding_router, "geocode_location", fake_geocode_location)

    geocoding_router.search_location(query="Koti", city="London", limit=5, db=object())

    assert received["city_bias"] == "Hyderabad"
    assert received["query"] == "Koti"


def test_frontend_geocode_endpoint_returns_same_shared_suggestions(monkeypatch):
    requests = []
    payload = {"features": [_feature("Ameerpet Metro Station", 78.4483, 17.4375)]}

    def fake_urlopen(request, timeout):
        requests.append(request.full_url)
        return _Response(payload)

    monkeypatch.setattr(geocoding.urllib.request, "urlopen", fake_urlopen)
    session = _Session()
    app.dependency_overrides[get_db] = lambda: session
    try:
        with TestClient(app) as client:
            first = client.get(
                "/api/geo/search",
                params={"query": "Ameerpet Metro Station", "city": "London", "limit": 5},
            )
            second = client.get(
                "/api/geo/search",
                params={"query": "Ameerpet Metro Station", "city": "London", "limit": 5},
            )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(requests) == 2  # provider called once for the phrase and core-name lookup
    assert all(
        geocoding.is_within_geocoding_boundary(item["latitude"], item["longitude"])
        for item in first.json()
    )


def test_hotspot_sync_uses_only_database_accident_counts(monkeypatch):
    zone_id = "zone-1"

    class _HotspotQuery:
        def __init__(self, is_prediction=False):
            self.is_prediction = is_prediction

        def join(self, *_args):
            return self

        def outerjoin(self, *_args):
            return self

        def group_by(self, *_args):
            return self

        def order_by(self, *_args):
            return self

        def filter(self, *_args):
            return self

        def all(self):
            return [(zone_id, "Test Zone", None, 2)]

        def scalar(self):
            return None

    class _HotspotSession:
        calls = 0

        def query(self, *_args):
            self.calls += 1
            return _HotspotQuery(is_prediction=self.calls > 1)

        def commit(self):
            pass

    captured = {}
    sentinel = SimpleNamespace()

    def fake_upsert(**kwargs):
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr("app.services.hotspot_service.upsert_accident_hotspot", fake_upsert)

    result = sync_empirical_hotspots(_HotspotSession())

    assert result == [sentinel]
    assert captured["accident_count"] == 2
    assert captured["risk_score"] == 45.0


def test_anomaly_inputs_require_request_or_shared_database_traffic():
    assert _request_or_database_value(None, 42, "vehicle_count") == 42
    assert _request_or_database_value(17, 42, "vehicle_count") == 17

    from fastapi import HTTPException
    import pytest

    with pytest.raises(HTTPException) as exc:
        _request_or_database_value(None, None, "vehicle_count")
    assert exc.value.status_code == 422
