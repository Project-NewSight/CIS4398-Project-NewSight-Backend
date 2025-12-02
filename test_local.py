"""
Local Testing Script for Text Detection
Simple script to test EasyOCR text detection on local images
"""

import os
from text_detection import TextDetector


def create_test_image():
    """Create a simple test image with text"""
    try:
        import cv2
        import numpy as np
        
        # Create test image directory
        os.makedirs('test_images', exist_ok=True)
        
        # Create simple test image
        img = np.ones((300, 500, 3), dtype=np.uint8) * 255
        cv2.putText(img, 'STOP', (150, 150), 
                    cv2.FONT_HERSHEY_BOLD, 3, (0, 0, 0), 5)
        
        output_path = 'test_images/test_stop_sign.jpg'
        cv2.imwrite(output_path, img)
        print(f"✓ Created test image: {output_path}")
        return output_path
    
    except ImportError:
        print("OpenCV not installed. Please install: pip install opencv-python")
        return None


def test_detection(image_path):
    """
    Test text detection on an image
    
    Args:
        image_path: Path to image file
    """
    print("\n" + "=" * 80)
    print("TESTING WITH EasyOCR")
    print("=" * 80)
    
    try:
        # Initialize detector
        detector = TextDetector()
        
        # Get text as string
        print("\n" + "-" * 80)
        print("TEXT OUTPUT:")
        print("-" * 80)
        text_string = detector.get_text_string(image_path)
        print(f"\n>>> '{text_string}'\n")
        
        # Also show detailed results
        results = detector.detect_text(image_path)
        
        print("-" * 80)
        print("DETAILED RESULTS:")
        print("-" * 80)
        
        if not results:
            print("No text detected in the image.")
        else:
            print(f"\nFound {len(results)} text element(s):\n")
            for i, det in enumerate(results, 1):
                print(f"{i}. Text: '{det['text']}'")
                print(f"   Confidence: {det['confidence']:.3f}")
                print()
            
            # Optional: Create visualized output
            save_vis = input("Save annotated image? (y/n): ").strip().lower()
            if save_vis == 'y':
                output_dir = 'test_results'
                os.makedirs(output_dir, exist_ok=True)
                
                filename = os.path.basename(image_path)
                output_path = os.path.join(output_dir, f"result_{filename}")
                
                detector.visualize(image_path, output_path)
                print(f"\n✓ Visualized result saved to: {output_path}")
        
        print("\n" + "=" * 80)
        return True
        
    except ImportError as e:
        print(f"\n✗ Error: {e}")
        print("\nPlease install: pip install easyocr")
        return False
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


def main():
    """Main testing function"""
    print("\n" + "=" * 80)
    print("LOCAL TEXT DETECTION TESTING")
    print("=" * 80)
    
    while True:
        print("\nOptions:")
        print("1. Test with sample image (auto-generated)")
        print("2. Test with your own image")
        print("3. Exit")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == '1':
            # Create and test with sample image
            print("\nCreating sample test image...")
            test_img = create_test_image()
            
            if test_img:
                test_detection(test_img)
        
        elif choice == '2':
            # Test with user's image
            image_path = input("\nEnter path to your image: ").strip()
            
            if not os.path.exists(image_path):
                print(f"✗ Error: File not found: {image_path}")
                continue
            
            test_detection(image_path)
        
        elif choice == '3':
            print("\nExiting...")
            break
        
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    # Check basic requirements
    try:
        import cv2
        import numpy as np
        print("✓ Basic dependencies installed (OpenCV, NumPy)")
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("\nPlease install: pip install opencv-python numpy")
        exit(1)
    
    # Check if EasyOCR is available
    try:
        import easyocr
        print("✓ EasyOCR installed")
    except ImportError:
        print("✗ EasyOCR not installed!")
        print("\nPlease install: pip install easyocr")
        exit(1)
    
    print()
    main()

