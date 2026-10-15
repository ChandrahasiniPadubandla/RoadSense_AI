import uuid

import pytest
from fastapi.testclient import TestClient

from app import database as db_module
from app.database.connection import SessionLocal
from app.database.models import Road
from app.main import app
from app.schemas.accident_risk import AccidentRiskPredictionRequest
from app.services.accident_risk_service import AccidentRiskService


def _real_road_id() -> str:
    db = SessionLocal()
    try:
        road = db.query(Road).filter(Road.road_name.isnot(None)).first()
        if road is None:
            pytest.skip("No real roads are available in the database for validation.")
        return str(road.road_id)
    finally:
        db.close()


VALID_PAYLOAD = {"road_id": _real_road_id()}


def test_valid_accident_risk_prediction():
    request = AccidentRiskPredictionRequest(**VALID_PAYLOAD)
    db = SessionLocal()
    try:
        from app.services.accident_risk_feature_service import accident_risk_feature_service

        feature_payload = accident_risk_feature_service.build_feature_payload(db, request.road_id)
        result = AccidentRiskService().predict(feature_payload)
    finally:
        db.close()

    assert 0 <= result["accident_risk"] <= 100
    assert result["accident_risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def test_missing_required_field():
    with pytest.raises(Exception):
        AccidentRiskPredictionRequest()


def test_database_connection_uses_null_pool_for_supabase():
    assert db_module.connection.engine.pool.__class__.__name__ == "NullPool"


def test_model_loading_failure_raises_runtime_error(tmp_path):
    with pytest.raises(RuntimeError):
        AccidentRiskService(model_dir=tmp_path)


def test_prediction_response_structure():
    db = SessionLocal()
    try:
        from app.services.accident_risk_feature_service import accident_risk_feature_service

        feature_payload = accident_risk_feature_service.build_feature_payload(db, uuid.UUID(VALID_PAYLOAD["road_id"]))
        result = AccidentRiskService().predict(feature_payload)
    finally:
        db.close()

    assert set(result.keys()) >= {"success", "accident_risk", "accident_risk_level"}
    assert isinstance(result["success"], bool)
    assert 0 <= result["accident_risk"] <= 100


def test_router_endpoint_returns_prediction():
    from app.security import get_current_user

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: uuid.uuid4()

    with TestClient(app) as client:
        response = client.post(
            "/api/accident-predictions/predict",
            json=VALID_PAYLOAD,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["road_id"] == VALID_PAYLOAD["road_id"]
    assert 0 <= payload["accident_risk"] <= 100
    assert payload["accident_risk_level"]

    app.dependency_overrides.clear()


def test_road_search_uses_real_database_rows():
    from app.security import get_current_user

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: uuid.uuid4()

    with TestClient(app) as client:
        response = client.get("/api/roads?search=Abids")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert any(item["road_name"].lower().startswith("abids") for item in payload)

    app.dependency_overrides.clear()


def test_accident_prediction_geocodes_and_creates_searched_road_if_missing():
    from app.security import get_current_user

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: uuid.uuid4()

    # Generate a unique road query that does not exist in the DB
    test_searched_road = f"Kondapur Forest Track {uuid.uuid4().hex[:6]}"

    db = SessionLocal()
    try:
        # Verify it doesn't exist beforehand
        existing = db.query(Road).filter(Road.road_name == test_searched_road).first()
        assert existing is None

        with TestClient(app) as client:
            response = client.post(
                "/api/predictions/accidents/route",
                json={
                    "start_location": test_searched_road,
                    "end_location": "Kondapur Junction",
                }
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["road_name"] is not None
        assert payload["created_new_road"] is True
        assert 0 <= payload["risk_percentage"] <= 100
        assert payload["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

        # Verify that the searched road now exists in the database
        created_road = db.query(Road).filter(Road.road_id == uuid.UUID(payload["road_id"])).first()
        assert created_road is not None
        assert created_road.road_name == test_searched_road
        assert created_road.start_location is not None
        assert created_road.speed_limit is not None

        # Clean up test records from DB
        from app.database.models import AccidentPrediction, Alert
        db.query(Alert).filter(Alert.road_id == created_road.road_id).delete()
        db.query(AccidentPrediction).filter(AccidentPrediction.start_road_id == created_road.road_id).delete()
        db.delete(created_road)
        db.commit()
    finally:
        db.close()
        app.dependency_overrides.clear()

