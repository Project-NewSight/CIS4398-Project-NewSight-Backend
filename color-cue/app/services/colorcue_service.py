"""
ColorCue Detection Pipeline (Roboflow Version – Robust + Debug)
------------------------------------------------------
Adds:
- Very verbose debug prints for every step
- Guardrails for bbox + pattern + color
"""

# region IMPORTS & INITIALIZATION
import os
from PIL import Image, ImageStat
from colorthief import ColorThief
import webcolors
from inference_sdk import InferenceHTTPClient
from statistics import mode
from google.cloud import vision

print("🔥 [ColorCue] colorcue_service.py imported")

# Roboflow clients
DETECT_CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="XkVRQV95oaJhYJsn1wVP"
)
CLASSIFY_CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="XkVRQV95oaJhYJsn1wVP"
)
COLOR6_CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="XkVRQV95oaJhYJsn1wVP"
)
COLOR14_CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="XkVRQV95oaJhYJsn1wVP"
)

YOLO_MODEL_ID = "clothing-detection-3wmlb/4"
CLASSIFIER_MODEL_ID = "clothing-classification-nsmcm/1"
COLOR6_MODEL_ID = "color-detection-sd8fb/1"
COLOR14_MODEL_ID = "color-classification-upmyn/1"

CONFIDENCE_THRESHOLD = 0.55
# endregion


# region COLOR MODELS (6-color, 14-color, fallback, multipoint sampling)
def force_low_conf_color():
    return "unknown", 0.001

def detect_color6(image_path):
    try:
        resp = COLOR6_CLIENT.infer(image_path, model_id=COLOR6_MODEL_ID)
        preds = resp.get("predictions", [])
        if not preds:
            return force_low_conf_color()
        best = max(preds, key=lambda x: x["confidence"])
        return best["class"], best["confidence"]
    except Exception as e:
        print("🔥 [color6 ERROR]", repr(e))
        return force_low_conf_color()

def detect_color14(image_path):
    try:
        resp = COLOR14_CLIENT.infer(image_path, model_id=COLOR14_MODEL_ID)
        preds = resp.get("predictions", None)

        if isinstance(preds, dict):
            best_color = max(preds.items(), key=lambda x: x[1].get("confidence", 0))
            return best_color[0], best_color[1].get("confidence", 0)

        if isinstance(preds, list):
            dict_preds = [p for p in preds if isinstance(p, dict)]
            if dict_preds:
                best = max(dict_preds, key=lambda x: x.get("confidence", 0))
                return best["class"], best["confidence"]

        return "unknown", 0.0

    except Exception as e:
        print("🔥 [color14 ERROR]", repr(e))
        return "unknown", 0.0

def sample_rgb_points(image, bbox=None):
    print("🎨 [sample_rgb_points] Running multi-point sampler")

    if bbox:
        left = int(bbox["x"]); top = int(bbox["y"])
        right = left + int(bbox["width"])
        bottom = top + int(bbox["height"])
        region = image.crop((left, top, right, bottom))
    else:
        region = image

    width, height = region.size
    samples = []

    grid = 6
    for i in range(grid):
        for j in range(grid):
            px = int((i + 0.5) * width / grid)
            py = int((j + 0.5) * height / grid)
            samples.append(region.getpixel((px, py)))

    color_names = [closest_color_name(rgb) for rgb in samples]

    try:
        return mode(color_names)
    except:
        return color_names[0]
'''
def run_color_models(crop_path, full_image_path, image=None, bbox=None):
    print("🎨 Running COLOR-6 + COLOR-14 models…")

    c6, conf6 = detect_color6(crop_path)
    c14, conf14 = detect_color14(crop_path)

    print("\n🎨 COLOR MODEL COMPARISON")
    print(f"   COLOR-6:   {c6} ({conf6:.3f})")
    print(f"   COLOR-14:  {c14} ({conf14:.3f})")

    best_conf = max(conf6, conf14)
    if best_conf > 0.01:
        if conf14 >= conf6:
            print(f"🏅 Final Color chosen from COLOR-14 = {c14} ({conf14:.3f})")
            return c14, conf14
        print(f"🏅 Final Color chosen from COLOR-6 = {c6} ({conf6:.3f})")
        return c6, conf6

    print("🎨 [COLOR MODELS] ML models failed → using multi-point RGB sampler")
    fallback = sample_rgb_points(image, bbox)
    return fallback, 0.001
# endregion
'''
def debug_color_sources(model1_color, model1_conf,
                        model2_color, model2_conf,
                        vision_swatches):

    print("\n\n=================== 🎨 COLOR DEBUG PANEL ===================")

    # MODEL 1 (6-color)
    print("🟦 MODEL 1 — 6-Color Detector")
    print(f"   Predicted: {model1_color}")
    print(f"   Confidence: {model1_conf:.3f}")

    # MODEL 2 (14-color)
    print("\n🟩 MODEL 2 — 14-Color Classifier")
    print(f"   Predicted: {model2_color}")
    print(f"   Confidence: {model2_conf:.3f}")

    # GOOGLE VISION
    print("\n🟧 GOOGLE VISION — Raw Swatches")
    for i, sw in enumerate(vision_swatches):
        r, g, b = sw["r"], sw["g"], sw["b"]
        lum = 0.2126*r + 0.7152*g + 0.0722*b
        print(f"   Swatch #{i+1}: RGB({r},{g},{b})  "
              f"pixel_fraction={sw['pixel_fraction']:.3f}  "
              f"score={sw['score']:.3f}  "
              f"luminance={lum:.1f}")

    print("============================================================\n")
SUPPORTED_COLORS = {"black", "blue", "green", "red", "white", "yellow"}



def choose_final_color(model1_color, model1_conf,
                       model2_color, model2_conf,
                       vision_swatches,
                       image_path=None):

    print("\n=================== 🎨 FINAL COLOR DECISION START ===================")
    debug_color_sources(model1_color, model1_conf,
                        model2_color, model2_conf,
                        vision_swatches)

    # ----------------------------------------------------------
    # Helper functions
    # ----------------------------------------------------------
    def luminance(r, g, b):
        return 0.2126*r + 0.7152*g + 0.0722*b

    def saturation(r,g,b):
        mx = max(r,g,b)
        mn = min(r,g,b)
        if mx == 0:
            return 0
        return (mx - mn) / mx

    def is_brownish(r,g,b):
        l = luminance(r,g,b)
        s = saturation(r,g,b)

        # Brown is warm (red > green > blue) but NOT saturated like orange
        if not (r > g and g >= b):
            return False

        # Brown is mid–dark, not bright
        if l > 180:  # too bright = tan/beige/orange
            return False

        # Brown is low saturation warm color
        if s > 0.45:   # orange often 0.55–0.85
            return False

        # Must have red dominance but not extreme like orange
        if r - g < 8:
            return False  # too yellowish
        if r - g > 80:
            return False  # heading into orange

        # Must not be near-gray
        if abs(r - g) < 5 and abs(g - b) < 5:
            return False

        return True


    def is_grayish(r, g, b):
        lum = luminance(r,g,b)
        sat = saturation(r,g,b)

        # Channels must be nearly equal (true grayscale)
        if abs(r - g) > 12 or abs(g - b) > 12 or abs(r - b) > 12:
            return False

        # Prevent blue tint from being mistaken as gray
        if b - r > 12 or b - g > 12:
            return False

        # true gray has very low saturation
        if sat > 0.12:
            return False

        # avoid white/black confusions
        if lum < 40 or lum > 210:
            return False

        return True


    def is_pinkish(r, g, b):
        lum = luminance(r, g, b)
        sat = saturation(r, g, b)

        # must be red-heavy
        if not (r > g + 20 and r > b + 20):
            return False

        # pink is bright (light red)
        if lum < 150 or lum > 255:
            return False

        # pink has moderate saturation (not gray, not neon red)
        if not (0.25 < sat < 0.65):
            return False

        return True


    def is_purpleish(r,g,b):
        # Purple = red and blue high, green low
        return (
            b > g and r > g and
            (r - g) > 20 and (b - g) > 20 and
            50 < luminance(r,g,b) < 200
        )

    def is_orangeish(r, g, b):
        l = luminance(r, g, b)
        s = saturation(r, g, b)

        # Orange is warm (R > G >= B)
        if not (r > g and g >= b):
            return False

        # Luminance range of real fabrics (includes dim indoor lighting)
        if not (50 < l < 200):
            return False

        # Saturation of real fabric oranges (0.20–0.55 typical)
        if not (0.20 < s < 0.65):
            return False

        # Red/Green difference (loosened to catch less saturated oranges)
        if (r - g) < 10:
            return False  # too yellow
        
        # Orange requires G > B (loosened)
        if (g - b) < 5:
            return False

        return True



    # ----------------------------------------------------------
    # STEP 1 — Google Vision HARD OVERRIDES for special colors
    # ----------------------------------------------------------
    print("\n🔍 STEP 1 — Analyzing Google Vision Swatches...")

    brown_fraction = sum(sw["pixel_fraction"] for sw in vision_swatches
                         if is_brownish(sw["r"], sw["g"], sw["b"]))
    gray_fraction = sum(
        sw["pixel_fraction"] 
        for sw in vision_swatches
        if is_grayish(sw["r"], sw["g"], sw["b"]) and sw["pixel_fraction"] > 0.05
    )
    pink_fraction = sum(sw["pixel_fraction"] for sw in vision_swatches
                        if is_pinkish(sw["r"], sw["g"], sw["b"]))
    purple_fraction = sum(sw["pixel_fraction"] for sw in vision_swatches
                          if is_purpleish(sw["r"], sw["g"], sw["b"]))
    orange_fraction = sum(sw["pixel_fraction"] for sw in vision_swatches
                          if is_orangeish(sw["r"], sw["g"], sw["b"]))

    print(f"🟤 Brown fraction:  {brown_fraction:.3f}")
    print(f"⚪ Gray fraction:   {gray_fraction:.3f}")
    print(f"💗 Pink fraction:   {pink_fraction:.3f}")
    print(f"💜 Purple fraction: {purple_fraction:.3f}")
    print(f"🟧 Orange fraction: {orange_fraction:.3f}")

    # Overrides
    if brown_fraction > 0.30:
        print("🏅 GV OVERRIDE → brown (strong brown evidence)")
        print("====================================================================\n")
        return "brown"
    
    if brown_fraction > 0.20 and model2_color.lower() == "green":
        print("🏅 GV OVERRIDE → brown (brown beats false ML green)")
        return "brown"
    
    if brown_fraction > 0.15 and model1_color.lower() == "black":
        print("🏅 GV OVERRIDE → brown (brown beats false ML black)")
        return "brown"
    if brown_fraction > 0.15 and model2_color.lower() == "black":
        print("🏅 GV OVERRIDE → brown (brown beats false ML black)")
        return "brown"

    if gray_fraction > 0.35:
        print("🏅 GV OVERRIDE → gray (strong gray evidence)")
        print("====================================================================\n")
        return "gray"

    if pink_fraction > 0.20:
        print("🏅 GV OVERRIDE → pink (Vision pink detection)")
        print("====================================================================\n")
        return "pink"

    if purple_fraction > 0.20:
        print("🏅 GV OVERRIDE → purple (Vision purple detection)")
        print("====================================================================\n")
        return "purple"

    if orange_fraction > 0.08:
        print("🏅 GV OVERRIDE → orange (Vision orange detection)")
        print("====================================================================\n")
        return "orange"

    # ----------------------------------------------------------
    # STEP 2 — **Use ML models ONLY if they output a supported color**
    # ----------------------------------------------------------
    print("\n🔍 STEP 2 — Checking ML model predictions...")

    print(f"   Model2 predicts {model2_color} ({model2_conf:.3f})")
    if model2_color.lower() in SUPPORTED_COLORS and model2_conf >= 0.55:
        print("🏅 ML OVERRIDE → Model2 (supported color + high confidence)")
        print("====================================================================\n")
        return model2_color.lower()

    print(f"   Model1 predicts {model1_color} ({model1_conf:.3f})")
    if model1_color.lower() in SUPPORTED_COLORS and model1_conf >= 0.60:
        print("🏅 ML OVERRIDE → Model1 (supported color + high confidence)")
        print("====================================================================\n")
        return model1_color.lower()

    # ----------------------------------------------------------
    # STEP 3 — Luminance-based simple black/white
    # ----------------------------------------------------------
    print("\n🔍 STEP 3 — Checking basic luminance (black/white detection)...")

    # Orange, pink, purple = saturated clothing colors
    chromatic_fraction = orange_fraction + pink_fraction + purple_fraction

    print(f"🎨 Chromatic fraction (orange+pink+purple): {chromatic_fraction:.3f}")

    # If any chromatic color is present, never override with white/black
    if chromatic_fraction > 0.02:
        print("❌ Skipping white/black override (chromatic colors detected)")
    else:
        for sw in vision_swatches:
            lum = luminance(sw["r"], sw["g"], sw["b"])
            if lum < 40:
                print(f"🏅 GV OVERRIDE → black (luminance {lum:.1f} < 40)")
                print("====================================================================\n")
                return "black"
            if lum > 220 and sw["pixel_fraction"] > 0.50:
                print(f"🏅 GV OVERRIDE → white (luminance {lum:.1f} > 220, swatch > 50%)")
                print("====================================================================\n")
                return "white"
    # ----------------------------------------------------------
    # STEP 4 — Fallback to ColorThief
    # ----------------------------------------------------------
    print("\n🔍 STEP 4 — Fallback to ColorThief dominant color...")
    fallback = extract_dominant_color(image_path)
    print(f"🏅 DECISION: Dominant color fallback → {fallback}")
    print("====================================================================\n")
    return fallback



# region COLOR HELPERS (CSS color mapping + dominant color)
BASIC_COLORS = {
    # Neutrals
    "black": (0,0,0), "white": (255,255,255),
    "gray": (128,128,128), "light gray": (200,200,200),
    "dark gray": (64,64,64), "charcoal": (54,69,79),
    # Browns
    "brown": (150,75,0), "dark brown": (101,67,33),
    "tan": (210,180,140), "beige": (220,198,156),
    "khaki": (189,183,107), "taupe": (139,133,137),
    "camel": (193,154,107), "espresso": (60,40,20),
    # Reds
    "red": (200,0,0), "crimson": (153,0,0),
    "burgundy": (128,0,32), "wine": (114,47,55),
    "maroon": (128,0,0), "rose": (255,102,102),
    # Pinks
    "pink": (255,182,193), "hot pink": (255,105,180),
    "magenta": (255,0,255),
    # Oranges
    "orange": (255,140,0), "rust": (183,65,14),
    "coral": (255,127,80),
    # Yellows
    "yellow": (255,255,0), "mustard": (204,153,0),
    "gold": (255,215,0),
    # Greens
    "green": (0,128,0), "mint": (152,255,152),
    "sage": (158,163,143), "olive": (107,142,35),
    "forest green": (34,139,34), "emerald": (80,200,120),
    "lime": (191,255,0),
    # Blues
    "blue": (0,0,255), "sky blue": (135,206,235),
    "light blue": (173,216,230), "baby blue": (137,207,240),
    "royal blue": (65,105,225), "cobalt": (0,71,171),
    "navy": (0,0,128), "midnight blue": (25,25,112),
    "teal": (0,128,128), "aqua": (0,255,255),
    "turquoise": (64,224,208),
    # Purples
    "purple": (128,0,128), "lavender": (230,230,250),
    "violet": (143,0,255), "indigo": (75,0,130),
    "plum": (142,69,133), "eggplant": (97,64,81),
    "mauve": (224,176,255),
}

def closest_color_name(rgb):
    min_distance = float("inf")
    best = None
    for name, ref in BASIC_COLORS.items():
        dist = sum((rgb[i] - ref[i]) ** 2 for i in range(3))
        if dist < min_distance:
            best = name
            min_distance = dist
    return best

def extract_dominant_color(image_path):
    print(f"🎨 [extract_dominant_color] Using full image: {image_path}")
    try:
        rgb = ColorThief(image_path).get_color(quality=1)
        return closest_color_name(rgb)
    except Exception as e:
        print("⚠ [extract_dominant_color] Fallback:", repr(e))
        return "unknown"

def extract_dominant_color_in_crop(image, bbox):
    try:
        left = int(bbox["x"]); top = int(bbox["y"])
        right = left + int(bbox["width"])
        bottom = top + int(bbox["height"])

        crop = image.crop((left, top, right, bottom))
        crop.save("temp_color_crop.jpg")

        rgb = ColorThief("temp_color_crop.jpg").get_color(quality=1)
        os.remove("temp_color_crop.jpg")
        return closest_color_name(rgb)
    except:
        return None
    
def color_match_logic(top_color: str, bottom_color: str):
    """
    Basic color theory matcher:
    - Neutrals go with everything
    - Complementary color matches
    - Avoid same-color top & bottom unless it's black/white/neutral
    """

    neutrals = ["black", "white", "gray", "brown", "tan", "beige", "cream", "navy"]

    # Normalize
    a = (top_color or "").lower()
    b = (bottom_color or "").lower()

    # Neutral rule
    if a in neutrals or b in neutrals:
        return True, "Neutral colors like these generally match well."

    # Same color rule
    if a == b:
        return False, "Wearing the same bright color for both pieces can look unbalanced."

    # Complementary colors
    complementary = {
        "red": "green",
        "blue": "orange",
        "yellow": "purple",
        "green": "red",
        "orange": "blue",
        "purple": "yellow",
    }

    if complementary.get(a) == b or complementary.get(b) == a:
        return True, "These colors are complementary and visually pleasing together."

    # Otherwise: safe neutral fallback
    return True, "These colors generally go well together."

# endregion


# region DETECTION MODELS (YOLO + Classifier)
def detect_yolo(image_path):
    resp = DETECT_CLIENT.infer(image_path, model_id=YOLO_MODEL_ID)
    preds = resp.get("predictions", [])
    if not preds:
        return None

    best = max(preds, key=lambda p: p["confidence"])
    return {
        "category": best["class"],
        "confidence": best["confidence"],
        "bbox": {
            "x": best["x"], "y": best["y"],
            "width": best["width"], "height": best["height"],
        }
    }

def classify_crop(crop_path):
    print("🔵 [FLOW] Entered classify_crop()")
    crop_path = os.path.abspath(crop_path)

    try:
        resp = CLASSIFY_CLIENT.infer(crop_path, model_id=CLASSIFIER_MODEL_ID)
    except Exception as e:
        print(f"🔥 [CLASSIFIER ERROR] {repr(e)}")
        return None, 0

    preds = resp.get("predictions", [])
    if not preds:
        return None, 0

    best = max(preds, key=lambda x: x["confidence"])
    return best["class"], best["confidence"]

def detect_clothing_item(image_path):
    print("🟧 [detect_clothing_item] Sending image to YOLO:", image_path)
    image = Image.open(image_path)
    img_w, img_h = image.size

    try:
        response = DETECT_CLIENT.infer(image_path, model_id=YOLO_MODEL_ID)
        print("🟩 [YOLO] Raw response:", response)

        detections = response.get("predictions", [])
        print(f"🟧 [YOLO] #detections: {len(detections)}")

        if not detections:
            print("⚠ [YOLO] No detections found")
            return {"category": None, "confidence": 0, "bbox": None}

        best = max(detections, key=lambda d: d["confidence"])

        print("🟧 [YOLO] Best detection:", best)

        if best["confidence"] < CONFIDENCE_THRESHOLD:
            print(f"⚠ [YOLO] Low confidence: {best['confidence']:.3f}")
            return {"category": None, "confidence": 0, "bbox": None}

        bbox = {
            "x": best["x"],
            "y": best["y"],
            "width": best["width"],
            "height": best["height"]
        }
        bbox = clip_bbox_to_image(bbox, img_w, img_h)

        return {
            "category": best["class"],
            "confidence": best["confidence"],
            "bbox": bbox
        }

    except Exception as e:
        print("🔥 [YOLO ERROR]:", repr(e))
        return {"category": None, "confidence": 0, "bbox": None}

# endregion


# region HELPERS (bbox, crop, pattern, category-normalization)
def clip_bbox_to_image(bbox, img_w, img_h):
    return {
        "x": max(0, bbox["x"]),
        "y": max(0, bbox["y"]),
        "width": min(bbox["width"], img_w - bbox["x"]),
        "height": min(bbox["height"], img_h - bbox["y"])
    }

def is_valid_bbox(bbox, img_w, img_h):
    if bbox is None:
        return False
    if bbox["x"] > img_w or bbox["y"] > img_h:
        return False
    if bbox["width"] <= 1 or bbox["height"] <= 1:
        return False
    return True

def detect_pattern(image, bbox):
    try:
        left = int(bbox["x"]); top = int(bbox["y"])
        right = left + int(bbox["width"])
        bottom = top + int(bbox["height"])

        crop = image.crop((left, top, right, bottom)).convert("L")
        variance = ImageStat.Stat(crop).var[0]

        if variance < 200:
            return "solid"
        if variance < 1000:
            return "striped"
        return "patterned"

    except:
        return "solid"

def crop_for_classification(image, bbox):
    left = int(bbox["x"]); top = int(bbox["y"])
    right = left + int(bbox["width"])
    bottom = top + int(bbox["height"])

    crop = image.crop((left, top, right, bottom))
    safe_path = os.path.abspath("temp_classifier_crop.jpg")
    crop.save(safe_path)
    return safe_path

YOLO_TO_UNIFIED = {
    "t-shirt": "t-shirt",
    "tshirt": "t-shirt",
    "tee": "t-shirt",

    "longsleeve": "long-sleeve",
    "long_sleeve": "long-sleeve",

    "pullover": "sweater",
    "sweatshirt": "sweater",
    "sweaters": "sweater",

    "top": "top",      
    "formal_shirt": "dress-shirt",  

    "jeans": "pants",
    "trousers": "pants",

    "short": "shorts",
    "shorts": "shorts",

    "skirt": "skirt",
    "dress": "dress",

    "hoodie": "hoodie",
    "cardigan": "cardigan",
    "blazer": "blazer",
    "vest": "vest",
}


CLASSIFIER_TO_UNIFIED = {
    "tshirt": "t-shirt",
    "t-shirt": "t-shirt",
    "tee": "t-shirt",

    "longsleeve": "long-sleeve",
    "long_sleeve": "long-sleeve",

    "tank": "tank-top",
    "tank_top": "tank-top",

    "polo": "polo",
    "blouse": "blouse",

    "jacket": "jacket",
    "hoodie": "hoodie",
    "coat": "coat",

    "short": "shorts",
    "shorts": "shorts",

    "pants": "pants",
    "jeans": "pants",
    "trousers": "pants",

    "dress": "dress",

    "shoes": "shoes",
    "unknown": "unknown",
}


def normalize_category(model_name, raw_category):
    raw = raw_category.lower().strip()

    if model_name == "yolo":
        return YOLO_TO_UNIFIED.get(raw, raw)

    return CLASSIFIER_TO_UNIFIED.get(raw, raw)
# endregion


# region MAIN PIPELINE (detect_all)
def classify_full_image(image_path):
    resp = CLASSIFY_CLIENT.infer(image_path, model_id=CLASSIFIER_MODEL_ID)
    preds = resp.get("predictions", [])
    if not preds:
        return None, 0
    best = max(preds, key=lambda x: x["confidence"])
    return best["class"], best["confidence"]

def detect_all(image_path: str) -> dict:
    """
    Detect clothing category + pattern ONLY.
    All color handling is done by Google Vision in add_item().
    """
    print("🟦 [detect_all] Starting:", image_path)
    from app.services.ocr_service import extract_shirt_text
    shirt_text = extract_shirt_text(image_path)

    # Load full image
    image = Image.open(image_path).convert("RGB")
    img_w, img_h = image.size

    # --- YOLO detection ---
    det = detect_clothing_item(image_path)
    bbox = det.get("bbox")
    raw_yolo_cat = det.get("category")
    yolo_conf = det.get("confidence")

    # --- Classifier ---
    if is_valid_bbox(bbox, img_w, img_h):
        crop_path = crop_for_classification(image, bbox)
        raw_clf_cat, clf_conf = classify_crop(crop_path)
    else:
        print("⚠ [detect_all] Invalid or missing bbox → using full image for classifier + color")
        crop_path = image_path  # <-- IMPORTANT FIX
        raw_clf_cat, clf_conf = classify_full_image(image_path)


    # --- Pick category based on confidence ---
    if clf_conf > yolo_conf:
        chosen_model = "classifier"
        raw_category = raw_clf_cat
        unified_category = normalize_category("classifier", raw_clf_cat)
        chosen_conf = clf_conf
    else:
        chosen_model = "yolo"
        raw_category = raw_yolo_cat
        unified_category = normalize_category("yolo", raw_yolo_cat)
        chosen_conf = yolo_conf

    # -------------------- CATEGORY DEBUG PANEL --------------------
    print("\n==================== CATEGORY DEBUG ====================")
    print(f"🟧 YOLO predicted:          {raw_yolo_cat} (conf={yolo_conf:.3f})")
    print(f"🟦 Classifier predicted:    {raw_clf_cat} (conf={clf_conf:.3f})")
    print(f"🏁 Winner model:            {chosen_model}")
    print(f"🔎 Raw chosen category:     {raw_category}")
    print(f"🎯 Unified category:        {unified_category}")
    print("========================================================\n")

    # --- Pattern detection ---
    if is_valid_bbox(bbox, img_w, img_h):
        pattern = detect_pattern(image, bbox)
    else:
        pattern = "solid"
        # --- COLOR DETECTION (Model 1, Model 2, Vision, Fusion) ---

    # 1. Run Roboflow color models on the cropped image
    print("\n🎨 [detect_all] Running color models…")
    print(f"🎨 crop_path being used: {crop_path}")

    # Use whatever crop_path is set to (safe fallback)
    color6, conf6 = detect_color6(crop_path)
    color14, conf14 = detect_color14(crop_path)


    # 2. Run Google Vision color on the full image
    vision_client = vision.ImageAnnotatorClient()
    with open(image_path, "rb") as img_file:
        content = img_file.read()
    gv_image = vision.Image(content=content)
    gv_resp = vision_client.image_properties(image=gv_image)
    vision_colors = []
    for c in gv_resp.image_properties_annotation.dominant_colors.colors:
        vision_colors.append({
            "r": c.color.red,
            "g": c.color.green,
            "b": c.color.blue,
            "score": c.score,
            "pixel_fraction": c.pixel_fraction
        })

    # 3. Choose final color
    final_color = choose_final_color(
        color6, conf6,
        color14, conf14,
        vision_colors,
        image_path=image_path
    )

    # --- RETURN ONLY CATEGORY + PATTERN ---
    final = {
        # LEGACY FIELD — prevents KeyError in add_item()
        "category": unified_category,

        # FULL CATEGORY DEBUG INFO
        "category_raw_yolo": raw_yolo_cat,
        "category_raw_classifier": raw_clf_cat,
        "category_unified": unified_category,
        "category_model_used": chosen_model,
        "category_confidence": chosen_conf,

        # COLOR + PATTERN + TEXT
        "color": final_color,
        "pattern": pattern,
        "printed_text": shirt_text,
    }

    
    print("✅ Final Output (Google Vision handles color separately):", final)
    return final

# endregion
