import importlib.util
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from rapidfuzz.fuzz import ratio

from app.services.geocoding import GeocodingError, search_geocoding_candidates

LOCATION_CATALOG_PATH = Path(__file__).resolve().parents[3] / "voice.zip" / "location_catalog.py"
_catalog_spec = importlib.util.spec_from_file_location(
    "roadsense_location_catalog",
    LOCATION_CATALOG_PATH,
)
if _catalog_spec is None or _catalog_spec.loader is None:
    raise ImportError(f"Could not load location catalog at {LOCATION_CATALOG_PATH}")
_location_catalog = importlib.util.module_from_spec(_catalog_spec)
_catalog_spec.loader.exec_module(_location_catalog)

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


def _normalize_location(text: str) -> str:
    return _location_catalog.normalize_location_text(text)


def _compact_location(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _normalize_location(text))


def _sanitize_fragment(fragment: Optional[str]) -> Optional[str]:
    if not fragment:
        return None
    cleaned = fragment.strip()
    previous = None
    while previous != cleaned:
        previous = cleaned
        cleaned = _TRAILING_FILLER.sub("", cleaned)
        cleaned = re.sub(
            r"(?:\s+\b(?:to|from|and|at)\b)+\s*$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"^[\s,.:;?!-]+|[\s,.:;?!-]+$", "", cleaned)
    cleaned = re.sub(r"^(?:the|a|an)\s+", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip() or None


def extract_location_fragments(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse route cues into origin/destination fragments without naming places."""
    cleaned = clean_voice_text(text)
    patterns = (
        (r"\breach\s+(.+?)\s+from\s+(.+)$", 2, 1),
        (r"\bgo\s+to\s+(.+?)\s+from\s+(.+)$", 2, 1),
        (r"\b(?:to|destination(?:\s+is)?)\s+(.+?)\s+from\s+(.+)$", 2, 1),
        (r"\bbetween\s+(.+?)\s+and\s*(.*)$", 1, 2),
        (r"\bfrom\s+(.+?)\s+to\s*(.*)$", 1, 2),
        (r"^(.+?)\s+to\s*(.*)$", 1, 2),
    )
    for pattern, start_group, end_group in patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            start = _sanitize_fragment(match.group(start_group))
            end = _sanitize_fragment(match.group(end_group))
            if start and end:
                return start, end
            # Destination-first commands use "to X from Y"; the first two
            # patterns already normalize their order above.
            return start, end

    origin = re.search(r"\bfrom\s+(.+)$", cleaned, re.IGNORECASE)
    if origin:
        return _sanitize_fragment(origin.group(1)), None
    destination = re.search(r"\b(?:to|destination(?:\s+is)?)\s+(.+)$", cleaned, re.IGNORECASE)
    if destination:
        return None, _sanitize_fragment(destination.group(1))
    return None, None


def _geocode_place(query: str) -> List[Dict[str, Any]]:
    """Default resolver: the project's existing geocoding provider (Photon)."""
    return search_geocoding_candidates(query)


def _candidate_name(candidate: Dict[str, Any]) -> str:
    return (
        candidate.get("display_name")
        or candidate.get("primary_name")
        or candidate.get("name")
        or ""
    ).strip()


def _candidate_search_text(candidate: Dict[str, Any]) -> str:
    parts = [
        candidate.get("name") or "",
        candidate.get("primary_name") or "",
        candidate.get("display_name") or "",
        candidate.get("secondary_name") or "",
    ]
    return " ".join(part for part in parts if part)


def _candidate_covers_fragment(
    fragment_normalized: str,
    fragment_compact: str,
    candidate: Dict[str, Any],
) -> bool:
    """True only when the geocoded place represents the *complete* spoken phrase.

    This is what prevents silently substituting a shorter overlapping place
    (e.g. resolving "Uppal Metro Station" to just "Uppal").
    """
    candidate_normalized = _normalize_location(_candidate_search_text(candidate))
    if not candidate_normalized:
        return False

    fragment_tokens = fragment_normalized.split()
    candidate_tokens = set(candidate_normalized.split())
    if fragment_tokens and all(token in candidate_tokens for token in fragment_tokens):
        return True

    compact_candidate = _compact_location(_candidate_search_text(candidate))
    return bool(fragment_compact) and fragment_compact in compact_candidate


def _to_location_match(
    candidate: Dict[str, Any], fragment_normalized: str
) -> Dict[str, Any]:
    name = _candidate_name(candidate) or fragment_normalized
    candidate_normalized = _normalize_location(_candidate_search_text(candidate))
    score = ratio(fragment_normalized, candidate_normalized) / 100 if candidate_normalized else 0.0
    return {
        "name": name,
        "source": "geocoding",
        "score": round(max(0.0, min(score, 1.0)), 3),
    }


def _resolve_location(
    fragment: Optional[str], geocoder: Callable[[str], List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """Resolve one complete spoken phrase to a real place via the geocoding API."""
    if not fragment:
        return {"status": "empty", "location": None, "matches": [], "coordinates": None, "message": None}

    try:
        candidates = geocoder(fragment) or []
    except GeocodingError as err:
        return {"status": err.status, "location": None, "matches": [], "coordinates": None, "message": err.message}
    except (TimeoutError, OSError):
        return {
            "status": "error",
            "location": None,
            "matches": [],
            "coordinates": None,
            "message": "The location service is unavailable. Please try again.",
        }

    if not candidates:
        return {"status": "not_found", "location": None, "matches": [], "coordinates": None, "message": None}

    fragment_normalized = _normalize_location(fragment)
    fragment_compact = _compact_location(fragment)

    ranked = sorted(
        candidates,
        key=lambda candidate: (-ratio(fragment_normalized, _normalize_location(_candidate_search_text(candidate))), _candidate_name(candidate).casefold()),
    )
    suggestions = [
        _to_location_match(candidate, fragment_normalized)
        for candidate in ranked[:5]
        if _candidate_name(candidate)
    ]

    covering = [
        candidate
        for candidate in candidates
        if _candidate_covers_fragment(fragment_normalized, fragment_compact, candidate)
    ]

    if covering:
        best = max(
            covering,
            key=lambda candidate: (
                ratio(fragment_normalized, _normalize_location(_candidate_search_text(candidate))),
                candidate.get("importance") or 0.0,
            ),
        )
        best_match = _to_location_match(best, fragment_normalized)
        best_match["score"] = max(best_match["score"], 0.99)
        ordered_matches = [best_match] + [
            suggestion for suggestion in suggestions if suggestion["name"] != best_match["name"]
        ]
        return {
            "status": "matched",
            "location": fragment,
            "matches": ordered_matches[:5],
            "coordinates": {
                "latitude": best.get("latitude"),
                "longitude": best.get("longitude"),
            },
            "message": None,
        }

    # Candidates exist but none represents the full phrase: never shorten or swap
    # to a different place — surface them as suggestions for the user to choose.
    return {
        "status": "ambiguous",
        "location": None,
        "matches": suggestions,
        "coordinates": None,
        "message": "Several places are close matches. Choose a suggestion to confirm the exact location.",
    }


_MESSAGE_PRIORITY = ("rate_limited", "timeout", "error", "ambiguous", "not_found")


def _route_message(start_result: Dict[str, Any], end_result: Dict[str, Any], success: bool) -> Optional[str]:
    statuses = {start_result["status"], end_result["status"]}
    for status in _MESSAGE_PRIORITY:
        if status in statuses:
            failing = start_result if start_result["status"] == status else end_result
            if status in ("rate_limited", "timeout", "error") and failing["message"]:
                return failing["message"]
            if status == "ambiguous":
                return "Several places are close matches. Choose a suggestion for the exact location."
            if status == "not_found":
                return "No real place matched one or more spoken locations. Please repeat the location names."
    if not success:
        return "Say an origin and destination, for example: from one location to another."
    return None


def extract_route_from_text(
    raw_text: str,
    db: Any = None,
    geocoder: Optional[Callable[[str], List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """Resolve a spoken route by geocoding each complete location phrase.

    Speech recognition and route parsing are unchanged; only the resolution of
    the parsed phrases now goes through the backend geocoding provider. The full
    recognized place name is returned verbatim (never shortened).
    """
    cleaned = clean_voice_text(raw_text or "")
    start_fragment, end_fragment = extract_location_fragments(raw_text or "")
    resolve = geocoder or _geocode_place

    start_result = _resolve_location(start_fragment, resolve)
    end_result = _resolve_location(end_fragment, resolve)
    start_location = start_result["location"]
    end_location = end_result["location"]
    success = bool(start_location and end_location)

    method = "geocoding" if success else ("partial" if (start_location or end_location) else "none")

    return {
        "success": success,
        "start_location": start_location,
        "end_location": end_location,
        "start_status": start_result["status"],
        "end_status": end_result["status"],
        "start_matches": start_result["matches"],
        "end_matches": end_result["matches"],
        "start_coordinates": start_result["coordinates"],
        "end_coordinates": end_result["coordinates"],
        "raw_text": raw_text or "",
        "cleaned_text": cleaned,
        "method": method,
        "resolver_ready": True,
        "model_loaded": False,
        "message": _route_message(start_result, end_result, success),
    }
