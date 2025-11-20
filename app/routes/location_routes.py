"""
Location Tracking Routes for NewSight
WebSocket endpoint for continuous background GPS tracking
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Optional
import json

router = APIRouter(prefix="/location", tags=["Location Tracking"])

# In-memory storage for user locations
# Structure: session_id -> {"latitude": float, "longitude": float, "timestamp": int}
user_locations: Dict[str, dict] = {}


@router.websocket("/ws")
async def websocket_location_tracker(websocket: WebSocket):
    """
    WebSocket endpoint for continuous location tracking
    
    Android/Web app connects when launched and sends periodic GPS updates
    Backend stores latest location for each session
    Other services can access location via get_user_location(session_id)
    
    Message format from client:
    {
        "session_id": "unique-session-id",
        "latitude": 39.9812,
        "longitude": -75.1556,
        "timestamp": 1234567890
    }
    
    Response format:
    {
        "status": "received",
        "session_id": "unique-session-id"
    }
    """
    await websocket.accept()
    session_id = None
    
    print(f"📍 Location WebSocket connection accepted")
    
    try:
        while True:
            # Receive location update from client
            data = await websocket.receive_text()
            location_data = json.loads(data)
            
            # Extract session_id and location
            session_id = location_data.get("session_id")
            lat = location_data.get("latitude")
            lng = location_data.get("longitude")
            timestamp = location_data.get("timestamp")
            
            if session_id and lat is not None and lng is not None:
                # Store latest location
                user_locations[session_id] = {
                    "latitude": lat,
                    "longitude": lng,
                    "timestamp": timestamp
                }
                
                print(f"📍 Location updated for {session_id[:8]}...: ({lat:.6f}, {lng:.6f})")
                
                # Acknowledge receipt
                await websocket.send_json({
                    "status": "received",
                    "session_id": session_id
                })
            else:
                # Invalid data
                await websocket.send_json({
                    "status": "error",
                    "message": "Missing session_id or coordinates"
                })
    
    except WebSocketDisconnect:
        # Clean up location when user disconnects
        if session_id:
            user_locations.pop(session_id, None)
            print(f"🔌 Location tracking disconnected: {session_id[:8]}...")
        else:
            print(f"🔌 Location tracking disconnected (unknown session)")
    
    except Exception as e:
        print(f"❌ Error in location WebSocket: {str(e)}")
        if session_id:
            user_locations.pop(session_id, None)


def get_user_location(session_id: str) -> Optional[dict]:
    """
    Retrieve stored location for a session
    
    This function is used by other routes (like navigation) to get user's current location
    without requiring the location to be passed in every request
    
    Args:
        session_id: User's session identifier
    
    Returns:
        Dictionary with latitude, longitude, and timestamp, or None if not found
    """
    return user_locations.get(session_id)


@router.get("/current/{session_id}")
async def get_current_location(session_id: str):
    """
    Get current stored location for a session (for testing/debugging)
    
    Returns:
        Current location data or error if not found
    """
    location = get_user_location(session_id)
    
    if location:
        return {
            "status": "success",
            "session_id": session_id,
            "location": location
        }
    else:
        return {
            "status": "not_found",
            "message": f"No location data for session {session_id}. Make sure location WebSocket is connected."
        }


@router.get("/active-sessions")
async def get_active_sessions():
    """
    Get list of all active location tracking sessions (for debugging)
    
    Returns:
        List of active session IDs and their last update time
    """
    sessions = []
    for session_id, location in user_locations.items():
        sessions.append({
            "session_id": session_id,
            "last_update": location.get("timestamp"),
            "coordinates": {
                "lat": location.get("latitude"),
                "lng": location.get("longitude")
            }
        })
    
    return {
        "status": "success",
        "active_sessions": len(sessions),
        "sessions": sessions
    }

