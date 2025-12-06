from models.clothing_item import ClothingItem
from sqlalchemy.orm import Session
import numpy as np

def cosine_similarity(a, b):
    if a is None or b is None:
        return -1
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def find_closest_item(db: Session, user_id: int, query_vec, features):
    items = (
        db.query(ClothingItem)
          .filter(ClothingItem.user_id == user_id)
          .all()
    )

    best_item = None
    best_score = -1

    for item in items:
        sim = cosine_similarity(query_vec, item.embedding)

        # bonus for metadata match
        if item.category == features["category"]:
            sim += 0.15
        if item.color == features["color"]:
            sim += 0.10

        if sim > best_score:
            best_score = sim
            best_item = item

    return best_item, best_score
