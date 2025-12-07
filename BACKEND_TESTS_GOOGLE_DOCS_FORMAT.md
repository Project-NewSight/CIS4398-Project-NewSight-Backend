# Backend API Test Cases

## test_contacts.py:
- **test_add_contact:**
  - Test: Add a valid emergency contact to the database
    - Confirm: Contact is saved with correct user_id, name, and phone number
  - Input: user_id=1, name="John Doe", phone="1234567890"
  - Result: Response status 200, contact created with ID returned

- **test_get_contacts:**
  - Test: Retrieve all emergency contacts for a specific user
    - Confirm: Returns array of contacts belonging to the user
  - Input: user_id = 1
  - Result: List of contacts with correct user_id association

- **test_delete_contact:**
  - Test: Remove an existing contact from the database
    - Confirm: Contact is deleted and no longer retrievable
  - Input: contact_id = 5
  - Result: Response status 200, message "Contact deleted"

- **test_delete_nonexistent_contact:**
  - Test: Attempt to delete a contact that doesn't exist
    - Confirm: Returns 404 error with appropriate message
  - Input: contact_id=999
  - Result: Response status 404, error message "Contact not found"

- **test_add_contact_database_error:**
  - Test: Handle database errors during contact creation
    - Confirm: Returns 500 error when database operation fails
  - Input: Invalid database state
  - Result: Response status 500, error message returned

## test_emergency_alert.py:
- **test_send_alert_with_location:**
  - Test: Send emergency SMS with GPS coordinates to all contacts
    - Confirm: SMS is sent to all emergency contacts with Google Maps link
  - Input: user_id=1, latitude="39.9526", longitude="-75.1652"
  - Result: SMS delivered with message "Emergency! My location: [Google Maps URL]"

- **test_send_alert_with_photo:**
  - Test: Send emergency alert with photo attachment
    - Confirm: Photo is uploaded to S3, URL included in SMS
  - Input: user_id=1, GPS coordinates, photo file
  - Result: Photo uploaded to S3, SMS contains photo URL

- **test_no_contacts_error:**
  - Test: Attempt to send alert for user with no emergency contacts
    - Confirm: Returns 404 error indicating no contacts found
  - Input: user_id=999 (no contacts)
  - Result: Response status 404, message "No emergency contacts found"

## test_sms_routes.py:
- **test_send_sms_success:**
  - Test: Send SMS via Vonage API
    - Confirm: SMS is successfully sent to recipient
  - Input: to_number="1234567890", message="Test message"
  - Result: Response status 200, success confirmation returned

- **test_send_sms_failure:**
  - Test: Handle SMS sending failure
    - Confirm: Returns 500 error when SMS fails to send
  - Input: Invalid phone number or API error
  - Result: Response status 500, error message describing failure

## test_navigation.py:
- **test_get_directions:**
  - Test: Request walking directions from origin to destination
    - Confirm: Returns route with steps, distance, and duration
  - Input: origin="39.9526,-75.1652", destination="Temple University"
  - Result: JSON with steps array, total distance, estimated time (SKIPPED - schema mismatch)

- **test_start_navigation:**
  - Test: Initiate a navigation session with session ID
    - Confirm: Session is created and directions are returned
  - Input: session_id="test-123", destination="CVS"
  - Result: Response status 200, directions and session details returned

- **test_stop_navigation:**
  - Test: End an active navigation session
    - Confirm: Session is terminated successfully
  - Input: session_id="test-123"
  - Result: Response status 200, message "Navigation stopped"

- **test_navigation_missing_session_id:**
  - Test: Attempt to start navigation without session ID
    - Confirm: Returns 400 error for missing required field
  - Input: destination="CVS" (no session_id)
  - Result: Response status 400, error message "session_id required"

- **test_navigation_health_check:**
  - Test: Check navigation service health status
    - Confirm: Service reports healthy status
  - Input: GET /navigation/health
  - Result: Response status 200, {status: "healthy", service: "navigation"}

## test_voice_commands.py:
- **test_wake_word_detection:**
  - Test: Detect wake word "Hey Guide" in audio
    - Confirm: Returns wake_word_detected=True when present
  - Input: Audio file containing "Hey Guide"
  - Result: {wake_word_detected: true}

- **test_no_wake_word:**
  - Test: Process audio without wake word
    - Confirm: Returns wake_word_detected=False
  - Input: Audio "Hello there"
  - Result: {wake_word_detected: false}

- **test_transcribe_audio:**
  - Test: Convert speech to text using Groq Whisper API
    - Confirm: Returns accurate transcription
  - Input: Audio "Take me to CVS"
  - Result: {text: "Take me to CVS"}

- **test_route_navigation_command:**
  - Test: Voice command triggers navigation feature
    - Confirm: LLM identifies NAVIGATION intent and extracts destination
  - Input: Audio "Navigate to Temple"
  - Result: {feature: "NAVIGATION", destination: "Temple"}

- **test_route_emergency_command:**
  - Test: Voice command triggers emergency alert
    - Confirm: LLM identifies EMERGENCY_CONTACT intent
  - Input: Audio "Send emergency alert"
  - Result: {feature: "EMERGENCY_CONTACT"}

- **test_unrecognized_command:**
  - Test: Handle unclear or unrecognized speech
    - Confirm: Returns feature="NONE" with error message
  - Input: Mumbled audio
  - Result: {feature: "NONE", error: "Command not recognized"}

## test_object_detection.py:
- **test_detect_obstacles:**
  - Test: Detect multiple objects (person, car, bicycle) in image frame
    - Confirm: Returns detections with class labels
  - Input: Image containing person and car
  - Result: detections=[{class: "person"}, {class: "car"}] (SKIPPED - YOLO model complexity)

- **test_obstacle_direction:**
  - Test: Identify obstacle position (left/front/right) based on bounding box
    - Confirm: Direction calculated correctly from bbox center
  - Input: Person at center x=0.5
  - Result: {direction: "front"}

- **test_confidence_threshold:**
  - Test: Filter low-confidence detections below threshold
    - Confirm: Only detections >= 0.4 confidence are returned
  - Input: Detection with confidence=0.25
  - Result: Detection excluded from results (SKIPPED - YOLO model complexity)

- **test_object_detection_info:**
  - Test: Get object detection service information
    - Confirm: Returns feature description and status
  - Input: GET /object-detection/
  - Result: Response status 200, service info returned (SKIPPED - endpoint requires YOLO model)

## test_text_detection.py:
- **test_text_detection_info:**
  - Test: Get text detection service information
    - Confirm: Returns feature description and OCR configuration
  - Input: GET /text-detection/
  - Result: Response status 200, OCR settings returned

- **test_normalize_text:**
  - Test: Text normalization for stability comparison
    - Confirm: Converts to lowercase, removes spaces and punctuation
  - Input: "HELLO, WORLD!"
  - Result: "helloworld"

- **test_stability_filter:**
  - Test: Text must appear in multiple consecutive frames to be returned
    - Confirm: Text is stable after appearing in 3 frames
  - Input: Same text detected in 3 consecutive frames
  - Result: {is_stable: true} after frame 3

- **test_low_confidence_filter:**
  - Test: Filter text detections below minimum confidence threshold
    - Confirm: Text with confidence < MIN_CONF is excluded
  - Input: Detection with confidence=0.3, MIN_CONF=0.5
  - Result: Detection filtered out

## test_familiar_face.py:
- **test_face_recognition_websocket:**
  - Test: Establish WebSocket connection for face recognition
    - Confirm: WebSocket accepts connection for real-time face detection
  - Input: WebSocket connection to /ws
  - Result: Connection established (SKIPPED - requires real-time streaming)

- **test_sync_gallery_endpoint:**
  - Test: Sync face gallery from S3 storage
    - Confirm: Downloads all user's face images from S3 folder
  - Input: GET /familiar-face/sync-gallery?user_id=123
  - Result: Response status 200, gallery sync status returned

- **test_face_detection_logic:**
  - Test: Face recognition using DeepFace model
    - Confirm: Returns face match with confidence score
  - Input: Image with known face
  - Result: {match: "John Doe", confidence: 0.95} (SKIPPED - DeepFace model complexity)

- **test_face_gallery_management:**
  - Test: Add and remove faces from user's gallery
    - Confirm: Gallery operations work correctly
  - Input: Add face "John Doe" to user 123's gallery
  - Result: Face stored successfully, retrievable from gallery

## test_location.py:
- **test_get_user_location:**
  - Test: Get user's current GPS coordinates
    - Confirm: Returns valid latitude and longitude
  - Input: GET /location/current
  - Result: {latitude: 39.9526, longitude: -75.1652}

- **test_reverse_geocode:**
  - Test: Convert GPS coordinates to human-readable address
    - Confirm: Returns accurate street address
  - Input: lat=39.9526, lng=-75.1652
  - Result: {address: "Temple University, Philadelphia, PA 19122"}

- **test_location_permission_denied:**
  - Test: Handle GPS permission denial
    - Confirm: Returns 403 error when permission denied
  - Input: User denies location access
  - Result: Response status 403, error "Location permission denied"

- **test_location_accuracy:**
  - Test: GPS accuracy validation
    - Confirm: Rejects locations with accuracy > 100m
  - Input: Location with accuracy=150m
  - Result: Warning issued, accuracy check fails

## test_websocket.py:
- **test_websocket_connection:**
  - Test: Establish WebSocket connection
    - Confirm: Connection successful for real-time communication
  - Input: Connect to /ws
  - Result: Connection established (SKIPPED - requires live connection)

- **test_websocket_face_detection:**
  - Test: Send video frame for face detection via WebSocket
    - Confirm: Receives face detection results
  - Input: Frame with face
  - Result: {match: "John Doe", confidence: 0.92} (SKIPPED - requires live connection)

- **test_websocket_text_detection:**
  - Test: Send video frame for text detection via WebSocket
    - Confirm: Receives OCR results
  - Input: Frame with text "STOP"
  - Result: {text: "STOP", confidence: 0.88} (SKIPPED - requires live connection)

- **test_websocket_message_routing:**
  - Test: Route messages to correct handler based on feature field
    - Confirm: Messages routed to face or text handler correctly
  - Input: {feature: "face"} vs {feature: "text"}
  - Result: Routed to "face_handler" or "text_handler"

- **test_websocket_error_handling:**
  - Test: Handle invalid WebSocket messages gracefully
    - Confirm: Errors don't crash connection, return error message
  - Input: Invalid message format
  - Result: {error: "Missing feature field"}, connection stays open

## test_asl_detection.py:
- **test_asl_predict_letter:**
  - Test: Upload ASL hand sign image for letter prediction
    - Confirm: Returns predicted letter with confidence
  - Input: Image of ASL "A" hand sign
  - Result: {letter: "A", confidence: 0.92} (SKIPPED - requires image processing)

- **test_asl_invalid_image:**
  - Test: Upload non-image file to ASL endpoint
    - Confirm: Returns 400 error for invalid file type
  - Input: .txt file
  - Result: Response status 400, error "Unable to decode image" (SKIPPED - requires image processing)

- **test_asl_no_hand_detected:**
  - Test: Upload image with no hand visible
    - Confirm: Returns null result when no hand detected
  - Input: Empty/background image
  - Result: {letter: null, confidence: null} (SKIPPED - requires image processing)

- **test_asl_letter_mapping:**
  - Test: ASL alphabet letter mapping logic
    - Confirm: Correct letter mapping for prediction indices
  - Input: Prediction index 0 and 25
  - Result: Index 0 = "A", Index 25 = "Z"

- **test_asl_confidence_threshold:**
  - Test: Confidence threshold for ASL predictions
    - Confirm: Low confidence predictions are rejected
  - Input: Prediction with confidence < 0.5
  - Result: Prediction rejected, confidence check fails

## test_color_cue.py:
- **test_colorcue_add_clothing_item:**
  - Test: Upload clothing image with automatic detection
    - Confirm: Item saved with detected color, category, pattern
  - Input: closet_id=1, front_image
  - Result: {item_id: 123, color: "blue", category: "shirt"} (SKIPPED - requires Google Vision API)

- **test_colorcue_color_detection:**
  - Test: RGB to color name conversion logic
    - Confirm: Correct color names returned for RGB values
  - Input: RGB (255, 0, 0) and (0, 0, 255)
  - Result: "red" and "blue"

- **test_colorcue_multicolor_detection:**
  - Test: Detect multi-colored clothing items
    - Confirm: is_multicolor flag set correctly based on color count
  - Input: Image with 2+ dominant colors
  - Result: {is_multicolor: true}

- **test_colorcue_clothing_categories:**
  - Test: Clothing category classification
    - Confirm: Valid categories assigned to items
  - Input: Various clothing types
  - Result: Categories include "shirt", "pants", "dress", "jacket", "shoes"

- **test_colorcue_pattern_detection:**
  - Test: Detect clothing patterns
    - Confirm: Patterns correctly identified
  - Input: Pattern types
  - Result: Valid patterns: "solid", "striped", "checkered", "floral", "polka-dot"

