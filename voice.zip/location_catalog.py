import re
import unicodedata
from difflib import SequenceMatcher


VALID_LOCATIONS = (
    "Abids",
    "Ameerpet",
    "Attapur",
    "Begumpet",
    "Banjara Hills",
    "Basheerbagh",
    "Bachupally",
    "Charminar",
    "Dilsukhnagar",
    "ECIL",
    "Financial District",
    "Gachibowli",
    "Himayat Nagar",
    "Hitech City",
    "Jubilee Hills",
    "Khairatabad",
    "Kompally",
    "Kondapur",
    "Kothapet",
    "Koti",
    "Kukatpally",
    "LB Nagar",
    "Lakdikapul",
    "Madhapur",
    "Malakpet",
    "Malkajgiri",
    "Manikonda",
    "Masab Tank",
    "Mehdipatnam",
    "Miyapur",
    "Nagole",
    "Nampally",
    "Nanakramguda",
    "Nacharam",
    "Punjagutta",
    "Paradise",
    "Raidurg",
    "Saidabad",
    "Secunderabad",
    "Shamshabad",
    "Somajiguda",
    "Suchitra",
    "Tarnaka",
    "Tolichowki",
    "Uppal",
    "Uppal Road",
)

_LOCATION_ALIASES = {
    "HITEC City": "Hitech City",
    "Hi Tech City": "Hitech City",
    "LB Nagar": "LB Nagar",
}


def normalize_location_text(text):
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def canonical_location(text):
    normalized = normalize_location_text(text)
    for location in VALID_LOCATIONS:
        if normalized == normalize_location_text(location):
            return location

    for alias, location in _LOCATION_ALIASES.items():
        if normalized == normalize_location_text(alias):
            return location

    return None


_NORMALIZED_LOCATIONS = tuple(
    (normalize_location_text(location), location)
    for location in VALID_LOCATIONS
)
_NORMALIZED_ALIASES = tuple(
    (normalize_location_text(alias), location)
    for alias, location in _LOCATION_ALIASES.items()
)


def find_location_mentions(text, ner_entities=()):
    words = list(re.finditer(r"\w+", text, flags=re.UNICODE))
    candidates = []

    for word_count in range(1, min(4, len(words)) + 1):
        for index in range(len(words) - word_count + 1):
            first_word = words[index]
            last_word = words[index + word_count - 1]
            phrase = normalize_location_text(
                text[first_word.start():last_word.end()]
            )
            if not phrase:
                continue

            for alias, location in _NORMALIZED_LOCATIONS + _NORMALIZED_ALIASES:
                exact = phrase == alias
                if not exact and (
                    len(alias) < 5 or abs(len(alias) - len(phrase)) > 1
                ):
                    continue
                if not exact and (
                    alias.startswith(phrase) or alias.endswith(phrase)
                ):
                    continue
                if not exact and SequenceMatcher(None, alias, phrase).ratio() < 0.86:
                    continue
                candidates.append(
                    (
                        first_word.start(),
                        last_word.end(),
                        location,
                        exact,
                        word_count,
                    )
                )

    for entity in ner_entities:
        location = canonical_location(entity.text)
        if location:
            candidates.append(
                (entity.start_char, entity.end_char, location, True, 0)
            )

    candidates.sort(
        key=lambda item: (
            item[0],
            item[3],
            item[4],
            item[1] - item[0],
        ),
        reverse=True,
    )

    mentions = []
    occupied = []
    for start, end, location, exact, word_count in candidates:
        if any(
            start < used_end and end > used_start
            for used_start, used_end in occupied
        ):
            continue
        mentions.append((start, end, location, exact))
        occupied.append((start, end))

    mentions.sort(key=lambda item: item[0])
    return mentions


_START_CUE = re.compile(
    r"\b(?:from|starting\s+at|start(?:ing)?\s+from|"
    r"start(?:ing)?\s+at|start(?:ing)?\s+point(?:\s+is)?|"
    r"start(?:ing)?\s+location(?:\s+is)?|start\s+is|"
    r"origin(?:\s+is)?|begin(?:ning)?\s+at|leaving|near|located\s+at|"
    r"currently\s+(?:at|in)|i\s+am\s+(?:in|at)|"
    r"i(?:'m| am)\s+starting\s+in)\s*[:,-]?\s*$",
    re.IGNORECASE,
)
_END_CUE = re.compile(
    r"\b(?:to|reach|reaching|destination(?:\s+is)?|"
    r"heading\s+to|heading\s+for|ending\s+at|end\s+at|"
    r"end(?:\s+point|\s+location)?(?:\s+is)?|final\s+stop(?:\s+is)?)"
    r"\s*[:,-]?\s*$",
    re.IGNORECASE,
)


def extract_route_locations(text, ner_entities=()):
    mentions = find_location_mentions(text, ner_entities)
    if len(mentions) < 2:
        return None, None

    start = None
    end = None
    for mention in mentions:
        before = text[max(0, mention[0] - 45):mention[0]]
        if _START_CUE.search(before):
            start = mention[2]
        if _END_CUE.search(before):
            end = mention[2]

    if start and end:
        return start, end

    ner_start = None
    ner_end = None
    for entity in ner_entities:
        location = canonical_location(entity.text)
        if not location:
            continue
        if entity.label_ == "START_LOCATION":
            ner_start = location
        elif entity.label_ == "END_LOCATION":
            ner_end = location

    if ner_start and ner_end and ner_start != ner_end:
        if start and start != ner_end:
            return start, ner_end
        if end and end != ner_start:
            return ner_start, end
        return ner_start, ner_end

    first, second = mentions[:2]
    between = text[first[1]:second[0]]
    before_first = text[max(0, first[0] - 45):first[0]]

    # Handle destination-first wording such as "to Nagole from Uppal".
    if re.search(r"\bfrom\b", between, re.IGNORECASE) and re.search(
        r"\bto\b", before_first, re.IGNORECASE
    ):
        return second[2], first[2]

    return first[2], second[2]
