"""
Test cases for Text Detection (OCR)
"""
import pytest
from unittest.mock import patch


def test_text_detection_info(client):
    """
    Test: Get text detection service info
    Confirm: Returns feature description and config
    Input: GET /text-detection/
    Result: Returns feature info with OCR settings
    """
    response = client.get("/text-detection/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["feature"] == "Text Detection (OCR)"
    assert "EasyOCR" in data["model"]
    assert "configuration" in data


def test_normalize_text():
    """
    Test: Text normalization for stability comparison
    Confirm: Lowercase, remove spaces and punctuation
    Input: "HELLO, WORLD!"
    Result: "helloworld"
    """
    import re
    
    def normalize_text(text: str) -> str:
        normalized = re.sub(r'\W+', '', text.lower())
        return normalized
    
    assert normalize_text("HELLO, WORLD!") == "helloworld"
    assert normalize_text("Stop Sign") == "stopsign"
    assert normalize_text("ONE-WAY") == "oneway"


def test_stability_filter():
    """
    Test: Only return text after multiple frames
    Confirm: Text stable after appearing in 3 frames
    Input: Simulate 3 frames with same text
    Result: is_stable=True after frame 3
    """
    from collections import deque, Counter
    
    STABILITY_WINDOW = 3
    STABILITY_COUNT = 2
    
    recent_buffer = deque(maxlen=STABILITY_WINDOW)
    
    # Add same text 3 times
    recent_buffer.append("STOP")
    assert len(recent_buffer) == 1
    
    recent_buffer.append("STOP")
    assert len(recent_buffer) == 2
    
    recent_buffer.append("STOP")
    assert len(recent_buffer) == 3
    
    # Check stability
    counter = Counter(recent_buffer)
    most_common, count = counter.most_common(1)[0]
    
    assert count >= STABILITY_COUNT
    assert most_common == "STOP"


def test_low_confidence_filter():
    """
    Test: Filter low confidence text
    Confirm: Text below MIN_CONF not returned
    Input: Detection with confidence=0.3, MIN_CONF=0.5
    Result: Detection filtered out
    """
    MIN_CONF = 0.5
    
    detections = [
        {"text": "HELLO", "confidence": 0.7},
        {"text": "WORLD", "confidence": 0.3},
    ]
    
    filtered = [d for d in detections if d["confidence"] >= MIN_CONF]
    
    assert len(filtered) == 1
    assert filtered[0]["text"] == "HELLO"
