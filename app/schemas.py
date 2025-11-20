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