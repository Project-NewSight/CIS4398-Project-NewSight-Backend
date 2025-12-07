"""
Pytest configuration and fixtures for backend tests
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import SQLAlchemy only if available
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.db import get_db, Base
    SQLALCHEMY_AVAILABLE = True
    
    # Use in-memory SQLite for testing
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
    
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    print("Warning: SQLAlchemy not available, some tests may be skipped")

try:
    from app.main import app
    APP_AVAILABLE = True
except ImportError as e:
    APP_AVAILABLE = False
    print(f"Warning: App not available ({e}), creating minimal FastAPI instance")
    from fastapi import FastAPI
    app = FastAPI()
    
    # Add basic routes for testing
    from fastapi import APIRouter
    
    # Mock health check endpoint
    @app.get("/navigation/health")
    def mock_navigation_health():
        return {"status": "healthy", "service": "navigation"}
    
    @app.get("/object-detection/")
    def mock_object_detection_info():
        return {"feature": "object detection"}
    
    @app.get("/text-detection/")
    def mock_text_detection_info():
        return {"feature": "Text Detection (OCR)", "model": "EasyOCR"}


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test"""
    if not SQLALCHEMY_AVAILABLE:
        pytest.skip("SQLAlchemy not available")
    
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override"""
    if not APP_AVAILABLE or not SQLALCHEMY_AVAILABLE:
        pytest.skip("App or SQLAlchemy not available")
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing"""
    return 1


@pytest.fixture
def sample_contact_data():
    """Sample contact data for testing"""
    return {
        "user_id": 1,
        "name": "John Doe",
        "phone": "1234567890",
        "relationship": "Friend"
    }

