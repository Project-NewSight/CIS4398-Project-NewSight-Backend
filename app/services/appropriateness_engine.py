# app/services/appropriateness_engine.py

from typing import Tuple, List, Dict


class OccasionAppropriatenessEngine:
    """
    Rule-based engine for:
    - Event type (wedding, funeral, court, etc.)
    - Culture (western, hindu, muslim, jewish, chinese, yoruba, santeria, catholic, etc.)
    - Weather (hot/warm/cool/cold/freezing)
    - Whether user will be outside a lot
    - Item attributes (category, pattern, primary_color)
    """

    # How formal different patterns are (rough scale 0–3)
    PATTERN_FORMALITY = {
        "solid": 3,
        "striped": 2,
        "plaid": 1,
        "patterned": 1,
        "graphic": 0,
    }

    # Event → “base event type” so we can share rules
    EVENT_BASE = {
        "interview": "business_formal",
        "job interview": "business_formal",
        "court": "business_formal",
        "court appearance": "business_formal",

        "wedding": "wedding",
        "ceremony": "wedding",
        "reception": "wedding",

        "funeral": "funeral",
        "memorial": "funeral",

        "graduation": "semi_formal",
        "religious service": "religious",
        "church": "religious",
        "mosque": "religious",
        "temple": "religious",
        "mass": "religious",

        "club": "nightlife",
        "clubbing": "nightlife",
        "night out": "nightlife",

        "brunch": "smart_casual",
        "dinner": "smart_casual",
        "date": "smart_casual",
        "meet the parents": "smart_casual",

        "gym": "sport",
        "workout": "sport",
        "practice": "sport",
    }

    CATEGORY_RULES: Dict[str, Dict[str, List[str]]] = {
        "business_formal": {
            # Business-formal is the strictest category.
            "disallowed": [
                "hoodie",
                "tank top",
                "shorts",
                "graphic tee",
                "tshirt",
                "t-shirt",
                "tee",
                "jeans",
                "crop top",
            ],
        },
        "wedding": {
            # Weddings are semi-formal or formal but still flexible depending on culture.
            "disallowed": [
                "hoodie",
                "shorts",
                "tshirt",
                "t-shirt",
                "tee",
                "tank top",
                "graphic tee",
                "jeans",
                "sweater",      # too casual for most weddings unless layered
                "crop top",
            ],
        },
        "funeral": {
            # Funerals require solemn, conservative clothing.
            "disallowed": [
                "shorts",
                "tank top",
                "graphic tee",
                "tshirt",
                "t-shirt",
                "tee",
                "crop top",
                "hoodie",       # added for decorum
            ],
        },
        "nightlife": {
            # Nightlife is flexible; almost anything is allowed.
            "disallowed": [],
        },
        "religious": {
            # Shoulders covered, modest attire expected.
            "disallowed": [
                "tank top",
                "crop top",
                "very short dress",
                "tshirt",
                "t-shirt",
                "tee",
                "graphic tee",
                "shorts",
            ],
        },
        "sport": {
            # Sport events require athletic wear and disallow dress clothing.
            "allowed": [
                "tshirt",
                "t-shirt",
                "tank top",
                "leggings",
                "shorts",
                "sport",
                "athletic",
            ],
            "disallowed": [
                "jeans",
                "dress",
                "blazer",
                "coat",
                "cardigan",
                "skirt",        # added (not practical)
            ],
        },
    }


    # Color norms by culture + base event type
    COLOR_CULTURAL_RULES = {
        "wedding": {
            "western": {"avoid": ["white"], "notes": "Avoid white, which is reserved for the bride."},
            "hindu": {
                "avoid": ["black", "white"],
                "preferred": ["red", "gold", "bright"],
                "notes": "Bright colors are preferred; avoid black and white."
            },
            "muslim": {
                "avoid": [],
                "notes": "Modesty is more important than color; avoid very flashy or overly tight outfits."
            },
            "jewish": {"avoid": ["white"], "notes": "Avoid pure white; modesty depends on community."},
            "chinese": {
                "avoid": ["white", "black"],
                "preferred": ["red", "gold"],
                "notes": "Red and gold are lucky; avoid white and black."
            },
            "yoruba": {
                "avoid": [],
                "notes": "Traditional attire and bright colors are common; follow any family color themes."
            },
            "santeria": {
                "avoid": [],
                "notes": "Dress can be bright or all-white depending on the house and orisha focus."
            },
            "catholic": {
                "avoid": [],
                "notes": "Avoid very revealing outfits; shoulders covered is often preferred in church."
            },
        },
        "funeral": {
            "western": {
                "preferred": ["black", "charcoal", "navy", "dark gray"],
                "avoid": ["red", "yellow", "bright"],
                "notes": "Dark, muted clothing is expected; avoid bright colors."
            },
            "chinese": {
                "preferred": ["white"],
                "avoid": ["red"],
                "notes": "White is often worn; red is inappropriate."
            },
            "hindu": {
                "preferred": ["white"],
                "avoid": ["black", "bright"],
                "notes": "White is common; bright or festive colors are discouraged."
            },
            "muslim": {
                "preferred": ["dark"],
                "avoid": ["bright"],
                "notes": "Modest, dark clothing is typical."
            },
            "jewish": {
                "preferred": ["dark"],
                "avoid": ["bright"],
                "notes": "Dark, conservative dress is common."
            },
            "yoruba": {
                "preferred": ["white", "muted"],
                "avoid": ["bright red"],
                "notes": "White or muted tones are common; families may specify colors."
            },
            "santeria": {
                "preferred": ["white"],
                "avoid": ["bright"],
                "notes": "White is often worn for mourning rituals."
            },
            "catholic": {
                "preferred": ["black", "dark"],
                "avoid": ["bright"],
                "notes": "Dark, modest clothing is typical."
            },
        },
    }

    @staticmethod
    def normalize_weather(weather: str) -> str:
        """
        Normalize user-supplied weather into: hot, warm, cool, cold, freezing.
        Accepts words ("cold", "hot") or numbers ("35", "80").
        """
        w = weather.strip().lower()
        # Try numeric first
        try:
            temp = float(w)
            if temp <= 32:
                return "freezing"
            if temp <= 45:
                return "cold"
            if temp <= 60:
                return "cool"
            if temp <= 75:
                return "warm"
            return "hot"
        except ValueError:
            # Not a number; use simple mapping
            if "freez" in w:
                return "freezing"
            if "cold" in w:
                return "cold"
            if "cool" in w:
                return "cool"
            if "warm" in w:
                return "warm"
            if "hot" in w:
                return "hot"
        return "unknown"

    @classmethod
    def analyze(
        cls,
        event: str,
        item: Dict[str, str],
        culture: str = "western",
        weather: str = "mild",
        mostly_outside: bool = False,
    ) -> Tuple[bool, List[str], str]:
        """
        Returns:
            (is_appropriate, reasons_list, spoken_message)
        """

        # -------------------------------
        # PREP + NORMALIZATION
        # -------------------------------
        reasons: List[str] = []
        event_lower = (event or "").lower()
        culture_lower = (culture or "").lower()

        base_event = cls.EVENT_BASE.get(event_lower, None)
        normalized_weather = cls.normalize_weather(weather)

        # Extract item features
        category = (item.get("category") or "").lower()
        category_unified = (item.get("category_unified") or category).lower()
        raw_category = (item.get("category_raw_yolo") or "").lower()
        pattern = (item.get("pattern") or "solid").lower()
        color = (item.get("primary_color") or "").lower()
        printed_text = (item.get("printed_text") or "").lower()

        # -------------------------------
        # 0. OFFENSIVE OR POLITICAL TEXT CHECK
        # -------------------------------
        if printed_text:
            banned_terms = [
                "fuck", "suck", "trump", "biden", "maga", "racist",
                "sex", "nazi", "fascist", "kill", "hate"
            ]
            if any(term in printed_text for term in banned_terms):
                reasons.append(
                    "The printed text includes offensive or political language, which is inappropriate for formal or public settings."
                )

        # -------------------------------
        # 1. CATEGORY RULES
        # -------------------------------
        if base_event and base_event in cls.CATEGORY_RULES:
            rules = cls.CATEGORY_RULES[base_event]
            disallowed = [c.lower() for c in rules.get("disallowed", [])]

            # Unified category check
            if category_unified in disallowed:
                reasons.append(f"A {category_unified} is usually not considered appropriate for a {event_lower}.")

        # -------------------------------
        # 1.5 SPECIAL RULES FOR PROFESSIONAL EVENTS (interview, court)
        # -------------------------------
        # YOLO raw category is used because unified category may be too broad (e.g. t-shirt → shirt)
        if base_event == "business_formal":
            if raw_category in ["t-shirt", "tee", "tshirt", "shorts"]:
                reasons.append(f"A {raw_category} is not appropriate for a {event_lower}.")
            if printed_text:
                reasons.append("Printed clothing is discouraged for professional or formal events.")

        # -------------------------------
        # 2. PATTERN FORMALITY RULES
        # -------------------------------
        formality = cls.PATTERN_FORMALITY.get(pattern, 1)
        if base_event in ["business_formal", "wedding", "funeral"]:
            if formality < 2:
                reasons.append(f"{pattern} patterns lean casual and may not fit well for a {event_lower}.")

        # -------------------------------
        # 3. COLOR CULTURAL RULES
        # -------------------------------
        if base_event in ["wedding", "funeral"]:
            culture_rules = cls.COLOR_CULTURAL_RULES.get(base_event, {}).get(culture_lower, {})
            avoid = [a.lower() for a in culture_rules.get("avoid", [])]
            preferred = [p.lower() for p in culture_rules.get("preferred", [])]
            notes = culture_rules.get("notes", "")

            if any(a in color for a in avoid):
                reasons.append(f"{color} is discouraged for a {event_lower} in {culture_lower} cultural settings.")

            if preferred and any(p in color for p in preferred):
                reasons.append(f"{color} is commonly considered appropriate for a {event_lower} in {culture_lower} contexts.")

            if notes:
                reasons.append(notes)

        # -------------------------------
        # 4. WEATHER APPROPRIATENESS RULES
        # -------------------------------
        if mostly_outside:
            if normalized_weather in ["cold", "freezing"]:
                if category_unified in ["t-shirt", "tank top", "dress", "skirt"] and "sweater" not in category_unified:
                    reasons.append(
                        f"It will be {normalized_weather} and you’ll be outside, so a {category_unified} may be too light."
                    )
            if normalized_weather in ["hot", "warm"]:
                if category_unified in ["coat", "jacket", "hoodie", "sweater"]:
                    reasons.append(
                        f"It will be {normalized_weather} and you’ll be outside, so a {category_unified} may be too warm."
                    )

        # -------------------------------
        # 5. FINAL VERDICT
        # -------------------------------
        bad_keywords = ["not appropriate", "discouraged", "too", "offensive", "political"]
        is_ok = not any(any(bad in r.lower() for bad in bad_keywords) for r in reasons)

        if is_ok:
            spoken = f"Yes, this looks appropriate for a {event_lower}."
            if reasons:
                spoken += " " + " ".join(reasons)
        else:
            spoken = f"This might not be ideal for a {event_lower}. " + " ".join(reasons)

        return is_ok, reasons, spoken
