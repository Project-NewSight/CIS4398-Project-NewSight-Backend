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

import time
from datetime import datetime
import requests

load_dotenv()

# Google Maps API key
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# TransitApp API 
TRANSIT_API_KEY = os.getenv("TRANSIT_API_KEY")
#config for the Transit API
TRANSIT_BASE_URL = "https://external.transitapp.com/v3"
TRANSIT_HEADERS = {
    "apiKey": TRANSIT_API_KEY if TRANSIT_API_KEY else "",
    "Accept": "application/json",
}


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
        api_key = GOOGLE_MAPS_API_KEY
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
    
    
    def get_transit_routes(self, origin_lat: float, origin_lng: float, destination: str, mode: str = "all") -> dict:
        """
        Get transit routes (bus/train) using TransitApp, based on origin + destination string.
        - Uses Google Maps to resolve destination -> coordinates
        - Uses TransitApp to find nearest stop to origin and plan transit trip
        
        Args:
            origin_lat: Starting latitude
            origin_lng: Starting longitude
            destination: Destination name or address
            mode: "all", "bus", or "train"
        
        Returns:
            Dictionary with:
                - origin_stop
                - options (trip options with legs)
                - alerts (delays/cancellations)
                - origin, destination coordinates
        
        Raises:
            Exception if keys not configured or no route found
        """
        if not TRANSIT_API_KEY:
            raise Exception("Transit API key not configured. Please set TRANSIT_API_KEY in .env file")
        if not self.gmaps:
            raise Exception("Google Maps API key not configured. Needed to geocode destination for transit routing.")
        
        # 1) Resolve destination string to final text and coordinates (reusing generic-place logic from google map)
        cleaned_destination = self._clean_destination(destination)
        print(f"🧹 (Transit) Cleaned destination: '{destination}' -> '{cleaned_destination}'")
        final_destination = cleaned_destination
        
        dest_lat: Optional[float] = None
        dest_lng: Optional[float] = None
        
        if self._is_generic_place_name(cleaned_destination):
            print(f"🔍 (Transit) Searching for nearest '{cleaned_destination}'...")
            
            nearest_place = self._find_nearest_place(cleaned_destination, origin_lat, origin_lng, radius=5000)
            if not nearest_place:
                print("(Transit) Expanding radius to 10km...")
                nearest_place = self._find_nearest_place(cleaned_destination, origin_lat, origin_lng, radius=10000)
            
            if nearest_place:
                final_destination = f"{nearest_place['name']}, {nearest_place['address']}"
                loc = nearest_place.get("location", {}) or {}
                dest_lat = loc.get("lat")
                dest_lng = loc.get("lng")
                print(f"✅ (Transit) Found destination place: {nearest_place['name']} at {nearest_place['address']}")
            else:
                raise Exception(f"Could not find any '{cleaned_destination}' near your location for transit routing.")
        
        # If we still don't have coordinates, geocode the final_destination
        if dest_lat is None or dest_lng is None:
            geocode_result = self.gmaps.geocode(final_destination)
            if not geocode_result:
                raise Exception(f"Could not geocode destination '{final_destination}' for transit routing.")
            loc = geocode_result[0]["geometry"]["location"]
            dest_lat = loc["lat"]
            dest_lng = loc["lng"]
            print(f"✅ (Transit) Geocoded destination '{final_destination}' to ({dest_lat}, {dest_lng})")
        
        # 2) Find nearest transit stop to origin point
        nearest_stop = self._transit_get_nearest_stop(origin_lat, origin_lng, mode)
        if not nearest_stop:
            raise Exception("No nearby transit stops found near your location.")
        
        stop_lat = nearest_stop.get("stop_lat")
        stop_lon = nearest_stop.get("stop_lon")
        stop_name = nearest_stop.get("stop_name", "Unknown stop")
        stop_distance = nearest_stop.get("distance", 0)
        
        # 3) Plan transit trip from nearest stop to the destination coordinates
        trip_data = self._transit_plan_trip(stop_lat, stop_lon, dest_lat, dest_lng, mode)
        if not trip_data or not trip_data.get("results"):
            raise Exception("No transit routes found for this destination.")
        
        results = trip_data.get("results", []) or []
        route_ids: Set[str] = set()
        
        # Collect route IDs for alerts (from transit API)
        for trip in results:
            for leg in trip.get("legs", []) or []:
                if leg.get("leg_mode") != "transit":
                    continue
                routes = leg.get("routes", []) or []
                if not routes:
                    continue
                rid = routes[0].get("global_route_id")
                if rid:
                    route_ids.add(rid)
        
        # 4) Fetch service alerts for those routes near origin (from transit API)
        alerts = self._transit_get_service_alerts(route_ids, origin_lat, origin_lng)
        
        # 5) Normalize trip options for frontend consumption
        now_ts = int(time.time())
        normalized_options = []
        
        for trip in results:
            duration_sec = trip.get("duration", 0) or 0
            duration_min = duration_sec // 60 if duration_sec else None
            
            start_time = trip.get("start_time")
            end_time = trip.get("end_time")
            
            legs_out = []
            for leg in trip.get("legs", []) or []:
                leg_mode = leg.get("leg_mode", "unknown")
                leg_duration_min = (leg.get("duration", 0) // 60) if leg.get("duration") else None
                
                if leg_mode == "walk":
                    legs_out.append({
                        "type": "walk",
                        "distance_m": int(leg.get("distance", 0) or 0),
                        "duration_min": leg_duration_min,
                    })
                elif leg_mode == "transit":
                    routes = leg.get("routes", []) or []
                    departures = leg.get("departures", []) or []
                    route_info = routes[0] if routes else {}
                    
                    dep_status = None
                    if departures:
                        dep = departures[0]
                        dep_time = dep.get("departure_time")
                        scheduled_time = dep.get("scheduled_departure_time")
                        is_realtime = dep.get("is_real_time", False)
                        is_cancelled = dep.get("is_cancelled", False)
                        
                        if is_cancelled:
                            dep_status = {"status": "cancelled"}
                        elif is_realtime and dep_time and scheduled_time:
                            delay = (dep_time - scheduled_time) // 60
                            if delay >= 2:
                                dep_status = {"status": "delayed", "delay_min": int(delay)}
                            else:
                                dep_status = {"status": "on_time"}
                        elif is_realtime:
                            dep_status = {"status": "live"}
                    
                    legs_out.append({
                        "type": "transit",
                        "mode_name": route_info.get("mode_name", "Transit"),
                        "route_short_name": route_info.get("route_short_name", ""),
                        "route_long_name": route_info.get("route_long_name", ""),
                        "duration_min": leg_duration_min,
                        "departure_status": dep_status,
                    })
                else:
                    legs_out.append({
                        "type": leg_mode,
                        "duration_min": leg_duration_min,
                    })
            
            normalized_options.append({
                "duration_min": duration_min,
                "start_time": start_time,
                "end_time": end_time,
                "legs": legs_out,
            })
        
        return {
            "origin": {
                "lat": origin_lat,
                "lng": origin_lng,
            },
            "destination": {
                "lat": dest_lat,
                "lng": dest_lng,
                "text": final_destination,
            },
            "origin_stop": {
                "name": stop_name,
                "lat": stop_lat,
                "lng": stop_lon,
                "distance_m": stop_distance,
            },
            "options": normalized_options,
            "alerts": alerts,
            "generated_at": now_ts,
        }
    
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
    

    #=========================
    # Tranist API helpers
    #=========================
    def _transit_get_nearest_stop(self, lat: float, lon: float, transport_mode: str = "all") -> Optional[Dict]:
        """Get the nearest transit stop from a point using TransitApp."""
        if not TRANSIT_API_KEY:
            return None
        
        url = f"{TRANSIT_BASE_URL}/public/nearby_stops"
        
        params = {
            "lat": lat,
            "lon": lon,
            "max_distance": 1500,
        }
        
        try:
            resp = requests.get(url, headers=TRANSIT_HEADERS, params=params, timeout=10)
        except Exception as e:
            print(f"Error calling TransitApp nearby_stops: {e}")
            return None
        
        if resp.status_code != 200:
            print(f"TransitApp nearby_stops error: {resp.status_code}")
            return None
        
        stops = resp.json().get("stops", []) or []
        if not stops:
            return None
        
        if transport_mode == "bus":
            filtered = [s for s in stops if s.get("route_type") == 3]
            if filtered:
                stops = filtered
        elif transport_mode == "train":
            filtered = [s for s in stops if s.get("route_type") in [0, 1, 2]]
            if filtered:
                stops = filtered
        
        return stops[0] if stops else None
    
    def _transit_get_service_alerts(self, route_ids: Set[str], lat: float, lon: float) -> List[Dict]:
        """Get service alerts (delays/cancellations) for a set of route IDs near a point."""
        if not TRANSIT_API_KEY or not route_ids:
            return []
        
        url = f"{TRANSIT_BASE_URL}/public/nearby_routes"
        
        params = {
            "lat": lat,
            "lon": lon,
            "max_distance": 1000,
        }
        
        try:
            resp = requests.get(url, headers=TRANSIT_HEADERS, params=params, timeout=10)
        except Exception as e:
            print(f"Error calling TransitApp nearby_routes for alerts: {e}")
            return []
        
        if resp.status_code != 200:
            print(f"TransitApp nearby_routes error (alerts): {resp.status_code}")
            return []
        
        routes = resp.json().get("routes", []) or []
        alerts: List[Dict] = []
        
        for route in routes:
            if route.get("global_route_id") not in route_ids:
                continue
            
            for itin in route.get("itineraries", []) or []:
                for item in itin.get("schedule_items", []) or []:
                    if item.get("is_cancelled"):
                        alerts.append({
                            "type": "CANCELLED",
                            "route": route.get("route_short_name", ""),
                            "message": f"Service cancelled for {route.get('route_short_name', '')} {route.get('route_long_name', '')}",
                        })
                    elif item.get("is_real_time"):
                        scheduled = item.get("scheduled_departure_time") or 0
                        actual = item.get("departure_time") or 0
                        if actual and scheduled and actual > scheduled:
                            delay_mins = (actual - scheduled) // 60
                            if delay_mins >= 2:
                                alerts.append({
                                    "type": "DELAY",
                                    "route": route.get("route_short_name", ""),
                                    "delay_minutes": int(delay_mins),
                                    "message": f"{route.get('route_short_name', '')} is running {int(delay_mins)} min late",
                                })
        
        return alerts
    
    def _transit_plan_trip(
        self,
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float,
        transport_mode: str = "all",
    ) -> Optional[Dict]:   
        #Flag is there isnt an key for TRANIST_API_KEY
        if not TRANSIT_API_KEY:
            raise Exception("TRANSIT_API_KEY is missing — please set it in the .env file.")
        
        url = f"{TRANSIT_BASE_URL}/public/plan"
        
        params: Dict[str, object] = {
            "from_lat": from_lat,
            "from_lon": from_lon,
            "to_lat": to_lat,
            "to_lon": to_lon,
            "mode": "transit",
            "num_result": 3,
            "should_update_realtime": True,
        }
        
        if transport_mode == "bus":
            params["allowed_modes"] = "Bus"
        elif transport_mode == "train":
            params["allowed_modes"] = "Metro,Subway,Rail,Train,Light Rail,Commuter Rail,Tram"
        
        try:
            resp = requests.get(url, headers=TRANSIT_HEADERS, params=params, timeout=30)
        except Exception as e:
            print(f"Error calling TransitApp plan: {e}")
            return None
        
        if resp.status_code != 0:
            print(f"TransitApp plan error: {resp.status_code}")
            print(resp.text)
            return None
        
        return resp.json()


