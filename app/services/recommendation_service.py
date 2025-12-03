"""
Advanced Outfit Recommendation Engine
-------------------------------------
Simplified rule-based scoring:

- Color harmony
- Pattern compatibility
- Genre compatibility
- Event appropriateness

No gender presentation scoring.
"""

from sqlalchemy.orm import Session
from app.models import ClothingItem


# ---------------------------------------------
# COLOR HARMONY
# ---------------------------------------------
NEUTRALS = ["black", "white", "gray", "beige", "brown", "navy"]

COMPLEMENTARY = {
    "red": "green",
    "orange": "blue",
    "yellow": "purple",
    "green": "red",
    "blue": "orange",
    "purple": "yellow",
}

ANALOGOUS = {
    "red": ["orange", "purple"],
    "orange": ["red", "yellow"],
    "yellow": ["orange", "green"],
    "green": ["yellow", "blue"],
    "blue": ["green", "purple"],
    "purple": ["blue", "red"],
}

def color_score(c1: str, c2: str) -> int:
    if not c1 or not c2:
        return 0

    c1, c2 = c1.lower(), c2.lower()

    if c1 == c2:
        return 20

    if c1 in NEUTRALS or c2 in NEUTRALS:
        return 25

    if COMPLEMENTARY.get(c1) == c2:
        return 35

    if c2 in ANALOGOUS.get(c1, []):
        return 30

    return 10


# ---------------------------------------------
# PATTERN COMPATIBILITY
# ---------------------------------------------
def pattern_score(p1: str, p2: str) -> int:
    if not p1 or not p2:
        return 10

    if p1 == "solid" and p2 == "solid":
        return 20

    if p1 == "solid" or p2 == "solid":
        return 18

    return 5


# ---------------------------------------------
# GENRE COMPATIBILITY
# ---------------------------------------------
GENRE_COMPATIBILITY = {
    "formal": ["formal", "semi-formal"],
    "business": ["business", "business casual"],
    "casual": ["casual", "athleisure"],
    "semi-formal": ["formal", "semi-formal"],
    "business casual": ["business casual", "business"],
}

def genre_score(g1: str, g2: str) -> int:
    if not g1 or not g2:
        return 10

    g1, g2 = g1.lower(), g2.lower()

    if g1 == g2:
        return 20

    if g2 in GENRE_COMPATIBILITY.get(g1, []):
        return 18

    return 8


# ---------------------------------------------
# EVENT APPROPRIATENESS
# ---------------------------------------------
EVENT_RULES = {
    "wedding": {
        "avoid": ["white"],
        "genres": ["formal", "semi-formal"],
    },
    "funeral": {
        "colors": ["black", "dark gray", "navy"],
        "genres": ["formal"],
    },
    "interview": {
        "colors": ["black", "navy", "gray"],
        "genres": ["business", "business casual"],
    },
    "date_night": {
        "colors": NEUTRALS + ["red", "burgundy"],
        "genres": ["casual", "semi-formal"],
    },
}

def event_score(item: ClothingItem, event: str) -> int:
    if not event or event not in EVENT_RULES:
        return 10

    rules = EVENT_RULES[event]
    score = 10

    # avoid rules (e.g., wedding do not wear white)
    if "avoid" in rules and item.color in rules["avoid"]:
        return 0

    # event color guidelines
    if "colors" in rules:
        if item.color in rules["colors"]:
            score += 5
        else:
            score -= 5

    # genre guidelines
    if "genres" in rules:
        if item.genre in rules["genres"]:
            score += 5
        else:
            score -= 3

    return max(score, 0)


# ---------------------------------------------
# OUTFIT SCORE (0–100)
# ---------------------------------------------
def outfit_score(top: ClothingItem, bottom: ClothingItem, event: str) -> int:
    return (
        color_score(top.color, bottom.color)
        + pattern_score(top.pattern, bottom.pattern)
        + genre_score(top.genre, bottom.genre)
        + event_score(top, event)
        + event_score(bottom, event)
    )


# ---------------------------------------------
# MAIN PUBLIC FUNCTION
# ---------------------------------------------
def suggest_outfit(db: Session, event: str = None, preferred: str = None):
    """
    Find best-scoring (top, bottom) outfit.
    `preferred` is ignored since gender scoring is removed.
    """
    clothing = db.query(ClothingItem).all()

    if not clothing:
        return {"message": "Closet is empty."}

    tops = [c for c in clothing if c.category in ["shirt", "blouse", "sweater", "jacket"]]
    bottoms = [c for c in clothing if c.category in ["pants", "shorts", "skirt"]]

    if not tops or not bottoms:
        return {"message": "Not enough items to suggest an outfit."}

    best_score = -1
    best_top = None
    best_bottom = None

    for top in tops:
        for bottom in bottoms:
            score = outfit_score(top, bottom, event)

            if score > best_score:
                best_score = score
                best_top = top
                best_bottom = bottom

    if not best_top or not best_bottom:
        return {"message": "No valid outfit found."}

    return {
        "event": event,
        "score": best_score,
        "top": {
            "id": best_top.item_id,
            "color": best_top.color,
            "pattern": best_top.pattern,
            "category": best_top.category,
            "genre": best_top.genre,
            "image_url": best_top.image_url,
        },
        "bottom": {
            "id": best_bottom.item_id,
            "color": best_bottom.color,
            "pattern": best_bottom.pattern,
            "category": best_bottom.category,
            "genre": best_bottom.genre,
            "image_url": best_bottom.image_url,
        },
    }
