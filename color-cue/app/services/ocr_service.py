import os
import re
import traceback
from inference_sdk import InferenceHTTPClient

# -----------------------------------------
# ROBOFLOW WASHING SYMBOL MODEL
# -----------------------------------------
ROBOFLOW_API_KEY = "XkVRQV95oaJhYJsn1wVP"
WASH_MODEL_ID = "washingsymbols/6"

WASH_MODEL = InferenceHTTPClient(
    api_url="https://detect.roboflow.com",
    api_key=ROBOFLOW_API_KEY
)

# EXACT classes your model returns
WASH_SYMBOL_MAP = {
    "30C": "Machine wash cold (30°C)",
    "40C": "Machine wash warm (40°C)",
    "50C": "Machine wash hot (50°C)",
    "60C": "Machine wash hot (60°C)",
    "90C": "Sanitize wash (90°C)",

    "Bleach": "Bleach allowed",
    "DoNotBleach": "Do not bleach",

    "DryClean": "Dry clean only",
    "DoNotDryClean": "Do not dry clean",

    "DryMethod": "Special dry method required",

    "HandWash": "Hand wash only",

    "DoNotWash": "Do not wash",

    "IronLow": "Iron on low heat",
    "IronMedium": "Iron on medium heat",
    "IronHigh": "Iron on high heat",
    "DoNotIron": "Do not iron",

    "TumbleDry": "Tumble dry",
    "DoNotTumbleDry": "Do not tumble dry",
}

# ---------------------------------------------------------
# GOOGLE OCR — TEXT EXTRACTION
# ---------------------------------------------------------

def extract_text_from_image(image_path: str) -> dict:
    """
    Extract text using Google Vision + detect washing symbols with Roboflow.
    Returns:
      - raw_text
      - material
      - washing_text
      - symbols (raw classes)
      - symbol_instructions (human readable)
      - washing_instructions (merged)
    """
    try:
        from google.cloud import vision
        client = vision.ImageAnnotatorClient()

        if not os.path.exists(image_path):
            return {
                "raw_text": "",
                "material": None,
                "washing_text": None,
                "symbols": [],
                "symbol_instructions": [],
                "washing_instructions": None
            }

        # -------------------------------
        # GOOGLE OCR
        # -------------------------------
        with open(image_path, "rb") as f:
            img = vision.Image(content=f.read())

        response = client.text_detection(image=img)

        if response.error.message:
            raw_text = ""
        else:
            raw_text = (
                response.text_annotations[0].description.lower()
                if response.text_annotations else ""
            )

        # Material & wash text parsing
        material_pattern = r"(cotton|polyester|silk|wool|nylon|linen|rayon|spandex|acrylic)"
        washing_pattern = (
            r"(hand wash|machine wash|dry clean|cold water|warm water|"
            r"iron|gentle cycle|line dry|hang dry|tumble dry)"
        )

        material_match = re.search(material_pattern, raw_text)
        washing_text_match = re.search(washing_pattern, raw_text)

        material = material_match.group(0) if material_match else None
        washing_text = washing_text_match.group(0) if washing_text_match else None

        # -------------------------------
        # ROBOFLOW LAUNDRY SYMBOL MODEL
        # -------------------------------
        symbol_preds = []
        symbol_instructions = []

        try:
            rf_resp = WASH_MODEL.infer(image_path, model_id=WASH_MODEL_ID)
            preds = rf_resp.get("predictions", [])

            for p in preds:
                cls = p.get("class")
                symbol_preds.append(cls)

                if cls in WASH_SYMBOL_MAP:
                    symbol_instructions.append(WASH_SYMBOL_MAP[cls])

        except Exception:
            traceback.print_exc()

        # -------------------------------
        # MERGE TEXT + SYMBOL INSTRUCTIONS
        # -------------------------------
        if washing_text and symbol_instructions:
            merged = washing_text + "; " + "; ".join(symbol_instructions)
        elif symbol_instructions:
            merged = "; ".join(symbol_instructions)
        else:
            merged = washing_text

        return {
            "raw_text": raw_text,
            "material": material,
            "washing_text": washing_text,
            "symbols": symbol_preds,
            "symbol_instructions": symbol_instructions,
            "washing_instructions": merged
        }

    except Exception as e:
        traceback.print_exc()
        return {
            "raw_text": "",
            "material": None,
            "washing_text": None,
            "symbols": [],
            "symbol_instructions": [],
            "washing_instructions": None
        }


# ---------------------------------------------------------
# SHIRT FRONT PRINTED TEXT
# ---------------------------------------------------------

def extract_shirt_text(image_path: str) -> str:
    try:
        from google.cloud import vision
        client = vision.ImageAnnotatorClient()

        with open(image_path, "rb") as f:
            img = vision.Image(content=f.read())

        response = client.text_detection(image=img)

        if response.error.message:
            return None

        if not response.text_annotations:
            return None

        printed_text = response.text_annotations[0].description.strip()
        return printed_text

    except Exception:
        traceback.print_exc()
        return None
