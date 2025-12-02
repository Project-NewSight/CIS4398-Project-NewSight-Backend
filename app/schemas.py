from pydantic import BaseModel, EmailStr
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

# ==================== User Profile =========================

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class Userout(BaseModel):
    id: int
    email: EmailStr

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


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


# ==================== Transit Navigation Models ====================

class TransitStop(BaseModel):
    name: str
    lat: float
    lng: float
    distance_m: int


class TransitLeg(BaseModel):
    type: str  # "walk" or "transit"
    duration_min: Optional[int] = None
    distance_m: Optional[int] = None
    mode_name: Optional[str] = None  # For transit: "Bus", "Train", etc.
    route_short_name: Optional[str] = None  # For transit: "23", "R5", etc.
    route_long_name: Optional[str] = None  # For transit: full route name
    departure_status: Optional[dict] = None  # Status info (on_time, delayed, cancelled)


class TransitOption(BaseModel):
    duration_min: Optional[int] = None
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    legs: List[TransitLeg]


class TransitAlert(BaseModel):
    type: str  # "DELAY", "CANCELLED", etc.
    route: str
    message: str
    delay_minutes: Optional[int] = None


class TransitInfo(BaseModel):
    options: List[TransitOption]
    alerts: List[TransitAlert]
    destination: dict


class TransitNavigationResponse(BaseModel):
    status: str
    navigation_type: str  # "transit"
    destination: str
    nearest_stop: TransitStop
    directions: DirectionsResponse  # Walking directions to stop
    transit_info: TransitInfo
    message: str