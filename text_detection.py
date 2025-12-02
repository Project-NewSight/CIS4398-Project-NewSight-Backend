"""
Text Detection Module for Street Signs
Using EasyOCR for text detection in street sign images
"""

import cv2
import numpy as np
from typing import List, Dict
import os


class TextDetector:
    """
    Simple text detection class for street signs using EasyOCR
    """
    
    def __init__(self, languages=['en'], gpu=False):
        """
        Initialize the text detector with EasyOCR
        
        Args:
            languages: List of language codes (e.g., ['en', 'es'])
            gpu: Whether to use GPU acceleration
        """
        self.languages = languages
        self.gpu = gpu
        self.reader = None
        
        print("Initializing EasyOCR...")
        self._initialize_easyocr()
        print("✓ Detector ready!")
    
    def _initialize_easyocr(self):
        """Initialize EasyOCR"""
        try:
            import easyocr
            self.reader = easyocr.Reader(self.languages, gpu=self.gpu)
        except ImportError:
            raise ImportError(
                "EasyOCR not installed.\n"
                "Install with: pip install easyocr"
            )
    
    def detect_text(self, image_path: str) -> List[Dict]:
        """
        Detect text in an image
        
        Args:
            image_path: Path to the image file
            
        Returns:
            List of dictionaries with 'text', 'confidence', and 'bbox'
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        print(f"\nProcessing: {image_path}")
        
        results = self.reader.readtext(image_path)
        
        detections = []
        for bbox, text, confidence in results:
            detections.append({
                'text': text,
                'confidence': float(confidence),
                'bbox': bbox
            })
        
        return detections
    
    def get_text_string(self, image_path: str, min_confidence: float = 0.5) -> str:
        """
        Get detected text as a single string
        
        Args:
            image_path: Path to the image file
            min_confidence: Minimum confidence threshold (0-1)
            
        Returns:
            Detected text as a single string
        """
        detections = self.detect_text(image_path)
        
        # Filter by confidence and join text
        text_parts = [
            det['text'] 
            for det in detections 
            if det['confidence'] >= min_confidence
        ]
        
        # Join with spaces
        result = ' '.join(text_parts)
        
        print(f"✓ Detected text: '{result}'")
        return result
    
    def visualize(self, image_path: str, output_path: str = None) -> np.ndarray:
        """
        Detect text and draw bounding boxes on the image
        
        Args:
            image_path: Path to input image
            output_path: Path to save annotated image (optional)
            
        Returns:
            Annotated image as numpy array
        """
        # Read image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not read image: {image_path}")
        
        # Detect text
        detections = self.detect_text(image_path)
        
        # Draw results
        for det in detections:
            text = det['text']
            confidence = det['confidence']
            bbox = det['bbox']
            
            if bbox is not None:
                # Convert to integer coordinates
                bbox = np.array(bbox, dtype=np.int32)
                
                # Draw bounding box
                cv2.polylines(image, [bbox], True, (0, 255, 0), 2)
                
                # Draw text label
                label = f"{text} ({confidence:.2f})"
                cv2.putText(
                    image, label,
                    (bbox[0][0], bbox[0][1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (0, 255, 0), 2
                )
        
        # Save if output path provided
        if output_path:
            cv2.imwrite(output_path, image)
            print(f"✓ Saved annotated image: {output_path}")
        
        return image

    def detect_text_image(self, image: np.ndarray) -> List[Dict]:
        """
        Detect text in an image array (numpy.ndarray).

        Args:
            image: BGR image as numpy array (as returned by OpenCV)

        Returns:
            List of dictionaries with 'text', 'confidence', and 'bbox'
        """
        if image is None:
            raise ValueError("Input image is None")

        # EasyOCR expects RGB images when passing ndarray
        try:
            img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        except Exception:
            # If conversion fails, pass image as-is
            img_rgb = image

        results = self.reader.readtext(img_rgb)

        detections = []
        for bbox, text, confidence in results:
            detections.append({
                'text': text,
                'confidence': float(confidence),
                'bbox': bbox
            })

        return detections

    def get_text_string_from_image(self, image: np.ndarray, min_confidence: float = 0.5) -> str:
        """
        Get detected text from an image array as a single string.

        Args:
            image: BGR image as numpy array
            min_confidence: Minimum confidence threshold (0-1)

        Returns:
            Detected text as a single string
        """
        detections = self.detect_text_image(image)

        text_parts = [
            det['text']
            for det in detections
            if det['confidence'] >= min_confidence
        ]

        result = ' '.join(text_parts)
        return result

    def visualize_image(self, image: np.ndarray, output_path: str = None) -> np.ndarray:
        """
        Detect text on an image array and draw bounding boxes.

        Args:
            image: BGR image as numpy array
            output_path: Optional path to save annotated image

        Returns:
            Annotated image as numpy array (BGR)
        """
        if image is None:
            raise ValueError("Input image is None")

        annotated = image.copy()
        detections = self.detect_text_image(image)

        for det in detections:
            text = det['text']
            confidence = det['confidence']
            bbox = det['bbox']

            if bbox is not None:
                bbox = np.array(bbox, dtype=np.int32)
                cv2.polylines(annotated, [bbox], True, (0, 255, 0), 2)

                label = f"{text} ({confidence:.2f})"
                # Put label above the top-left corner of bbox if possible
                org = (int(bbox[0][0]), max(int(bbox[0][1]) - 10, 10))
                cv2.putText(
                    annotated, label,
                    org,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 255, 0), 2
                )

        if output_path:
            cv2.imwrite(output_path, annotated)
            print(f"✓ Saved annotated image: {output_path}")

        return annotated


if __name__ == "__main__":
    print("=" * 80)
    print("TEXT DETECTION MODULE - EasyOCR")
    print("=" * 80)
    print("\nUsage:")
    print("  detector = TextDetector()")
    print("  text = detector.get_text_string('sign.jpg')")
    print("  print(text)  # 'Main Street'")
    print("=" * 80)
