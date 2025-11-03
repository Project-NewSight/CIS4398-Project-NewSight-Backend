"""
FastAPI Navigation Server for NewSight
Provides voice-activated navigation with Google Maps integration
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import googlemaps
import os
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="NewSight Navigation API",
    description="Voice-activated navigation service for visually impaired users",
    version="2.0.0"
)

# CORS Configuration - Allow frontend to access API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Google Maps client
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY) if GOOGLE_MAPS_API_KEY else None


# ==================== Data Models ====================

class NavigationRequest(BaseModel):
    """User's navigation request from speech-to-text"""
    request: str


class LocationCoordinates(BaseModel):
    """GPS coordinates"""
    lat: float
    lng: float


class DirectionsRequest(BaseModel):
    """Request for walking directions"""
    origin: LocationCoordinates
    destination: str


class NavigationStep(BaseModel):
    """Single navigation instruction"""
    instruction: str
    distance: str
    duration: str
    distance_meters: int
    duration_seconds: int
    start_location: LocationCoordinates
    end_location: LocationCoordinates


class DirectionsResponse(BaseModel):
    """Complete route with all navigation steps"""
    status: str
    destination: str
    origin: LocationCoordinates
    total_distance: str
    total_duration: str
    total_distance_meters: int
    total_duration_seconds: int
    steps: List[NavigationStep]
    message: str


# ==================== Helper Functions ====================

def extract_destination(text: str) -> str:
    """
    Extract destination from user's voice request
    Handles common patterns like:
    - "directions to [place]"
    - "navigate to [place]"
    - "take me to [place]"
    """
    text = text.lower().strip()
    
    # Common patterns for navigation requests
    patterns = [
        r'(?:give me )?(?:directions?|navigate) (?:to|towards?) (.+)',
        r'take me to (.+)',
        r'how (?:do i|can i) get to (.+)',
        r'(?:go|going) to (.+)',
        r'(?:find|locate) (.+)',
        r'where is (.+)',
        r'to (.+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            destination = match.group(1).strip()
            # Clean up common trailing words
            destination = re.sub(
                r'\s+(please|thanks?|thank you)$', 
                '', 
                destination, 
                flags=re.IGNORECASE
            )
            return destination
    
    # If no pattern matched, return the whole text
    return text


def clean_html_instructions(html_text: str) -> str:
    """Remove HTML tags from Google Maps instructions"""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html_text)
    # Replace common HTML entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    return text.strip()


def find_nearest_place(place_name: str, origin_lat: float, origin_lng: float, radius: int = 5000) -> Optional[Dict]:
    """
    Find the nearest location matching the place name using Google Places API
    
    Args:
        place_name: Name of place to search for (e.g., "CVS", "Starbucks")
        origin_lat: User's current latitude
        origin_lng: User's current longitude
        radius: Search radius in meters (default 5km)
    
    Returns:
        Dictionary with place details or None if not found
    """
    if not gmaps:
        return None
    
    try:
        # Try Places Nearby Search first
        places_result = gmaps.places_nearby(
            location=(origin_lat, origin_lng),
            keyword=place_name,
            radius=radius,
            rank_by=None  # Will rank by prominence within radius
        )
        
        # If no results with nearby, try text search
        if not places_result.get('results'):
            places_result = gmaps.places(
                query=place_name,
                location=(origin_lat, origin_lng),
                radius=radius
            )
        
        if places_result.get('results') and len(places_result['results']) > 0:
            # Get the first (closest/most relevant) result
            nearest = places_result['results'][0]
            
            return {
                'name': nearest.get('name'),
                'address': nearest.get('vicinity') or nearest.get('formatted_address', ''),
                'place_id': nearest.get('place_id'),
                'location': nearest['geometry']['location']
            }
        
        return None
        
    except Exception as e:
        print(f"Error finding nearest place: {e}")
        return None


def is_generic_place_name(destination: str) -> bool:
    """
    Check if the destination is a generic place name that needs nearby search
    """
    # Common generic place types
    generic_terms = [
        'starbucks', 'cvs', 'walgreens', 'mcdonalds', 'walmart', 'target',
        'dunkin', 'subway', 'pizza', 'bank', 'atm', 'gas station', 'pharmacy',
        'grocery store', 'restaurant', 'cafe', 'coffee', 'hospital', 'hotel',
        'gym', 'library', 'post office', 'bar', 'church', 'school', 'park'
    ]
    
    destination_lower = destination.lower().strip()
    
    # Check if it's just a generic term without specific address/location info
    for term in generic_terms:
        if term in destination_lower:
            # Check if it doesn't have specific location indicators
            has_address = any(indicator in destination_lower for indicator in 
                            ['street', 'st', 'avenue', 'ave', 'road', 'rd', 'blvd', 'drive', 'dr'])
            has_numbers = any(char.isdigit() for char in destination)
            
            # If it's generic name without address, return True
            if not has_address and not has_numbers:
                return True
    
    return False


# ==================== API Endpoints ====================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "NewSight Navigation API",
        "version": "2.0.0",
        "status": "running",
        "google_maps_configured": GOOGLE_MAPS_API_KEY is not None
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "navigation-api",
        "google_maps": "configured" if gmaps else "not_configured"
    }


@app.post("/api/navigation/process-request")
async def process_navigation_request(request: NavigationRequest):
    """
    Process user's navigation request and extract destination
    This is Phase 1 - just understanding what user wants
    """
    try:
        user_request = request.request
        
        if not user_request:
            raise HTTPException(status_code=400, detail="No request provided")
        
        # Extract destination from the request
        destination = extract_destination(user_request)
        
        return {
            "status": "success",
            "original_request": user_request,
            "extracted_destination": destination,
            "message": f"I understood that you want directions to: {destination}" 
                if destination else "I couldn't identify a destination in your request."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/navigation/get-directions", response_model=DirectionsResponse)
async def get_directions(request: DirectionsRequest):
    """
    Get walking directions from origin to destination using Google Maps
    Automatically finds nearest location for generic place names (CVS, Starbucks, etc.)
    """
    if not gmaps:
        raise HTTPException(
            status_code=503,
            detail="Google Maps API key not configured. Please set GOOGLE_MAPS_API_KEY in .env file"
        )
    
    try:
        origin_coords = (request.origin.lat, request.origin.lng)
        destination = request.destination
        final_destination = destination
        
        # Check if it's a generic place name (CVS, Starbucks, etc.)
        if is_generic_place_name(destination):
            print(f"🔍 Searching for nearest '{destination}'...")
            
            # Find nearest location
            nearest_place = find_nearest_place(
                destination, 
                request.origin.lat, 
                request.origin.lng,
                radius=5000  # Search within 5km
            )
            
            if nearest_place:
                # Use formatted address or coordinates for more reliable directions
                final_destination = f"{nearest_place['name']}, {nearest_place['address']}"
                print(f"✅ Found: {nearest_place['name']} at {nearest_place['address']}")
                print(f"📍 Using destination: {final_destination}")
            else:
                # If not found nearby, try with city name appended as fallback
                print(f"⚠️  No nearby location found, trying with original query")
        
        # Request directions from Google Maps
        directions = gmaps.directions(
            origin=origin_coords,
            destination=final_destination,
            mode="walking",
            alternatives=False
        )
        
        if not directions:
            raise HTTPException(
                status_code=404,
                detail=f"No walking route found to '{destination}'. Try being more specific with the location."
            )
        
        # Parse the first route
        route = directions[0]
        leg = route['legs'][0]
        
        # Extract all navigation steps
        steps = []
        for step in leg['steps']:
            nav_step = NavigationStep(
                instruction=clean_html_instructions(step['html_instructions']),
                distance=step['distance']['text'],
                duration=step['duration']['text'],
                distance_meters=step['distance']['value'],
                duration_seconds=step['duration']['value'],
                start_location=LocationCoordinates(
                    lat=step['start_location']['lat'],
                    lng=step['start_location']['lng']
                ),
                end_location=LocationCoordinates(
                    lat=step['end_location']['lat'],
                    lng=step['end_location']['lng']
                )
            )
            steps.append(nav_step)
        
        response = DirectionsResponse(
            status="success",
            destination=leg['end_address'],
            origin=request.origin,
            total_distance=leg['distance']['text'],
            total_duration=leg['duration']['text'],
            total_distance_meters=leg['distance']['value'],
            total_duration_seconds=leg['duration']['value'],
            steps=steps,
            message=f"Found route to {leg['end_address']}. {len(steps)} steps total."
        )
        
        return response
        
    except googlemaps.exceptions.ApiError as e:
        raise HTTPException(status_code=503, detail=f"Google Maps API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting directions: {str(e)}")


@app.post("/api/navigation/geocode")
async def geocode_location(location: dict):
    """
    Convert a place name to coordinates
    Useful for finding specific locations
    """
    if not gmaps:
        raise HTTPException(
            status_code=503,
            detail="Google Maps API key not configured"
        )
    
    try:
        place_name = location.get("place")
        if not place_name:
            raise HTTPException(status_code=400, detail="Place name required")
        
        # Geocode the location
        geocode_result = gmaps.geocode(place_name)
        
        if not geocode_result:
            raise HTTPException(
                status_code=404,
                detail=f"Location '{place_name}' not found"
            )
        
        result = geocode_result[0]
        location_coords = result['geometry']['location']
        
        return {
            "status": "success",
            "place": place_name,
            "formatted_address": result['formatted_address'],
            "coordinates": {
                "lat": location_coords['lat'],
                "lng": location_coords['lng']
            }
        }
        
    except googlemaps.exceptions.ApiError as e:
        raise HTTPException(status_code=503, detail=f"Google Maps API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Run Server ====================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 NewSight Navigation Backend Server Starting...")
    print("=" * 60)
    print(f"📍 Server will run on http://localhost:8000")
    print(f"📡 API Documentation: http://localhost:8000/docs")
    print(f"📊 Google Maps API: {'✅ Configured' if gmaps else '⚠️  Not Configured'}")
    print("=" * 60)
    print("\n🔗 Endpoints:")
    print("   - GET  /api/health")
    print("   - POST /api/navigation/process-request")
    print("   - POST /api/navigation/get-directions")
    print("   - POST /api/navigation/geocode")
    print("\n" + "=" * 60)
    print("Press Ctrl+C to stop the server\n")
    
    uvicorn.run(
        "navigation_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
