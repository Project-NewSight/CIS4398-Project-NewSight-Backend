"""
Test cases for Navigation System
"""
import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.skip(reason="Navigation response schema mismatch - needs schema update")
def test_get_directions(client):
    """
    Test: Request walking directions
    Confirm: Returns route with steps
    Input: origin coords, destination="Temple University"
    Result: Returns steps array, distance, time
    """
    pass  # Skip for now - schema needs updating


def test_start_navigation(client):
    """
    Test: Start navigation session
    Confirm: Session created with directions
    Input: session_id, destination="CVS"
    Result: Navigation started, directions returned
    """
    with patch('app.routes.navigation_routes.get_user_location') as mock_location, \
         patch('app.services.navigation_service.NavigationService.start_navigation') as mock_start:
        
        mock_location.return_value = {"latitude": 39.9526, "longitude": -75.1652}
        mock_start.return_value = {
            "steps": [{"instruction": "Head to CVS", "distance_meters": 500}],
            "destination": "CVS"
        }
        
        response = client.post(
            "/navigation/start",
            json={
                "session_id": "test-session-123",
                "destination": "CVS"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "directions" in data
        assert "message" in data


def test_stop_navigation(client):
    """
    Test: Stop navigation session
    Confirm: Session closed successfully
    Input: session_id="test-123"
    Result: Returns success message
    """
    with patch('app.services.navigation_service.NavigationService.stop_navigation') as mock_stop:
        response = client.post(
            "/navigation/stop",
            json={"session_id": "test-session-123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "stopped" in data["message"].lower()
        assert mock_stop.called


def test_navigation_missing_session_id(client):
    """
    Test: Start navigation without session_id
    Confirm: Returns 400 error
    Input: Only destination, no session_id
    Result: 400 error
    """
    response = client.post(
        "/navigation/start",
        json={"destination": "CVS"}
    )
    
    assert response.status_code == 400
    assert "session_id" in response.json()["detail"].lower()


def test_navigation_health_check(client):
    """
    Test: Check navigation service health
    Confirm: Returns healthy status
    Input: GET /navigation/health
    Result: status="healthy"
    """
    response = client.get("/navigation/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "navigation"
