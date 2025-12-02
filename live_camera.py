"""
Live camera capture script for text detection using the project's TextDetector.

Usage:
  python live_camera.py

Controls while running:
  - q: Quit
  - s: Save current annotated frame to disk

This script uses the default Mac camera (index 0). If you have multiple cameras,
change `camera_index` accordingly.
"""

import argparse
import os
import time
import threading
import queue
import cv2
import numpy as np
from text_detection import TextDetector


def ensure_output_dir(path: str = "live_results"):
    os.makedirs(path, exist_ok=True)
    return path


def main(camera_index=0, save_dir="live_results", frame_skip=5, target_width=640):
    # Initialize detector (gracefully handle missing EasyOCR)
    try:
        detector = TextDetector()
    except ImportError as e:
        print(f"Warning: {e}")
        print("Continuing without OCR — camera feed will display but no text detection will run.")

        class _FallbackDetector:
            def visualize_image(self, image, output_path=None):
                return image

            def get_text_string_from_image(self, image, min_confidence=0.5):
                return ""

        detector = _FallbackDetector()

    # Open camera
    cap = cv2.VideoCapture(camera_index, cv2.CAP_AVFOUNDATION)
    if not cap.isOpened():
        # Try default constructor without backend spec
        cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        print("✗ Could not open camera. Check camera permissions and index.")
        return

    print("✓ Camera opened. Press 'q' to quit, 's' to save an annotated frame.")

    out_dir = ensure_output_dir(save_dir)

    # Threaded OCR worker setup
    ocr_queue = queue.Queue(maxsize=1)
    ocr_result = {"text": "", "annotated": None, "detections": [], "small_size": None}
    stop_event = threading.Event()

    def ocr_worker(detector, q, result_store, stop_event, target_width=640):
        while not stop_event.is_set():
            try:
                frame = q.get(timeout=0.1)
            except queue.Empty:
                continue

            # Resize for faster OCR
            try:
                h, w = frame.shape[:2]
                if w > target_width:
                    scale = target_width / float(w)
                    small = cv2.resize(frame, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
                else:
                    small = frame
            except Exception:
                small = frame

            start = time.time()
            try:
                # Get raw detections (bbox coords relative to `small`)
                detections = detector.detect_text_image(small)
                # Also create a small annotated preview for quick save/preview
                annotated_small = detector.visualize_image(small)
                # Produce joined text string
                text = ' '.join([d['text'] for d in detections if d.get('confidence', 0) >= 0.0])
            except Exception as e:
                detections = []
                text = ""
                annotated_small = small
                print(f"OCR worker error: {e}")
            elapsed_ms = int((time.time() - start) * 1000)
            print(f"OCR worker: Detected: '{text}'  ({elapsed_ms} ms)\n  elems: {len(detections)}")

            # Store detections and small size so main thread can scale bboxes
            result_store["text"] = text
            result_store["annotated"] = annotated_small
            result_store["detections"] = detections
            result_store["small_size"] = (small.shape[1], small.shape[0]) if small is not None else None
            q.task_done()

    worker = threading.Thread(target=ocr_worker, args=(detector, ocr_queue, ocr_result, stop_event, target_width))
    worker.daemon = True
    worker.start()

    frame_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue

            frame_count += 1

            # Display: start with full-resolution frame
            display = frame.copy()

            # If worker returned detections for a small image, scale them to full-res and draw
            detections = ocr_result.get("detections", [])
            small_size = ocr_result.get("small_size")
            if detections and small_size is not None:
                sw, sh = small_size
                fh, fw = frame.shape[:2]
                # Compute scale factors from small -> full
                scale_x = fw / float(sw) if sw else 1.0
                scale_y = fh / float(sh) if sh else 1.0

                for det in detections:
                    bbox = det.get('bbox')
                    text_label = det.get('text', '')
                    confidence = det.get('confidence', 0.0)
                    if bbox is None:
                        continue

                    try:
                        pts = np.array(bbox, dtype=np.float32)
                        # Scale points to full resolution
                        pts[:, 0] = pts[:, 0] * scale_x
                        pts[:, 1] = pts[:, 1] * scale_y
                        pts_int = pts.astype(np.int32)

                        cv2.polylines(display, [pts_int], True, (0, 255, 0), 2)

                        label = f"{text_label} ({confidence:.2f})"
                        org = (int(pts_int[0][0]), max(int(pts_int[0][1]) - 10, 10))
                        cv2.putText(display, label, org, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    except Exception:
                        # skip drawing on error
                        continue

            # Overlay the last detected text (string) as status
            text = ocr_result.get("text", "")
            if text:
                cv2.putText(display, f"Detected: {text}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            cv2.imshow("Live Text Detection", display)

            # Submit frame for OCR every `frame_skip` frames (non-blocking)
            if frame_count % frame_skip == 0:
                try:
                    ocr_queue.put_nowait(frame.copy())
                    print(f"Main: queued frame {frame_count} for OCR")
                except queue.Full:
                    # drop frame if worker is busy
                    print(f"Main: dropped frame {frame_count} (worker busy)")

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Save last annotated result, scaled to full resolution
                detections = ocr_result.get("detections", [])
                small_size = ocr_result.get("small_size")
                if detections and small_size is not None:
                    fh, fw = frame.shape[:2]
                    sw, sh = small_size
                    scale_x = fw / float(sw) if sw else 1.0
                    scale_y = fh / float(sh) if sh else 1.0

                    annotated_full = frame.copy()
                    for det in detections:
                        bbox = det.get('bbox')
                        text_label = det.get('text', '')
                        confidence = det.get('confidence', 0.0)
                        if bbox is None:
                            continue
                        try:
                            pts = np.array(bbox, dtype=np.float32)
                            pts[:, 0] = pts[:, 0] * scale_x
                            pts[:, 1] = pts[:, 1] * scale_y
                            pts_int = pts.astype(np.int32)
                            cv2.polylines(annotated_full, [pts_int], True, (0, 255, 0), 2)
                            label = f"{text_label} ({confidence:.2f})"
                            org = (int(pts_int[0][0]), max(int(pts_int[0][1]) - 10, 10))
                            cv2.putText(annotated_full, label, org, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        except Exception:
                            continue

                    filename = f"frame_{int(time.time())}.jpg"
                    path = os.path.join(out_dir, filename)
                    cv2.imwrite(path, annotated_full)
                    print(f"Saved annotated frame: {path}")
                else:
                    # Fallback: save raw frame
                    filename = f"frame_{int(time.time())}.jpg"
                    path = os.path.join(out_dir, filename)
                    cv2.imwrite(path, frame)
                    print(f"Saved raw frame (no detections): {path}")

    finally:
        stop_event.set()
        worker.join(timeout=1)
        cap.release()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Live camera text detection')
    parser.add_argument('--camera', type=int, default=0, help='Camera index (default: 0)')
    parser.add_argument('--skip', type=int, default=5, help='Process every Nth frame (default: 5)')
    parser.add_argument('--width', type=int, default=640, help='Resize width for OCR (default: 640)')
    parser.add_argument('--out', type=str, default='live_results', help='Output directory')
    args = parser.parse_args()

    main(camera_index=args.camera, save_dir=args.out, frame_skip=args.skip, target_width=args.width)
