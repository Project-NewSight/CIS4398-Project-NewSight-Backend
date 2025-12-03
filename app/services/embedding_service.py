"""
Embedding Service using CLIP (sentence-transformers)
------------------------------------------------------
Creates embeddings from clothing images so the headset
can recognize items in different lighting or angles.
"""

import numpy as np
from numpy.linalg import norm
from PIL import Image
from sentence_transformers import SentenceTransformer
from app.models import ClothingItem
# -----------------------------------------
# Load CLIP model once at startup
# Output dimension = 512
# -----------------------------------------
clip_model = SentenceTransformer("clip-ViT-B-32")
print("🔥 USING CLIP 512 EMBEDDING SERVICE — IMPORTED FROM:", __file__)


def generate_embedding(image_path: str) -> list:
    """
    Generate a 512-dimensional CLIP embedding for an image.
    Works offline. No TensorFlow or OpenAI required.
    """
    try:
        img = Image.open(image_path).convert("RGB")
        embedding = clip_model.encode(img)
        return embedding.tolist()
    except Exception as e:
        print("Embedding error:", e)
        return [0.0] * 512


def embedding_to_string(vec: list) -> str:
    """Store embedding as comma-separated text in DB."""
    return ",".join(str(v) for v in vec)


def string_to_embedding(vec_str: str) -> np.ndarray:
    """Convert DB text back into numpy array."""
    if not vec_str:
        return np.zeros((512,))
    return np.array([float(v) for v in vec_str.split(",")])

def cosine_similarity(a, b):
    """Fast cosine similarity."""
    a = np.array(a)
    b = np.array(b)

    if norm(a) == 0 or norm(b) == 0:
        return -1

    return float(np.dot(a, b) / (norm(a) * norm(b)))


def find_closest_item(closet_id: int, query_vec: list, features: dict, db):
    """
    Identify which item in the closet is most similar to the image.
    Uses:
    - cosine similarity of embeddings
    - category bonus
    - color bonus
    """

    print("\n🟦 [find_closest_item] Starting identity search…")
    print(f"   → closet_id: {closet_id}")
    print(f"   → detected category: {features.get('category')}")
    print(f"   → detected color: {features.get('color')}")

    items = db.query(ClothingItem).filter_by(closet_id=closet_id).all()

    if not items:
        print("❌ No clothing found for this closet_id.")
        return None, -1.0

    best_item = None
    best_score = -999.0

    for item in items:
        item_vec = string_to_embedding(item.embedding_str)
        sim = cosine_similarity(query_vec, item_vec)

        # semantic bonuses
        if item.category == features.get("category"):
            sim += 0.15
        if item.color == features.get("color"):
            sim += 0.10

        print(f"   → item {item.item_id}: sim={sim:.4f}  ({item.color} {item.category})")

        if sim > best_score:
            best_score = sim
            best_item = item

    print(f"🏆 Best match = Item {best_item.item_id}  score={best_score:.4f}")
    return best_item, best_score