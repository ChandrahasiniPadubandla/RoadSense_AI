import os
import re
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger("Metrivon.voice")

# Resolve model path dynamically relative to repository root
REPO_ROOT = Path(__file__).resolve().parents[3]

# The trained spaCy location-NER model ships inside `voice/location_ner_model`.
# Fallbacks are maintained for backward compatibility.
_MODEL_DIR_CANDIDATES = (
    REPO_ROOT / "voice" / "location_ner_model",
    REPO_ROOT / "voice.zip" / "location_ner_model",
    REPO_ROOT / "voice_extractor" / "location_ner_model",
)

# Dynamically link voice catalog module from voice directory
_VOICE_DIR = REPO_ROOT / "voice"
if _VOICE_DIR.is_dir() and str(_VOICE_DIR) not in sys.path:
    sys.path.insert(0, str(_VOICE_DIR))

try:
    from location_catalog import (
        VALID_LOCATIONS,
        _LOCATION_ALIASES,
        canonical_location,
        extract_route_locations as catalog_extract_route,
        find_location_mentions,
    )
except ImportError:
    VALID_LOCATIONS = ()
    _LOCATION_ALIASES = {}
    canonical_location = lambda x: None
    catalog_extract_route = lambda text, ents=(): (None, None)
    find_location_mentions = lambda text, ents=(): []


def resolve_model_path() -> Optional[Path]:
    """Return the directory holding the location-NER model, or ``None``.

    ``VOICE_NER_MODEL_PATH`` may point at an explicit model directory for
    advanced setups; otherwise the in-repo copy is used.
    """
    override = (os.getenv("VOICE_NER_MODEL_PATH") or "").strip()
    candidates = ([Path(override)] if override else []) + list(_MODEL_DIR_CANDIDATES)
    for candidate in candidates:
        if (candidate / "meta.json").is_file():
            return candidate
    return None


# Resolved once at import time; used by the loader and reported by /voice/status.
MODEL_PATH: Optional[Path] = resolve_model_path()

# Lazy-loaded spaCy model
_nlp = None
_model_load_attempted = False

# Words that start a spoken query but are never a place name.
_GENERIC_QUERY_WORDS = {
    "traffic", "accident", "route", "risk", "check", "show",
    "traffic status", "traffic congestion", "accident risk",
}

# Generic infrastructure / facility suffixes that should never be standalone locations.
_GENERIC_FRAGMENT_WORDS = {
    "station", "metro station", "metro", "bus station", "bus stand",
    "bus stop", "stop", "road", "street", "lane", "colony",
    "junction", "circle", "x roads", "x road", "building", "hospital",
    "mall", "gate", "phase", "stand", "depot", "point", "hub", "terminal",
}


def is_generic_fragment(text: Optional[str]) -> bool:
    """True if text is None, empty, or just a generic facility word like 'station'."""
    if not text:
        return True
    cleaned_lower = text.strip().lower()
    return cleaned_lower in _GENERIC_FRAGMENT_WORDS or len(cleaned_lower) <= 2

# Trailing time / politeness phrases that people tack onto a spoken query
# ("... to Kondapur right now", "... to Nagole in 30 minutes"). They are not
# part of the destination and would make the location lookup fail.
_TRAILING_FILLER = re.compile(
    r"\s+(?:"
    r"right\s+now|now|today|tonight|tomorrow|please|currently|at\s+the\s+moment"
    r"|(?:in|after|within|for)\s+(?:the\s+next\s+)?(?:an?|\d+|one|two|three|five|ten|fifteen|twenty|thirty|forty[- ]five|sixty)\s*(?:min(?:ute)?s?|hours?|hrs?)"
    r"|at\s+\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?"
    r"|(?:this|in\s+the)\s+(?:morning|afternoon|evening|night)"
    r"|during\s+(?:the\s+)?(?:morning|evening|peak)(?:\s+hours?)?"
    r")\s*$",
    re.IGNORECASE,
)


def get_nlp_model():
    """Lazily load the spaCy location NER model."""
    global _nlp, _model_load_attempted
    if _nlp is not None:
        return _nlp

    if not _model_load_attempted:
        _model_load_attempted = True
        model_path = MODEL_PATH or resolve_model_path()
        if model_path is None:
            logger.error(
                "Location NER model not found. Looked in: %s. "
                "Ensure voice/location_ner_model is present.",
                ", ".join(str(candidate) for candidate in _MODEL_DIR_CANDIDATES),
            )
            return None

        try:
            import spacy
            logger.info("Loading location NER model from: %s", model_path)
            _nlp = spacy.load(str(model_path))
            logger.info("Location NER model loaded successfully from %s.", model_path)
        except Exception as e:
            logger.error("Failed to load spaCy location NER model from %s: %s", model_path, e)
            _nlp = None

    return _nlp


def clean_voice_text(text: str) -> str:
    """Strip common voice prefixes/fillers while preserving location names."""
    if not text:
        return ""
    cleaned = text.strip()
    # Remove leading common conversational queries
    patterns_to_remove = [
        r"^(please\s+)?(what\s+is\s+the\s+)?(traffic\s+status|traffic\s+congestion|traffic|accident\s+risk|risk|condition)\s+(between|from|for|on)\s+",
        r"^(please\s+)?(check|predict|show|get|tell\s+me)\s+(the\s+)?(traffic|accident\s+risk|route|congestion)\s+(between|from|for|on|to)\s+",
        r"^(please\s+)?(can\s+you\s+)?(check|predict|find)\s+",
        r"^(navigate|take\s+me)\s+",
    ]
    for pat in patterns_to_remove:
        match = re.search(pat, cleaned, re.IGNORECASE)
        if match:
            # Keep "from" or "between" if present at the end of the match
            matched_str = match.group(0).lower()
            if "between" in matched_str:
                cleaned = "between " + cleaned[match.end():]
            elif "from" in matched_str:
                cleaned = "from " + cleaned[match.end():]
            else:
                cleaned = cleaned[match.end():]
            break

    return cleaned.strip()


def format_location_name(text: str, location: Optional[str]) -> Optional[str]:
    """Include the metro-station suffix when the transcript says 'metro'."""
    if not location:
        return location
    if re.search(r"\b" + re.escape(location) + r"\s+metro(?:\s+station)?\b", text, re.IGNORECASE):
        if "metro" not in location.lower():
            return f"{location} Metro Station"
    return location


def extract_locations_ner(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract start and end location using the trained spaCy NER model."""
    nlp = get_nlp_model()
    if not nlp:
        return None, None

    try:
        doc = nlp(text)
        start_location = None
        end_location = None

        for ent in doc.ents:
            if ent.label_ == "START_LOCATION" and not start_location:
                start_location = ent.text.strip()
            elif ent.label_ == "END_LOCATION" and not end_location:
                end_location = ent.text.strip()

        return start_location, end_location
    except Exception as e:
        logger.error("Error running spaCy NER inference: %s", e)
        return None, None


def extract_locations_pattern(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Robust fallback rule-based pattern extractor for spoken route queries."""
    cleaned = text.strip()

    # Pattern: from X to Y
    m = re.search(r"\bfrom\s+(.+?)\s+to\s+(.+)$", cleaned, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Pattern: between X and Y
    m = re.search(r"\bbetween\s+(.+?)\s+and\s+(.+)$", cleaned, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Pattern: reach Y from X
    m = re.search(r"\breach\s+(.+?)\s+from\s+(.+)$", cleaned, re.IGNORECASE)
    if m:
        return m.group(2).strip(), m.group(1).strip()

    # Pattern: go to Y from X
    m = re.search(r"\bgo\s+to\s+(.+?)\s+from\s+(.+)$", cleaned, re.IGNORECASE)
    if m:
        return m.group(2).strip(), m.group(1).strip()

    # Pattern: X to Y (e.g. "Uppal to Nagole")
    m = re.search(r"^(.+?)\s+to\s+(.+)$", cleaned, re.IGNORECASE)
    if m:
        start = m.group(1).strip()
        # Ensure start does not start with generic commands
        start = re.sub(r"^(traffic|accident|route|risk|check|show)\s+", "", start, flags=re.IGNORECASE).strip()
        if not start or start.lower() in _GENERIC_QUERY_WORDS:
            return None, m.group(2).strip()
        return start, m.group(2).strip()

    return None, None


def sanitize_location(loc: Optional[str]) -> Optional[str]:
    """Clean trailing punctuation, politeness fillers, and leading articles."""
    if not loc:
        return None
    cleaned_loc = re.sub(r"[?!.,;]+$", "", loc).strip()
    previous = None
    while previous != cleaned_loc:
        previous = cleaned_loc
        cleaned_loc = _TRAILING_FILLER.sub("", cleaned_loc)
        cleaned_loc = re.sub(r"[?!.,;]+$", "", cleaned_loc).strip()
    cleaned_loc = re.sub(r"^the\s+", "", cleaned_loc, flags=re.IGNORECASE).strip()
    return cleaned_loc if cleaned_loc else None


def extract_route_from_text(
    raw_text: str,
    db: Optional[Any] = None,
    resolve_osm: bool = True
) -> Dict[str, Any]:
    """
    Main extraction & location resolution pipeline:
    1. Cleans the spoken transcript.
    2. Runs the trained spaCy location NER model + voice/location_catalog.
    3. Runs linguistic regex cue fallback for arbitrary / un-cataloged location names.
    4. Connects to OpenStreetMap (OSM) / Photon geocoding engine to validate
       and resolve exact geographic coordinates & address metadata.
    """
    if not raw_text or not raw_text.strip():
        return {
            "start_location": None,
            "end_location": None,
            "start_latitude": None,
            "start_longitude": None,
            "end_latitude": None,
            "end_longitude": None,
            "start_formatted": None,
            "end_formatted": None,
            "start_status": "empty",
            "end_status": "empty",
            "osm_resolved": False,
            "raw_text": raw_text or "",
            "cleaned_text": "",
            "method": "none",
            "model_loaded": get_nlp_model() is not None,
            "success": False
        }

    cleaned = clean_voice_text(raw_text)
    nlp = get_nlp_model()
    start_loc = None
    end_loc = None
    raw_extracted_start = None
    raw_extracted_end = None
    method = "none"

    # 1. Catalog-assisted extraction using trained NER model ents
    if nlp is not None:
        try:
            doc = nlp(cleaned)
            cat_start, cat_end = catalog_extract_route(cleaned, doc.ents)
            if not cat_start and not cat_end and raw_text != cleaned:
                doc_raw = nlp(raw_text)
                cat_start, cat_end = catalog_extract_route(raw_text, doc_raw.ents)

            if cat_start and cat_end:
                raw_extracted_start = cat_start
                raw_extracted_end = cat_end
                start_loc = format_location_name(cleaned, cat_start)
                end_loc = format_location_name(cleaned, cat_end)
                method = "ner"
        except Exception as err:
            logger.warning("Catalog-assisted route extraction skipped: %s", err)

    # 2. Direct NER extraction if catalog didn't catch both
    if not start_loc or not end_loc:
        ner_start, ner_end = extract_locations_ner(cleaned)
        if not ner_start or not ner_end:
            alt_s, alt_e = extract_locations_ner(raw_text)
            ner_start = ner_start or alt_s
            ner_end = ner_end or alt_e

        # Reject generic suffixes like "station", "stop", "road"
        if is_generic_fragment(ner_start):
            ner_start = None
        if is_generic_fragment(ner_end):
            ner_end = None

        if ner_start and not start_loc:
            raw_extracted_start = ner_start
            start_loc = ner_start
            method = "ner" if not end_loc else "hybrid"
        if ner_end and not end_loc:
            raw_extracted_end = ner_end
            end_loc = ner_end
            method = "ner" if not start_loc else "hybrid"

    # 3. Linguistic grammar pattern extraction (captures full compound landmarks like "Moosapet metro station")
    pat_start, pat_end = extract_locations_pattern(cleaned)
    if not pat_start or not pat_end:
        pat_start, pat_end = extract_locations_pattern(raw_text)

    # If pattern found a complete landmark phrase, use it to upgrade fragments or fill missing
    if pat_start and not is_generic_fragment(pat_start):
        if not start_loc or is_generic_fragment(start_loc) or (start_loc.lower() in pat_start.lower() and len(pat_start) > len(start_loc)):
            raw_extracted_start = pat_start
            start_loc = pat_start
            method = "pattern" if not end_loc else "hybrid"

    if pat_end and not is_generic_fragment(pat_end):
        if not end_loc or is_generic_fragment(end_loc) or (end_loc.lower() in pat_end.lower() and len(pat_end) > len(end_loc)):
            raw_extracted_end = pat_end
            end_loc = pat_end
            method = "pattern" if not start_loc else "hybrid"

    # 4. Clean and normalize
    start_loc = sanitize_location(start_loc)
    end_loc = sanitize_location(end_loc)
    if not raw_extracted_start and start_loc:
        raw_extracted_start = start_loc
    if not raw_extracted_end and end_loc:
        raw_extracted_end = end_loc

    # Canonicalize known aliases from catalog
    if start_loc:
        canon_s = canonical_location(start_loc)
        if canon_s:
            start_loc = format_location_name(cleaned, canon_s)
    if end_loc:
        canon_e = canonical_location(end_loc)
        if canon_e:
            end_loc = format_location_name(cleaned, canon_e)

    # 5. OpenStreetMap (OSM) / Geocoding resolution & validation
    start_lat = None
    start_lng = None
    end_lat = None
    end_lng = None
    start_formatted = None
    end_formatted = None
    osm_resolved = False

    if resolve_osm and (start_loc or end_loc):
        try:
            from app.services.geocoding import geocode_location

            if start_loc:
                res_s = geocode_location(start_loc, db=db)
                if res_s and len(res_s) > 0:
                    start_lat = res_s[0]["latitude"]
                    start_lng = res_s[0]["longitude"]
                    start_formatted = res_s[0].get("display_name") or res_s[0].get("primary_name")
                    # If start_loc is already a valid canonical location (e.g. "Uppal"), keep it!
                    # Only auto-correct if start_loc was not already canonical (e.g. speech typos)
                    if not canonical_location(start_loc):
                        osm_primary = res_s[0].get("primary_name")
                        if osm_primary:
                            canon = canonical_location(osm_primary)
                            start_loc = canon if canon else osm_primary

            if end_loc:
                res_e = geocode_location(end_loc, db=db)
                if res_e and len(res_e) > 0:
                    end_lat = res_e[0]["latitude"]
                    end_lng = res_e[0]["longitude"]
                    end_formatted = res_e[0].get("display_name") or res_e[0].get("primary_name")
                    # If end_loc is already a valid canonical location (e.g. "Nagole"), keep it!
                    # Only auto-correct if end_loc was not already canonical
                    if not canonical_location(end_loc):
                        osm_primary = res_e[0].get("primary_name")
                        if osm_primary:
                            canon = canonical_location(osm_primary)
                            end_loc = canon if canon else osm_primary

            if (start_lat is not None and start_lng is not None) and (end_lat is not None and end_lng is not None):
                osm_resolved = True
        except Exception as geocoding_err:
            logger.warning("Voice OSM geocoding resolution skipped: %s", geocoding_err)

    # Validate identical locations
    is_identical = bool(
        start_loc and end_loc and start_loc.strip().lower() == end_loc.strip().lower()
    )
    success = bool(start_loc and end_loc and not is_identical)

    msg = None
    if is_identical:
        msg = f"Start location and destination cannot be identical ('{start_loc}')."
    elif not success:
        if not start_loc and not end_loc:
            msg = "Could not identify start and end locations. Try phrasing as 'From [Origin] to [Destination]'."
        elif not start_loc:
            msg = f"Found destination '{end_loc}', but could not detect start location."
        elif not end_loc:
            msg = f"Found origin '{start_loc}', but could not detect destination."

    start_status = "resolved" if start_loc else "empty"
    end_status = "resolved" if end_loc else "empty"

    return {
        "start_location": start_loc,
        "end_location": end_loc,
        "extracted_start_words": raw_extracted_start,
        "extracted_end_words": raw_extracted_end,
        "search_query_origin": start_loc or raw_extracted_start,
        "search_query_destination": end_loc or raw_extracted_end,
        "start_latitude": start_lat,
        "start_longitude": start_lng,
        "end_latitude": end_lat,
        "end_longitude": end_lng,
        "start_formatted": start_formatted,
        "end_formatted": end_formatted,
        "start_status": start_status,
        "end_status": end_status,
        "osm_resolved": osm_resolved,
        "raw_text": raw_text,
        "cleaned_text": cleaned,
        "method": method if success else ("partial" if (start_loc or end_loc) else "none"),
        "model_loaded": nlp is not None,
        "success": success,
        "message": msg,
    }
