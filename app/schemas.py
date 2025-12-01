from pydantic import BaseModel
from typing import Optional, List

class EmergencyContactOut(BaseModel):
    contact_id: int
    user_id: int
    name: str
    phone: str
    relationship: str
    address: str
    image_url: str | None=None

    class Config:
        orm_mode = True


# ==================== Navigation Models ====================

class LocationCoordinates(BaseModel):
    """GPS coordinates"""
    lat: float
    lng: float


class NavigationStep(BaseModel):
    """Single navigation instruction with location data"""
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


class NavigationUpdate(BaseModel):
    """Real-time navigation update sent via WebSocket"""
    status: str  # "navigating" | "step_completed" | "arrived"
    current_step: int
    total_steps: int
    instruction: str
    distance_to_next: float
    should_announce: bool
    announcement: Optional[str] = None


# ==================== Transit Models ====================
class LocationCoordinates(BaseModel):
    lat: float
    lng: float


class NavigationStep(BaseModel):
    instruction: str
    distance: str
    duration: str
    distance_meters: int
    duration_seconds: int
    start_location: LocationCoordinates
    end_location: LocationCoordinates


class DirectionsResponse(BaseModel):
    status: str
    destination: str
    origin: LocationCoordinates
    total_distance: str
    total_duration: str
    total_distance_meters: int
    total_duration_seconds: int
    steps: List[NavigationStep]
    message: str


class NavigationUpdate(BaseModel):
    status: str
    current_step: int
    total_steps: int
    instruction: str
    distance_to_next: float
    should_announce: bool
    announcement: Optional[str] = None


class DirectionsRequest(BaseModel):
    origin_lat: float
    origin_lng: float
    destination: str


class TransitRoutesRequest(BaseModel):
    origin_lat: float
    origin_lng: float
    destination: str
    mode: str = "all"   # "all", "bus", "train"


class StartNavigationRequest(BaseModel):
    session_id: str
    origin_lat: float
    origin_lng: float
    destination: str


class UpdateLocationRequest(BaseModel):
    session_id: str
    current_lat: float
    current_lng: float


class StopNavigationRequest(BaseModel):
    session_id: str