from fastapi import FastAPI, WebSocket
from text_detection import TextDetector
import base64, cv2, numpy as np, json, os, time, re
print("main_ws.py executing...")
app = FastAPI()

# Minimum confidence threshold for returning recognized text
# Configurable via environment variable, e.g. MIN_CONF=0.8
MIN_CONF = float(os.environ.get("MIN_CONF", "0.5"))

# Directory to save raw/annotated frames for debugging
# Note: This is disabled for public repo. Uncomment the two lines below
# to enable saving frames locally for troubleshooting.
# WS_RAW_DIR = os.environ.get("WS_RAW_DIR", "ws_raw")
# os.makedirs(WS_RAW_DIR, exist_ok=True)

detector = TextDetector()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client Connected")
    from collections import deque, Counter

    # Stability parameters (buffer window and required count)
    # STABILITY_WINDOW: how many recent frames to consider
    # STABILITY_COUNT: minimum occurrences of same text in the window to be considered stable
    STABILITY_WINDOW = int(os.environ.get("STABILITY_WINDOW", "5"))
    STABILITY_COUNT = int(os.environ.get("STABILITY_COUNT", "3"))

    # Per-connection buffer of (text, confidence) from last N frames
    recent_buffer = deque(maxlen=STABILITY_WINDOW)
    
    # Track consecutive empty frames to clear buffer
    consecutive_empty_frames = 0
    CLEAR_BUFFER_THRESHOLD = 2  # Clear buffer after 2 consecutive frames with no text (more aggressive)

    while True:
        try:
            msg = await websocket.receive_text()
            data = json.loads(msg)  # <-- Parse JSON from Android

            feature = data.get("feature")
            frame_b64 = data.get("frame")

            if not frame_b64:
                continue

            # Decode base64 into image bytes
            frame_bytes = base64.b64decode(frame_b64)
            print(f"Received frame: {len(frame_bytes)} bytes")

            # Decode into OpenCV image
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                print("Warning: OpenCV failed to decode frame (frame is None)")
            else:
                print(f"Decoded frame shape: {frame.shape}, dtype: {frame.dtype}")

            # OCR
            detections = detector.detect_text_image(frame)

            # Aggregate per-frame words into a reading-ordered phrase
            words = []
            for d in detections:
                txt = d.get("text")
                conf = float(d.get("confidence", 0.0))
                bbox = d.get("bbox")
                if not txt or conf < MIN_CONF:
                    continue

                # Normalize/serialize bbox to int pairs if present
                bbox_serial = None
                if bbox:
                    try:
                        bbox_serial = [[int(p[0]), int(p[1])] for p in bbox]
                    except Exception:
                        bbox_serial = bbox

                # compute a simple top-left coordinate for sorting
                min_x = 0
                min_y = 0
                if bbox_serial:
                    xs = [pt[0] for pt in bbox_serial]
                    ys = [pt[1] for pt in bbox_serial]
                    if xs and ys:
                        min_x = int(min(xs))
                        min_y = int(min(ys))

                words.append({
                    "text": txt,
                    "confidence": conf,
                    "bbox": bbox_serial,
                    "x": min_x,
                    "y": min_y
                })

            # Sort into reading order: top-to-bottom (y bucket), then left-to-right (x)
            words_sorted = sorted(words, key=lambda w: (int(w["y"] / 20), w["x"]))

            # Build full_text and its average confidence for this frame
            full_text = " ".join(w["text"] for w in words_sorted) if words_sorted else ""
            avg_conf = (sum(w["confidence"] for w in words_sorted) / len(words_sorted)) if words_sorted else 0.0

            # Normalize full text for stability comparisons (lowercase, remove punctuation, collapse spaces)
            norm = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", full_text)).strip().lower()

            # Prepare per-frame results payload (reading order)
            per_frame_results = [{"text": w["text"], "confidence": w["confidence"], "bbox": w["bbox"]} for w in words_sorted]

            # (annotated save moved down) -- previously saved every frame with detections

            # Append aggregated normalized full-text + avg confidence to recent buffer
            # Clear buffer if we've had too many consecutive empty frames (resets for new detections)
            if norm:
                recent_buffer.append((norm, avg_conf))
                consecutive_empty_frames = 0  # Reset counter on successful detection
            else:
                consecutive_empty_frames += 1
                if consecutive_empty_frames >= CLEAR_BUFFER_THRESHOLD:
                    if len(recent_buffer) > 0:
                        print(f"  🧹 Clearing buffer after {consecutive_empty_frames} empty frames")
                        recent_buffer.clear()
                    consecutive_empty_frames = 0  # Reset counter
                else:
                    recent_buffer.append(("", 0.0))

            # Compute consensus in recent buffer
            texts = [t for t, c in recent_buffer if t]
            results_filtered = []
            stable_text = None
            if texts:
                counts = Counter(texts)
                most_common, count = counts.most_common(1)[0]
                # average confidence for that text over occurrences
                confs = [c for t, c in recent_buffer if t == most_common]
                avg_conf_buf = sum(confs) / len(confs) if confs else 0.0
                if count >= STABILITY_COUNT and avg_conf_buf >= MIN_CONF:
                    # compute enclosing bbox for the current-frame words (if any)
                    xs = []
                    ys = []
                    for w in per_frame_results:
                        bb = w.get("bbox")
                        if bb:
                            for px, py in bb:
                                xs.append(px); ys.append(py)
                    bbox_enclosing = None
                    if xs and ys:
                        xmin = int(min(xs)); ymin = int(min(ys))
                        xmax = int(max(xs)); ymax = int(max(ys))
                        bbox_enclosing = [[xmin, ymin], [xmax, ymin], [xmax, ymax], [xmin, ymax]]

                    stable_text = most_common
                    results_filtered.append({
                        "text": stable_text,
                        "confidence": avg_conf_buf,
                        "count": count,
                        "bbox": bbox_enclosing
                    })

            # Saving annotated frames to ws_raw is disabled/commented out for public repo.
            # Debugging tip: Uncomment this entire block to save annotated frames
            # when a stable phrase is detected. Files will be written to `WS_RAW_DIR`.
            # try:
            #     if results_filtered:
            #         ts = int(time.time() * 1000)
            #         ann_fname = os.path.join(WS_RAW_DIR, f"stable_annot_{ts}.jpg")
            #         img_annot = frame.copy() if frame is not None else None
            #         if img_annot is not None:
            #             stable_bbox = results_filtered[0].get('bbox')
            #             if stable_bbox:
            #                 try:
            #                     pts = np.array(stable_bbox, dtype=np.int32)
            #                     cv2.polylines(img_annot, [pts], True, (0, 0, 255), 3)
            #                     label = f"STABLE: {results_filtered[0].get('text')} ({results_filtered[0].get('confidence'):.2f})"
            #                     org = (int(pts[0][0]), max(int(pts[0][1]) - 10, 10))
            #                     cv2.putText(img_annot, label, org, cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            #                 except Exception:
            #                     pass
            #             for w in per_frame_results:
            #                 bb = w.get("bbox")
            #                 if bb:
            #                     try:
            #                         pts = np.array(bb, dtype=np.int32)
            #                         cv2.polylines(img_annot, [pts], True, (0, 255, 0), 2)
            #                         label = f"{w.get('text')} ({w.get('confidence'):.2f})"
            #                         org = (int(pts[0][0]), max(int(pts[0][1]) - 10, 10))
            #                         cv2.putText(img_annot, label, org, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            #                     except Exception:
            #                         pass
            #         cv2.imwrite(ann_fname, img_annot)
            #         print(f"Saved annotated STABLE frame to: {ann_fname}")
            # except Exception as _e:
            #     print("Warning: failed to save stable annotated frame:", _e)

            # Determine what text to send to frontend
            text_to_send = stable_text if stable_text else full_text
            
            print(f" {feature}: stable={stable_text} | full={full_text} | sending='{text_to_send}' (buffer={len(recent_buffer)}/{STABILITY_WINDOW}, need={STABILITY_COUNT}, conf>={MIN_CONF})")

            # Send results BACK to Android (include per-frame words + aggregated full_text + stability info)
            # Frontend expects "text_string" and "detections" fields
            response = {
                "text_string": text_to_send,  # Frontend looks for this
                "detections": per_frame_results,  # Frontend looks for this array
                # Keep backward compatibility
                "feature": feature,
                "per_frame_words": per_frame_results,
                "full_text": full_text,
                "results": results_filtered,
                "count": len(results_filtered),
                "stable_text": stable_text
            }
            
            await websocket.send_text(json.dumps(response))
        
        except Exception as e:
            print(" Error:", e)
            break
print("main_ws module loaded")
print("app variable defined:", 'app' in globals())
