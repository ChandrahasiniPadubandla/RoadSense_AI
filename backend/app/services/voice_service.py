import os
import re
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger("Metrivon.voice")

# Resolve model path dynamically relative to repository root
REPO_ROOT = Path(__file__).resolve().parents[3]

# The trained spaCy location-NER model ships inside this repository, so every
# clone uses the exact same artifact (no download and no credentials required).
# It was originally committed under `voice_extractor/location_ner_model` and is
# now committed under `voice.zip/location_ner_model`. Both are checked so that a
# fresh clone and an older local checkout resolve to the same model instead of
# silently falling back to the regex extractor.
_MODEL_DIR_CANDIDATES = (
    REPO_ROOT / "voice.zip" / "location_ner_model",
    REPO_ROOT / "voice_extractor" / "location_ner_model",
)


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
                "Run the backend from a normal clone so the committed "
                "voice.zip/location_ner_model is available.",
                ", ".join(str(candidate) for candidate in _MODEL_DIR_CANDIDATES),
            )
            return None

        try:
            import spacy
            logger.info("Loading location NER model from: %s", model_path)
            _nlp = spacy.load(str(model_path))
            logger.info("Location NER model loaded successfully.")
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
        # "traffic to Nagole" has a destination but no origin.
        if not start or start.lower() in _GENERIC_QUERY_WORDS:
            return None, m.group(2).strip()
        return start, m.group(2).strip()

    return None, None


def extract_route_from_text(raw_text: str) -> Dict[str, Any]:
    """
    Main extraction function:
    1. Cleans the spoken transcript.
    2. Runs the trained spaCy location NER model.
    3. If both start and end locations are not found, falls back to pattern extraction.
    4. Cleans trailing punctuation or artifacts.
    """
    if not raw_text or not raw_text.strip():
        return {
            "start_location": None,
            "end_location": None,
            "raw_text": raw_text or "",
            "cleaned_text": "",
            "method": "none",
            "model_loaded": get_nlp_model() is not None,
            "success": False
        }

    cleaned = clean_voice_text(raw_text)

    # 1. Try NER
    start_loc, end_loc = extract_locations_ner(cleaned)
    method = "ner"

    # If raw_text gave different results or didn't match, also test raw text with NER
    if not start_loc or not end_loc:
        alt_start, alt_end = extract_locations_ner(raw_text)
        start_loc = start_loc or alt_start
        end_loc = end_loc or alt_end

    # 2. Fallback to patterns if either is missing
    if not start_loc or not end_loc:
        pat_start, pat_end = extract_locations_pattern(cleaned)
        if not pat_start or not pat_end:
            pat_start, pat_end = extract_locations_pattern(raw_text)

        if not start_loc and pat_start:
            start_loc = pat_start
            method = "pattern" if not end_loc else "hybrid"
        if not end_loc and pat_end:
            end_loc = pat_end
            method = "pattern" if not start_loc else "hybrid"

    # Post-clean extracted locations
    def sanitize(loc: Optional[str]) -> Optional[str]:
        if not loc:
            return None
        # Remove trailing question marks, periods, commas
        cleaned_loc = re.sub(r"[?!.,;]+$", "", loc).strip()
        # Remove trailing time / politeness phrases ("right now", "in 30 minutes"...)
        previous = None
        while previous != cleaned_loc:
            previous = cleaned_loc
            cleaned_loc = _TRAILING_FILLER.sub("", cleaned_loc)
            cleaned_loc = re.sub(r"[?!.,;]+$", "", cleaned_loc).strip()
        # Remove leading "the "
        cleaned_loc = re.sub(r"^the\s+", "", cleaned_loc, flags=re.IGNORECASE).strip()
        return cleaned_loc if cleaned_loc else None

    start_loc = sanitize(start_loc)
    end_loc = sanitize(end_loc)

    success = bool(start_loc and end_loc)

    return {
        "start_location": start_loc,
        "end_location": end_loc,
        "raw_text": raw_text,
        "cleaned_text": cleaned,
        "method": method if success else ("partial" if (start_loc or end_loc) else "none"),
        "model_loaded": get_nlp_model() is not None,
        "success": success
    }
