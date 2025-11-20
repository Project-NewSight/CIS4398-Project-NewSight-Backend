"""
Navigation Service for NewSight
Handles Google Maps integration and real-time navigation logic
"""

from math import radians, sin, cos, sqrt, atan2
from typing import Dict, List, Optional
import googlemaps
import os
import re
from dotenv import load_dotenv
from app.schemas import LocationCoordinates, NavigationStep, DirectionsResponse, NavigationUpdate

load_dotenv()


class NavigationService:
    """
    Core navigation service handling:
    - Google Maps directions
    - Generic place search (CVS, Starbucks, etc.)
    - Real-time navigation tracking
    - Proximity-based announcements
    """
    
    def __init__(self):
        """Initialize Google Maps client and navigation state"""
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        self.gmaps = googlemaps.Client(key=api_key) if api_key else None
        
        # Active navigation sessions: session_id -> navigation state
        self.active_navigations: Dict[str, dict] = {}
    
    
    def get_directions(self, origin_lat: float, origin_lng: float, destination: str) -> dict:
        """
        Get walking directions from origin to destination
        
        Args:
            origin_lat: Starting latitude
            origin_lng: Starting longitude
            destination: Destination name or address
        
        Returns:
            Dictionary with route information and all steps
        
        Raises:
            Exception if Google Maps API not configured or no route found
        """
        if not self.gmaps:
            raise Exception("Google Maps API key not configured. Please set GOOGLE_MAPS_API_KEY in .env file")
        
        origin_coords = (origin_lat, origin_lng)
        
        # Clean destination: remove words like "nearest", "closest", "the", "a"
        cleaned_destination = self._clean_destination(destination)
        print(f"🧹 Cleaned destination: '{destination}' -> '{cleaned_destination}'")
        final_destination = cleaned_destination
        
        # Check if it's a generic place name (CVS, Starbucks, etc.)
        if self._is_generic_place_name(cleaned_destination):
            print(f"🔍 Searching for nearest '{cleaned_destination}'...")
            
            # Find nearest location - try with increasing radius
            nearest_place = self._find_nearest_place(cleaned_destination, origin_lat, origin_lng, radius=5000)
            
            if not nearest_place:
                # Try wider search (10km)
                print(f"🔍 Expanding search radius...")
                nearest_place = self._find_nearest_place(cleaned_destination, origin_lat, origin_lng, radius=10000)
            
            if nearest_place:
                final_destination = f"{nearest_place['name']}, {nearest_place['address']}"
                print(f"✅ Found: {nearest_place['name']} at {nearest_place['address']}")
            else:
                # If still not found, raise helpful error
                raise Exception(f"Could not find any '{cleaned_destination}' near your location. Try searching for a specific address or landmark instead.")
        
        # Get directions from Google Maps
        try:
            directions = self.gmaps.directions(
                origin=origin_coords,
                destination=final_destination,
                mode="walking",
                alternatives=False
            )
        except googlemaps.exceptions.ApiError as e:
            raise Exception(f"Google Maps API error: {str(e)}")
        
        if not directions:
            raise Exception(f"No walking route found to '{destination}'. Try being more specific.")
        
        # Parse the first route
        route = directions[0]
        leg = route['legs'][0]
        
        # Extract all navigation steps
        steps = []
        for step in leg['steps']:
            nav_step = NavigationStep(
                instruction=self._clean_html_instructions(step['html_instructions']),
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
        
        # Build response
        response = DirectionsResponse(
            status="success",
            destination=leg['end_address'],
            origin=LocationCoordinates(lat=origin_lat, lng=origin_lng),
            total_distance=leg['distance']['text'],
            total_duration=leg['duration']['text'],
            total_distance_meters=leg['distance']['value'],
            total_duration_seconds=leg['duration']['value'],
            steps=steps,
            message=f"Found route to {leg['end_address']}. {len(steps)} steps total."
        )
        
        return response.dict()
    
    
    def start_navigation(self, session_id: str, origin_lat: float, origin_lng: float, destination: str) -> dict:
        """
        Initialize navigation session for a user
        
        Args:
            session_id: Unique session identifier
            origin_lat: Starting latitude
            origin_lng: Starting longitude
            destination: Destination name or address
        
        Returns:
            Full route with all navigation steps
        """
        # Get directions from Google Maps
        directions = self.get_directions(origin_lat, origin_lng, destination)
        
        # Store navigation state
        self.active_navigations[session_id] = {
            "destination": directions["destination"],
            "steps": directions["steps"],
            "current_step_index": 0,
            "total_steps": len(directions["steps"]),
            "status": "active",
            "last_announcement": None,
            "last_announced_distance": None
        }
        
        print(f"🗺️  Navigation started for session {session_id}: {directions['destination']}")
        
        return directions
    
    
    def update_location(self, session_id: str, current_lat: float, current_lng: float) -> dict:
        """
        Process user's new location and return navigation update
        
        Args:
            session_id: User's session ID
            current_lat: Current latitude
            current_lng: Current longitude
        
        Returns:
            NavigationUpdate with current status and any announcements
        """
        if session_id not in self.active_navigations:
            return {
                "status": "error",
                "message": "No active navigation for this session"
            }
        
        nav = self.active_navigations[session_id]
        current_step_idx = nav["current_step_index"]
        steps = nav["steps"]
        
        # Check if already arrived
        if current_step_idx >= len(steps):
            self.active_navigations.pop(session_id, None)
            return NavigationUpdate(
                status="arrived",
                current_step=len(steps),
                total_steps=len(steps),
                instruction="You have arrived",
                distance_to_next=0,
                should_announce=True,
                announcement="You have arrived at your destination"
            ).dict()
        
        current_step = steps[current_step_idx]
        
        # Calculate distance to end of current step
        distance_to_step_end = self._haversine_distance(
            current_lat, current_lng,
            current_step["end_location"]["lat"],
            current_step["end_location"]["lng"]
        )
        
        # Check if user completed this step (within 20 meters)
        if distance_to_step_end < 20:
            # Move to next step
            nav["current_step_index"] += 1
            nav["last_announcement"] = None
            nav["last_announced_distance"] = None
            
            if nav["current_step_index"] >= len(steps):
                # Arrived at destination
                self.active_navigations.pop(session_id, None)
                print(f"🎯 Session {session_id} arrived at destination")
                
                return NavigationUpdate(
                    status="arrived",
                    current_step=len(steps),
                    total_steps=len(steps),
                    instruction="You have arrived",
                    distance_to_next=0,
                    should_announce=True,
                    announcement="You have arrived at your destination"
                ).dict()
            
            # Get next step
            next_step = steps[nav["current_step_index"]]
            
            print(f"✅ Session {session_id} completed step {current_step_idx + 1}, moving to step {nav['current_step_index'] + 1}")
            
            return NavigationUpdate(
                status="step_completed",
                current_step=nav["current_step_index"] + 1,
                total_steps=nav["total_steps"],
                instruction=next_step["instruction"],
                distance_to_next=next_step["distance_meters"],
                should_announce=True,
                announcement=f"{next_step['instruction']}"
            ).dict()
        
        # Still on current step - check if should announce proximity
        should_announce = False
        announcement = None
        
        # Announce at specific thresholds: 100m, 50m, 25m
        # Convert meters to feet for more natural announcements
        distance_feet = distance_to_step_end * 3.28084
        
        if distance_to_step_end > 100 and nav["last_announcement"] != "far":
            # Don't announce if far away
            nav["last_announcement"] = "far"
        elif 90 <= distance_to_step_end <= 110 and nav["last_announcement"] != "100m":
            should_announce = True
            if distance_feet < 528:  # Less than 0.1 mile
                announcement = f"In {int(distance_feet)} feet, {current_step['instruction']}"
            else:
                announcement = f"In 100 meters, {current_step['instruction']}"
            nav["last_announcement"] = "100m"
        elif 40 <= distance_to_step_end <= 60 and nav["last_announcement"] != "50m":
            should_announce = True
            announcement = f"In {int(distance_feet)} feet, {current_step['instruction']}"
            nav["last_announcement"] = "50m"
        elif 20 <= distance_to_step_end <= 30 and nav["last_announcement"] != "25m":
            should_announce = True
            announcement = f"In {int(distance_feet)} feet, {current_step['instruction']}"
            nav["last_announcement"] = "25m"
        
        if should_announce:
            print(f"🔊 Session {session_id}: {announcement}")
        
        return NavigationUpdate(
            status="navigating",
            current_step=current_step_idx + 1,
            total_steps=nav["total_steps"],
            instruction=current_step["instruction"],
            distance_to_next=distance_to_step_end,
            should_announce=should_announce,
            announcement=announcement
        ).dict()
    
    
    def stop_navigation(self, session_id: str):
        """
        Stop and clean up navigation session
        
        Args:
            session_id: Session to stop
        """
        if session_id in self.active_navigations:
            self.active_navigations.pop(session_id)
            print(f"🛑 Navigation stopped for session {session_id}")
    
    
    def _haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate distance between two GPS coordinates using Haversine formula
        
        Args:
            lat1, lng1: First coordinate
            lat2, lng2: Second coordinate
        
        Returns:
            Distance in meters
        """
        R = 6371000  # Earth's radius in meters
        
        lat1_rad, lng1_rad = radians(lat1), radians(lng1)
        lat2_rad, lng2_rad = radians(lat2), radians(lng2)
        
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlng/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    
    def _is_generic_place_name(self, destination: str) -> bool:
        """
        Check if destination is a generic place name that needs nearby search
        
        Args:
            destination: Place name to check (should be cleaned and lowercase)
        
        Returns:
            True if generic place name (CVS, Starbucks, etc.)
        """
        generic_terms = [
            # Restaurants & Food
            'starbucks', 'dunkin', 'mcdonalds', 'subway', 'pizza', 'restaurant', 'cafe', 'coffee',
            'burger king', 'taco bell', 'wendys', 'chipotle', 'panera', 'chick-fil-a',
            
            # Retail Stores
            'cvs', 'walgreens', 'walmart', 'target', 'grocery store', 'supermarket',
            'rite aid', '7-eleven', 'wawa', 'convenience store',
            
            # Services
            'bank', 'atm', 'pharmacy', 'post office', 'ups store', 'fedex',
            'gas station', 'auto repair', 'car wash',
            
            # Public Transportation
            'bus stop', 'train station', 'subway station', 'metro station',
            'transit center', 'bus station', 'septa', 
            
            # Healthcare
            'hospital', 'urgent care', 'clinic', 'doctor', 'dentist', 'pharmacy',
            
            # Recreation & Services
            'gym', 'library', 'park', 'playground', 'museum', 'movie theater', 'cinema',
            'hotel', 'motel', 'bar', 'pub', 'nightclub',
            
            # Religious & Education
            'church', 'mosque', 'synagogue', 'temple', 'school', 'university', 'college',
            
            # Other Common Places
            'mall', 'shopping center', 'parking garage', 'parking lot', 'rest area',
            'public restroom', 'bathroom', 'police station', 'fire station'
        ]
        
        destination_lower = destination.lower().strip()
        
        # Check for exact match or if term is contained
        for term in generic_terms:
            if term == destination_lower or term in destination_lower:
                # Check if it doesn't have specific location indicators
                has_address = any(indicator in destination_lower for indicator in 
                                ['street', 'st', 'avenue', 'ave', 'road', 'rd', 'blvd', 'drive', 'dr'])
                has_numbers = any(char.isdigit() for char in destination)
                
                # If it's generic name without address, return True
                if not has_address and not has_numbers:
                    print(f"✅ '{destination}' identified as generic place (matched: '{term}')")
                    return True
        
        print(f"ℹ️  '{destination}' not recognized as generic place - will search as-is")
        return False
    
    
    def _find_nearest_place(self, place_name: str, origin_lat: float, origin_lng: float, 
                           radius: int = 5000) -> Optional[Dict]:
        """
        Find nearest location matching place name using Google Places API
        
        Args:
            place_name: Name of place (e.g., "CVS", "Starbucks")
            origin_lat: User's current latitude
            origin_lng: User's current longitude
            radius: Search radius in meters (default 5km)
        
        Returns:
            Dictionary with place details or None if not found
        """
        if not self.gmaps:
            return None
        
        try:
            # Try Places Nearby Search first (best for generic searches)
            places_result = self.gmaps.places_nearby(
                location=(origin_lat, origin_lng),
                keyword=place_name,
                radius=radius,
                rank_by=None  # Rank by prominence within radius
            )
            
            # If no results, try text search with location bias
            if not places_result.get('results'):
                print(f"🔍 Trying text search for '{place_name}'...")
                places_result = self.gmaps.places(
                    query=f"{place_name} near me",
                    location=(origin_lat, origin_lng),
                    radius=radius
                )
            
            # Check if we got any results
            if places_result.get('results') and len(places_result['results']) > 0:
                nearest = places_result['results'][0]
                
                print(f"📍 Found {len(places_result['results'])} results, using closest: {nearest.get('name')}")
                
                return {
                    'name': nearest.get('name'),
                    'address': nearest.get('vicinity') or nearest.get('formatted_address', ''),
                    'place_id': nearest.get('place_id'),
                    'location': nearest['geometry']['location']
                }
            
            print(f"⚠️  No results found for '{place_name}' within {radius}m")
            return None
            
        except Exception as e:
            print(f"Error finding nearest place: {e}")
            return None
    
    
    def _clean_html_instructions(self, html_text: str) -> str:
        """
        Remove HTML tags from Google Maps instructions
        
        Args:
            html_text: HTML instruction text from Google Maps
        
        Returns:
            Clean text without HTML tags
        """
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_text)
        # Replace common HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        return text.strip()
    
    
    def _clean_destination(self, destination: str) -> str:
        """
        Clean destination string by removing common filler words and punctuation
        
        Args:
            destination: Raw destination string
        
        Returns:
            Cleaned destination string
        
        Examples:
            "Nearest Starbucks." -> "starbucks"
            "the closest CVS!" -> "cvs"
            "a Walmart near me" -> "walmart"
        """
        # Remove trailing punctuation first
        cleaned = destination.strip().rstrip('.!?,;:')
        
        # Convert to lowercase
        cleaned = cleaned.lower()
        
        # Words to remove
        filler_words = [
            'nearest', 'closest', 'nearby', 'near me', 'close by',
            'the', 'a', 'an', 'my', 'some', 'please', 'find', 'locate'
        ]
        
        # Remove filler words
        for word in filler_words:
            # Use word boundaries to avoid removing parts of words
            pattern = r'\b' + re.escape(word) + r'\b'
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Clean up extra spaces
        cleaned = ' '.join(cleaned.split()).strip()
        
        return cleaned if cleaned else destination.lower()

