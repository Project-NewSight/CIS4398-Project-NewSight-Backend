from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime
import os

from app.db import get_db
from app.models import ClothingItem
from app.schemas import ClothingItemOut
from app.services.s3_service import upload_to_s3
from sqlalchemy import text
from app.services.ocr_service import extract_text_from_image, extract_shirt_text
from app.services.embedding_service import generate_embedding, embedding_to_string, find_closest_item
from app.services.colorcue_service import detect_all
from fastapi import APIRouter
from app.services.recommendation_service import suggest_outfit as suggest_engine
from app.services.ocr_service import extract_shirt_text
from typing import Optional

router = APIRouter(prefix="/colorcue", tags=["Color Cue"])
@router.post("/add_item", response_model=ClothingItemOut)
async def add_item(
    closet_id: int = Form(...),
    genre: str = Form(None),
    notes: str = Form(None),
    style: str = Form(None),

    file_front: UploadFile = File(...),     # Main clothing photo
    tag_side_a: Optional[UploadFile] = File(default=None),    # Tag side A
    tag_side_b: Optional[UploadFile] = File(default=None),    # Tag side B

    db: Session = Depends(get_db)
):
    """
    Upload 3 images (front, tag-side A, tag-side B) → detect color, category, pattern,
    OCR washing/material → embed → save to DB.
    """

    from app.services.google_vision_service import (
        detect_colors,
        is_multicolor,
        pattern_likelihood,
        rgb_to_simple_color,
    )
    from app.services.ocr_service import extract_text_from_image, extract_shirt_text
    from app.services.colorcue_service import detect_all
    from app.services.embedding_service import generate_embedding, embedding_to_string
    from app.services.s3_service import upload_to_s3

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # ------------------------
    # 1. Save all uploaded files temporarily
    # ------------------------
    def save_temp(upload: UploadFile, label: str):
        if not upload:
            return None
        temp_path = f"temp_{label}_{timestamp}_{upload.filename}"
        with open(temp_path, "wb") as f:
            f.write(upload.read() if isinstance(upload.file, bytes) else upload.file.read())
        return temp_path

    # FRONT image
    front_temp = save_temp(file_front, "front")

    # TAG images
    tagA_temp = save_temp(tag_side_a, "tagA")
    tagB_temp = save_temp(tag_side_b, "tagB")

    try:
        # ------------------------
        # 2. Upload images to S3 (store only front image in DB)
        # ------------------------
        front_url = upload_to_s3(
            file_path=front_temp,
            folder="colorcue_img",
            filename=file_front.filename
        )

        tagA_url = upload_to_s3(tagA_temp, "colorcue_img", tag_side_a.filename) if tagA_temp else None
        tagB_url = upload_to_s3(tagB_temp, "colorcue_img", tag_side_b.filename) if tagB_temp else None

        # ------------------------
        # 3. OCR from tag images → fall back to front image
        # ------------------------
        ocr_sources = [p for p in [tagA_temp, tagB_temp] if p]

        material = None
        washing_instructions = None

        if ocr_sources:
            # Merge OCR results from both tag images
            for tag_path in ocr_sources:
                ocr = extract_text_from_image(tag_path)
                if not material and ocr.get("material"):
                    material = ocr["material"]
                if not washing_instructions and ocr.get("washing_instructions"):
                    washing_instructions = ocr["washing_instructions"]
        else:
            # fallback to front image
            ocr = extract_text_from_image(front_temp)
            material = ocr.get("material")
            washing_instructions = ocr.get("washing_instructions")

        # ------------------------
        # 4. Graphic / printed text detection (front only)
        # ------------------------
        printed_text = extract_shirt_text(front_temp)

        # ------------------------
        # 5. Google Vision colors (full image)
        # ------------------------
        gv_colors = detect_colors(front_temp)

        multi = is_multicolor(gv_colors)
        pattern_prob = 1.0 if pattern_likelihood(gv_colors) else 0.0

        sorted_colors = sorted(gv_colors, key=lambda c: c["pixel_fraction"], reverse=True)
        primary = sorted_colors[0]
        primary_simple = rgb_to_simple_color(primary["r"], primary["g"], primary["b"])

        secondary_simple = [
            rgb_to_simple_color(c["r"], c["g"], c["b"])
            for c in sorted_colors[1:3]
        ]

        # ------------------------
        # 6. Run ColorCue pipeline for category/pattern/color
        # ------------------------
        det = detect_all(front_temp)

        detected_category = (
            det.get("category_unified")
            or det.get("category_raw_classifier")
            or det.get("category_raw_yolo")
            or det.get("category")
            or "unknown"
        )

        detected_pattern = det.get("pattern", "solid")
        detected_color = det.get("color") or primary_simple

        # ------------------------
        # 7. Generate vector embedding
        # ------------------------
        embedding = generate_embedding(front_temp)
        embedding_str = embedding_to_string(embedding)

        # ------------------------
        # 8. Save to DB
        # ------------------------
        new_item = ClothingItem(
            closet_id=closet_id,
            category=detected_category,
            color=detected_color,
            material=material,
            style=style,
            genre=genre,
            pattern=detected_pattern,
            washing_instructions=washing_instructions,
            notes=notes,

            # vector embedding
            embedding=embedding,
            embedding_str=embedding_str,

            # image URL stored in closet DB
            image_url=front_url,

            # metadata
            primary_color=primary_simple,
            secondary_colors=",".join(secondary_simple),
            is_multicolor=multi,
            pattern_probability=pattern_prob,
            dominant_colors_json=str(gv_colors),
            printed_text=printed_text,

            # Optional: tag image URLs (add DB column if needed)
            # tag_image_a=tagA_url,
            # tag_image_b=tagB_url,
        )

        db.add(new_item)
        db.commit()
        db.refresh(new_item)

        return new_item

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving item: {str(e)}")

    finally:
        # ------------------------
        # 9. Cleanup temp files
        # ------------------------
        for p in [front_temp, tagA_temp, tagB_temp]:
            if p and os.path.exists(p):
                os.remove(p)


@router.get("/debug/db_user")
def debug_db_user(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT CURRENT_USER;")).fetchone()
    return {"db_user": result[0]}

@router.post("/identify_item")
async def identify_item(
    closet_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Identify an item by comparing the uploaded image to the user's closet.
    """

    # --- Save temp file ---
    temp_path = f"identify_{datetime.now().timestamp()}_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    try:
        # --- 1. Run ColorCue detection (category, color, pattern) ---
        print("\n🟦 [identify_item] Running detect_all()…")
        features = detect_all(temp_path)

        # --- 2. Generate embedding for query item ---
        print("🟦 [identify_item] Generating embedding…")
        query_vector = generate_embedding(temp_path)

        # --- 3. Find closest match in the closet ---
        print("🟦 [identify_item] Searching closet for closest match…")
        closest_item, score = find_closest_item(
            closet_id=closet_id,
            query_vec=query_vector,
            features=features,
            db=db
        )

        # --- 4. Build response ---
        if closest_item:
            item_data = {
                "id": closest_item.item_id,
                "color": closest_item.color,
                "category": closest_item.category,
                "pattern": closest_item.pattern,
                "genre": closest_item.genre,
                "notes": closest_item.notes,
                "image_url": closest_item.image_url,
            }
        else:
            item_data = None

        return {
            "closest_item": item_data,
            "similarity": score,
            "detected_item": features
        }

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)