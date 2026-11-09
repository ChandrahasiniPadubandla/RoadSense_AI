import re
from typing import Dict, List, Optional, Tuple, Any
import spacy
from spacy.pipeline import EntityRuler

# Comprehensive gazetteer of Hyderabad & Telangana regions, junctions, corridors, and transport nodes
KNOWN_LOCATIONS = [
    # Major Hubs & IT Corridors
    "Hitech City", "Cyberabad", "Madhapur", "Gachibowli", "Kondapur", "Raidurg", "Financial District",
    "Knowledge City", "Nanakramguda", "Kokapet", "Mindspace",
    
    # Central & Western
    "Banjara Hills", "Jubilee Hills", "Ameerpet", "Panjagutta", "Somajiguda", "Begumpet",
    "Khairatabad", "Lakdikapul", "Mehdipatnam", "Masab Tank", "Tolichowki", "Shaikpet",
    
    # Northern & North-Western
    "Secunderabad", "Kukatpally", "KPHB", "Miyapur", "Nizampet", "Bachupally", "Kompally",
    "Balanagar", "IDPL", "Moosapet", "Sanathnagar", "Erragadda", "Bharat Nagar", "Fateh Nagar",
    "Alwal", "Bowenpally", "Bolarum", "Trimulgherry", "Malkajgiri", "Sainikpuri", "Jeedimetla", "Chintal",
    
    # Eastern
    "Uppal", "Habsiguda", "Boduppal", "Nagole", "Kusaiguda", "ECIL", "Tarnaka", "Nacharam",
    "Ramanthapur", "Peerzadiguda", "Ghatkesar", "Gandimaisamma",
    
    # Southern & Old City
    "Charminar", "LB Nagar", "Kothapet", "Dilsukhnagar", "Kachiguda", "Gandipet", "Malakpet", "Santosh Nagar",
    "Chandrayangutta", "Falaknuma", "Bahadurpura", "Attapur", "Rajendranagar", "Shamshabad",
    
    # Highways, Corridors & Landmarks
    "Outer Ring Road", "ORR", "PVNR Expressway", "Airport Road", "Rajiv Gandhi International Airport",
    "Tank Bund", "Necklace Road", "Jubilee Checkpost", "Cyber Towers", "Paradise Junction"
]


class LocationExtractor:
    """
    Hybrid Named Entity Recognition (NER) location extractor combining:
    1. spaCy statistical NER model with custom domain EntityRuler
    2. Regex patterns for corridors (Origin -> Destination) and prepositions
    3. Gazetteer dictionary fallback for localized entities
    """
    
    def __init__(self, spacy_model: str = "en_core_web_sm"):
        self.nlp = None
        self.known_locations = KNOWN_LOCATIONS
        # Sorted by length descending so multi-word locations match first (e.g. "Banjara Hills" before "Hills")
        self.sorted_locations = sorted(self.known_locations, key=len, reverse=True)
        self._init_spacy(spacy_model)
        self._init_patterns()

    def _init_spacy(self, model_name: str):
        try:
            self.nlp = spacy.load(model_name)
            # Add custom entity ruler if not present
            if "entity_ruler" not in self.nlp.pipe_names:
                ruler = self.nlp.add_pipe("entity_ruler", before="ner")
                patterns = [{"label": "GPE", "pattern": loc} for loc in self.known_locations]
                ruler.add_patterns(patterns)
        except Exception as e:
            print(f"[Warning] spaCy could not be initialized with '{model_name}': {e}. Using pattern fallback.")
            self.nlp = None

    def _init_patterns(self):
        known_location_pattern = "|".join(
            re.escape(location) for location in self.sorted_locations
        )

        # Corridor patterns: (regex, is_destination_first)
        self.corridor_patterns = [
            # 1. from <origin> to <destination> (Highest priority, unambiguous)
            (
                re.compile(
                    r'\bfrom\s+([A-Za-z0-9\s\-]+?)\s+to\s+(?:reach\s+)?([A-Za-z0-9\s\-]+?)'
                    r'(?=[,\.\?!]|\s+(?:so|when|today|now|right now|this evening|tomorrow|later|this morning|via|if\s+i\s+(?:start|leave|depart)|after|in\s+\d+\s*(?:minutes?|mins?|hours?|hrs?)|give\s+me|show|tell|find|check|calculate|estimate|what|how)\b|$)',
                    re.IGNORECASE
                ),
                False
            ),
            # 2. route/drive/travel from <origin> to <destination>
            (
                re.compile(
                    r'\b(?:route|drive|travel|trip|commute)\s+(?:from\s+)?([A-Za-z0-9\s\-]+?)\s+to\s+([A-Za-z0-9\s\-]+?)'
                    r'(?=[,\.\?!]|\s+(?:if\s+i\s+(?:start|leave|depart)|after|in\s+\d+\s*(?:minutes?|mins?|hours?|hrs?)|give\s+me|show|tell|find|check|calculate|estimate|what|how)\b|$)',
                    re.IGNORECASE
                ),
                False
            ),
            # 3. between <origin> and <destination>
            (
                re.compile(
                    r'\bbetween\s+([A-Za-z0-9\s\-]+?)\s+and\s+([A-Za-z0-9\s\-]+?)'
                    r'(?=[,\.\?!]|\s+(?:today|now|right now|this evening|tomorrow|later|this morning|via|if\s+i\s+(?:start|leave|depart)|after|in\s+\d+\s*(?:minutes?|mins?|hours?|hrs?)|give\s+me|show|tell|find|check|calculate|estimate|what|how)\b|$)',
                    re.IGNORECASE
                ),
                False
            ),
            # 4. at/near <destination> if i start/leave from <origin>
            (
                re.compile(
                    r'\b(?:at|near)\s+([A-Za-z0-9\s\-]+?)\s+if\s+i\s+(?:start|leave|depart)\s+from\s+([A-Za-z0-9\s\-]+?)(?=[,\.\?!]|$)',
                    re.IGNORECASE
                ),
                True
            ),
            # 5. reach <destination> from <origin> (Negative lookahead to avoid matching time/if conditions)
            (
                re.compile(
                    r'\breach\s+(?!if\b|when\b|after\b)([A-Za-z0-9\s\-]+?)\s+from\s+((?:(?!\bto\b)[A-Za-z0-9\s\-])+?)'
                    r'(?=[,\.\?!]|\s+(?:today|now|right now|this evening|tomorrow|later|this morning|via|if\s+i\s+(?:start|leave|depart)|after|in\s+\d+\s*(?:minutes?|mins?|hours?|hrs?)|give\s+me|show|tell|find|check|calculate|estimate|what|how)\b|$)',
                    re.IGNORECASE
                ),
                True
            ),
            # 6. reach <origin> to <destination>
            (
                re.compile(
                    r'\breach\s+([A-Za-z0-9\s\-]+?)\s+to\s+([A-Za-z0-9\s\-]+?)'
                    r'(?=[,\.\?!]|\s+(?:if\s+i\s+(?:start|leave|depart)|after|in\s+\d+\s*(?:minutes?|mins?|hours?|hrs?)|give\s+me|show|tell|find|check|calculate|estimate|what|how)\b|$)',
                    re.IGNORECASE
                ),
                False
            ),
            # 7. A bare "origin to destination" route.
            (
                re.compile(
                    rf'^\s*({known_location_pattern})\s+to\s+({known_location_pattern})\s*[.!?]?\s*$',
                    re.IGNORECASE,
                ),
                False
            ),
        ]
        
        # Single target location patterns
        self.single_location_patterns = [
            re.compile(r'\b(?:near|around|at|in|towards|through|for|to|outside)\s+(?!which\b|what\b|where\b|who\b|when\b|how\b|reach\b|start\b|if\b)([A-Za-z0-9\s\-]+?)(?=[,\.\?!]|\s+(?:today|now|right now|this evening|tomorrow|later|this morning|right|zone|area|which|what|where|who|when|how)\b|$)', re.IGNORECASE),
            re.compile(r'\b(?:route to|road to|drive to|way to|commute to)\s+([A-Za-z0-9\s\-]+?)(?=[,\.\?!]|$)', re.IGNORECASE),
            re.compile(r'\b(?:near the|around the)\s+([A-Za-z0-9\s\-]+?)(?=[,\.\?!]|$)', re.IGNORECASE),
        ]

    def _clean_location(self, text: str) -> Optional[str]:
        if not text:
            return None
        text = text.strip()
        # Remove trailing/leading punctuation
        text = re.sub(r'^[,\.\?!\-\s]+|[,\.\?!\-\s]+$', '', text)

        # Reject temporal or conditional clauses mistakenly captured
        bad_clause_patterns = [
            r'\bif\s+i\b',
            r'\bstart\b',
            r'\bleave\b',
            r'\bdepart\b',
            r'\bafter\b',
            r'\bwhen\b',
            r'\breach\b',
            r'\b\d+\s*(?:minutes?|mins?|hours?|hrs?)\b',
            r'\bto\b',  # multiple locations crammed
            r'\bfrom\b',
        ]
        text_lower = text.casefold()
        for bp in bad_clause_patterns:
            if re.search(bp, text_lower):
                return None

        # Filter out common stop words or question words mistakenly captured
        stopwords = {
            "my", "the", "a", "an", "this", "that", "these", "those", "here", "there",
            "which", "what", "where", "who", "when", "how",
            "city", "center", "city center", "work", "home", "office", "selected",
            "location", "junction", "route", "trip", "journey", "road", "area",
            "market", "market district", "airport road"
        }
        if text.lower() in stopwords and text.lower() not in ["airport road"]:
            return None

        # Normalize common variations / abbreviations / misspellings
        normalized_map = {
            "gamdipet": "Gandipet",
            "moospet": "Moosapet",
            "moosapet": "Moosapet",
            "idpl": "IDPL",
            "hitec city": "Hitech City",
            "hitech city": "Hitech City",
            "kphb": "KPHB",
            "ecil": "ECIL",
            "orr": "ORR",
            "sec'bad": "Secunderabad",
            "secbad": "Secunderabad",
        }
        if text.casefold() in normalized_map:
            return normalized_map[text.casefold()]

        # Check against known locations for proper casing
        for known in self.sorted_locations:
            if text.lower() == known.lower():
                return known

        # Return capitalized representation if length > 2
        return text.title() if len(text) > 2 else None

    def extract_with_spacy(self, text: str) -> Tuple[List[str], List[Dict[str, Any]]]:
        if not self.nlp:
            return [], []
        doc = self.nlp(text)
        locations = []
        raw_entities = []
        for ent in doc.ents:
            if ent.label_ in ("GPE", "LOC", "FAC", "ORG"):
                cleaned = self._clean_location(ent.text)
                if cleaned and cleaned not in locations:
                    locations.append(cleaned)
                    raw_entities.append({"text": ent.text, "label": ent.label_, "cleaned": cleaned})
        return locations, raw_entities

    def extract_with_patterns(self, text: str) -> Dict[str, Any]:
        origin = None
        destination = None
        detected_locs = []

        # Check corridor patterns first
        for pat, is_dest_first in self.corridor_patterns:
            match = pat.search(text)
            if match:
                if is_dest_first:
                    dest_raw, orig_raw = match.group(1), match.group(2)
                else:
                    orig_raw, dest_raw = match.group(1), match.group(2)
                orig = self._clean_location(orig_raw)
                dest = self._clean_location(dest_raw)
                if orig and dest:
                    origin, destination = orig, dest
                    detected_locs.extend([orig, dest])
                    break

        # Check single location patterns if no corridor found
        if not detected_locs:
            for pat in self.single_location_patterns:
                matches = pat.findall(text)
                for m in matches:
                    cleaned = self._clean_location(m)
                    if cleaned and cleaned not in detected_locs:
                        detected_locs.append(cleaned)

        # Dictionary / Gazetteer scanning fallback in the order locations appear.
        text_lower = text.lower()
        location_matches = []
        for loc in self.sorted_locations:
            pattern = rf'\b{re.escape(loc.lower())}\b'
            for match in re.finditer(pattern, text_lower):
                location_matches.append((match.start(), match.end(), loc))

        location_matches.sort(key=lambda item: (item[0], -(item[1] - item[0])))
        non_overlapping_matches = []
        for start, end, location in location_matches:
            if any(
                start < known_end and end > known_start
                for known_start, known_end, _ in non_overlapping_matches
            ):
                continue
            non_overlapping_matches.append((start, end, location))

        gazetteer_locations = []
        for _, _, location in non_overlapping_matches:
            if location not in gazetteer_locations:
                gazetteer_locations.append(location)

        if not origin and len(gazetteer_locations) >= 2:
            detected_locs = gazetteer_locations
        else:
            for location in gazetteer_locations:
                if location not in detected_locs:
                    detected_locs.append(location)

        return {
            "locations": detected_locs,
            "origin": origin,
            "destination": destination
        }

    def extract(self, text: str) -> Dict[str, Any]:
        """
        Unified extraction method executing corridor patterns and gazetteer first,
        with spaCy NER enhancements.
        """
        pattern_res = self.extract_with_patterns(text)
        spacy_locs, raw_entities = self.extract_with_spacy(text)

        origin = pattern_res["origin"]
        destination = pattern_res["destination"]
        
        # Merge locations while preserving order
        combined_locs = []
        for loc in pattern_res["locations"] + spacy_locs:
            if loc not in combined_locs:
                combined_locs.append(loc)

        # If corridor wasn't captured explicitly by pattern, but 2 locations were detected
        if not origin and not destination and len(combined_locs) >= 2:
            origin = combined_locs[0]
            destination = combined_locs[1]

        primary_loc = destination or origin or (combined_locs[0] if combined_locs else "Hyderabad (General)")

        method = "spacy_ner + patterns" if spacy_locs and pattern_res["locations"] else (
            "pattern_corridor" if pattern_res["origin"] else ("spacy_ner" if spacy_locs else "pattern_fallback")
        )

        return {
            "locations": combined_locs,
            "origin": origin,
            "destination": destination,
            "primary_location": primary_loc,
            "is_corridor": bool(origin and destination),
            "extraction_method": method,
            "entities": raw_entities
        }

# Global extractor instance
location_extractor = LocationExtractor()
