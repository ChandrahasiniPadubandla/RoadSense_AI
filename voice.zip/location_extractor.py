import spacy
import re


# =========================================================
# LOAD TRAINED MODEL
# =========================================================

MODEL_PATH = "location_ner_model"

nlp = spacy.load(MODEL_PATH)


# =========================================================
# NER LOCATION EXTRACTION
# =========================================================

def extract_locations(text):

    doc = nlp(text)

    start_location = None
    end_location = None

    for ent in doc.ents:

        if ent.label_ == "START_LOCATION":

            start_location = ent.text.strip()

        elif ent.label_ == "END_LOCATION":

            end_location = ent.text.strip()

    return start_location, end_location


# =========================================================
# FALLBACK EXTRACTION
# =========================================================

def extract_using_pattern(text):

    text = text.strip()

    # Example:
    # from Uppal to Nagole

    match = re.search(
        r"from\s+(.+?)\s+to\s+(.+)",
        text,
        re.IGNORECASE
    )

    if match:

        start_location = match.group(1).strip()
        end_location = match.group(2).strip()

        return start_location, end_location


    # Example:
    # reach Nagole from Uppal

    match = re.search(
        r"reach\s+(.+?)\s+from\s+(.+)",
        text,
        re.IGNORECASE
    )

    if match:

        end_location = match.group(1).strip()
        start_location = match.group(2).strip()

        return start_location, end_location


    # Example:
    # go to Nagole from Uppal

    match = re.search(
        r"go\s+to\s+(.+?)\s+from\s+(.+)",
        text,
        re.IGNORECASE
    )

    if match:

        end_location = match.group(1).strip()
        start_location = match.group(2).strip()

        return start_location, end_location


    return None, None


# =========================================================
# MAIN FUNCTION FOR FASTAPI
# =========================================================

def extract_route(text):

    # First try NER

    start_location, end_location = extract_locations(text)

    # If NER does not find both,
    # use pattern extraction

    if start_location is None or end_location is None:

        start_location, end_location = extract_using_pattern(text)


    # Return structured result

    return {
        "start_location": start_location,
        "end_location": end_location
    }