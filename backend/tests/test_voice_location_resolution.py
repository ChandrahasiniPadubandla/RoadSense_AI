import hashlib

from app.routers import voice as voice_router
from app.schemas.voice import VoiceRouteExtractRequest
from app.services import voice_service
from app.services.voice_service import (
    clean_voice_text,
    extract_route_from_text,
    get_nlp_model,
    resolve_model_path,
)

# The location NER model is a committed artifact, so its checksum is part of the
# reproducibility contract. Update this constant (and backend/README.md) only
# when the model is intentionally replaced.
EXPECTED_MODEL_SHA256 = "ee1db62316747d3965a434daab93b09d4b7e2c20d776142e7260ebcf2490c751"
EXPECTED_LABELS = {"START_LOCATION", "END_LOCATION"}


def test_model_ships_with_the_repository():
    """A fresh clone must contain the model; no machine-specific path allowed."""
    path = resolve_model_path()
    assert path is not None, "location NER model missing from the repository"
    assert (path / "meta.json").is_file()
    assert path.name == "location_ner_model"
    assert path.parent.name in {"voice.zip", "voice_extractor"}


def test_committed_model_matches_recorded_checksum():
    path = resolve_model_path()
    assert path is not None
    digest = hashlib.sha256((path / "ner" / "model").read_bytes()).hexdigest()
    assert digest == EXPECTED_MODEL_SHA256, "committed NER model changed unexpectedly"


def test_model_loads_with_expected_labels():
    nlp = get_nlp_model()
    assert nlp is not None, "spaCy could not load the committed NER model"
    assert set(nlp.get_pipe("ner").labels) == EXPECTED_LABELS


def test_extraction_uses_the_model_not_the_regex_fallback():
    get_nlp_model()  # ensure the lazy model is loaded first
    result = extract_route_from_text("from Uppal to Nagole")
    assert result["model_loaded"] is True
    assert result["start_location"]
    assert result["end_location"]
    assert result["method"] in {"ner", "hybrid"}


def test_same_input_gives_identical_results():
    get_nlp_model()
    first = extract_route_from_text("from Kondapur to Nagole right now")
    second = extract_route_from_text("from Kondapur to Nagole right now")
    assert first == second


def test_clean_voice_text_strips_conversational_prefix():
    assert clean_voice_text("What is the traffic from Uppal to Nagole?") == "from Uppal to Nagole?"


def test_status_endpoint_reports_loaded_model_and_path():
    body = voice_router.get_voice_status()
    assert body["model_loaded"] is True
    assert body["model_path"]
    assert body["model_path"].endswith("location_ner_model")


def test_voice_endpoint_returns_model_backed_result():
    response = voice_router.extract_route_from_voice(
        VoiceRouteExtractRequest(text="from Uppal to Nagole")
    )
    body = response.model_dump()
    assert body["success"] is True
    assert body["model_loaded"] is True
    assert body["start_location"]
    assert body["end_location"]


def test_repo_root_points_at_a_real_checkout():
    assert (voice_service.REPO_ROOT / "backend").is_dir()
