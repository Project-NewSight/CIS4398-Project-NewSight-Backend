"""
Navigation Routes for NewSight
API endpoints and WebSocket for real-time turn-by-turn navigation
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from app.services.navigation_service import NavigationService
from app.routes.location_routes import get_user_location
from app.schemas import (
    DirectionsRequest,
    TransitRoutesRequest,
    UpdateLocationRequest,
    DirectionsResponse,
    NavigationUpdate,
)
import json

router = APIRouter(prefix="/navigation", tags=["Navigation"])

# Initialize navigation service
nav_service = NavigationService()

@router.post("/directions", response_model=DirectionsResponse)
async def get_directions(body: DirectionsRequest):
    """
    Get walking directions without starting a full navigation session
    """
    try:
        data = nav_service.get_directions(
            origin_lat=body.origin_lat,
            origin_lng=body.origin_lng,
            destination=body.destination,
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/transit-routes")
async def get_transit_routes(body: TransitRoutesRequest):
    """
    Get transit routes (bus/train) using Transit API + Google Maps
    """
    try:
        data = nav_service.get_transit_routes(
            origin_lat=body.origin_lat,
            origin_lng=body.origin_lng,
            destination=body.destination,
            mode=body.mode,
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/start")
async def start_navigation(request: dict):
    """
    Start navigation session
    
    Called after voice command identifies navigation feature
    Uses stored location from location WebSocket
    
    Request body:
    {
        "session_id": "unique-session-id",
        "destination": "CVS" or "123 Main St"
    }
    
    Optional (if location not in WebSocket storage):
    {
        "session_id": "unique-session-id",
        "destination": "CVS",
        "origin_lat": 39.9812,
        "origin_lng": -75.1556
    }
    
    Response:
    {
        "status": "success",
        "directions": {DirectionsResponse},
        "message": "Navigation started. Connect to /ws/navigation for real-time updates"
    }
    """
    try:
        session_id = request.get("session_id")
        destination = request.get("destination")
        
        if not session_id or not destination:
            raise HTTPException(
                status_code=400,
                detail="Missing session_id or destination"
            )
        
        # Try to get location from WebSocket storage first
        location = get_user_location(session_id)
        
        # If not in storage, check if provided in request
        if not location:
            origin_lat = request.get("origin_lat")
            origin_lng = request.get("origin_lng")
            
            if origin_lat is not None and origin_lng is not None:
                location = {
                    "latitude": origin_lat,
                    "longitude": origin_lng
                }
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Location not found. Either connect to /ws/location first or provide origin_lat/origin_lng"
                )
        
        # Start navigation
        print(f"🚀 Starting navigation: session={session_id}, destination={destination}")
        print(f"📍 Using location: ({location['latitude']}, {location['longitude']})")
        
        directions = nav_service.start_navigation(
            session_id=session_id,
            origin_lat=location["latitude"],
            origin_lng=location["longitude"],
            destination=destination
        )
        
        return {
            "status": "success",
            "directions": directions,
            "message": "Navigation started. Connect to /ws/navigation for real-time updates"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Navigation error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws")
async def websocket_navigation(websocket: WebSocket):
    """
    Real-time navigation WebSocket
    
    Provides turn-by-turn navigation updates as user walks
    Announces proximity to turns and step completions
    
    Flow:
    1. Client connects with session_id in first message
    2. Client continuously sends GPS updates
    3. Server responds with navigation updates and announcements
    
    Client sends:
    {
        "session_id": "unique-session-id",  // First message only
        "latitude": 39.9812,
        "longitude": -75.1556
    }
    
    Server sends:
    {
        "status": "navigating" | "step_completed" | "arrived",
        "current_step": 2,
        "total_steps": 12,
        "instruction": "Turn right onto Main St",
        "distance_to_next": 45.3,
        "should_announce": true,
        "announcement": "In 50 feet, turn right onto Main St"
    }
    """
    await websocket.accept()
    session_id = None
    
    print(f"🗺️  Navigation WebSocket connection accepted")
    
    try:
        # First message should contain session_id
        init_data = await websocket.receive_text()
        init_msg = json.loads(init_data)
        session_id = init_msg.get("session_id")
        
        if not session_id:
            await websocket.send_json({
                "status": "error",
                "message": "session_id required in first message"
            })
            await websocket.close()
            return
        
        print(f"🗺️  Navigation WebSocket connected: {session_id[:8]}...")
        
        # Check if navigation session exists
        if session_id not in nav_service.active_navigations:
            await websocket.send_json({
                "status": "error",
                "message": f"No active navigation for session {session_id}. Call /navigation/start first."
            })
            await websocket.close()
            return
        
        # Send initial confirmation
        nav = nav_service.active_navigations[session_id]
        current_step = nav["steps"][0]
        
        await websocket.send_json({
            "status": "navigation_started",
            "current_step": 1,
            "total_steps": nav["total_steps"],
            "instruction": current_step["instruction"],
            "distance_to_next": current_step["distance_meters"],
            "should_announce": True,
            "announcement": f"Starting navigation. {current_step['instruction']}"
        })
        
        # Main loop - receive location updates and send navigation updates
        while True:
            data = await websocket.receive_text()
            location = json.loads(data)
            
            lat = location.get("latitude")
            lng = location.get("longitude")
            
            if lat is None or lng is None:
                await websocket.send_json({
                    "status": "error",
                    "message": "Missing latitude or longitude"
                })
                continue
            
            # Update navigation state with new location
            nav_update = nav_service.update_location(session_id, lat, lng)
            
            # Send update back to client
            await websocket.send_json(nav_update)
            
            # If arrived, close connection
            if nav_update.get("status") == "arrived":
                print(f"🎯 Navigation completed for session {session_id[:8]}...")
                break
    
    except WebSocketDisconnect:
        print(f"🔌 Navigation WebSocket disconnected: {session_id[:8] if session_id else 'unknown'}...")
        if session_id:
            nav_service.stop_navigation(session_id)
    
    except Exception as e:
        print(f"❌ Error in navigation WebSocket: {str(e)}")
        if session_id:
            nav_service.stop_navigation(session_id)
        try:
            await websocket.send_json({
                "status": "error",
                "message": str(e)
            })
        except:
            pass


@router.post("/stop")
async def stop_navigation(request: dict):
    """
    Stop navigation session
    
    Called when user cancels navigation or manually stops
    
    Request body:
    {
        "session_id": "unique-session-id"
    }
    
    Response:
    {
        "status": "success",
        "message": "Navigation stopped"
    }
    """
    session_id = request.get("session_id")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")
    
    nav_service.stop_navigation(session_id)
    
    return {
        "status": "success",
        "message": "Navigation stopped"
    }


@router.get("/active-sessions")
async def get_active_navigation_sessions():
    """
    Get list of all active navigation sessions (for debugging)
    
    Returns:
        List of active navigation sessions with their status
    """
    sessions = []
    for session_id, nav in nav_service.active_navigations.items():
        sessions.append({
            "session_id": session_id,
            "destination": nav.get("destination"),
            "current_step": nav.get("current_step_index") + 1,
            "total_steps": nav.get("total_steps"),
            "status": nav.get("status")
        })
    
    return {
        "status": "success",
        "active_navigations": len(sessions),
        "sessions": sessions
    }


@router.get("/health")
async def navigation_health_check():
    """
    Health check for navigation service
    
    Returns:
        Status of navigation service and Google Maps API
    """
    return {
        "status": "healthy",
        "service": "navigation",
        "google_maps_configured": nav_service.gmaps is not None,
        "active_navigations": len(nav_service.active_navigations)
    }

