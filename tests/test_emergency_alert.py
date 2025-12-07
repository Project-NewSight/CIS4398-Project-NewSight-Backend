"""
Test cases for Emergency Alert System
"""
import pytest
from unittest.mock import patch, MagicMock
from app.models import EmergencyContact


def test_send_alert_with_location(client, db_session):
    """
    Test: Send emergency SMS with GPS coordinates
    Confirm: SMS sent to all contacts with location link
    Input: user_id=1, latitude="39.9526", longitude="-75.1652"
    Result: SMS delivered with Google Maps link
    """
    # Add test contacts
    contact = EmergencyContact(user_id=1, name="John Doe", phone="1234567890")
    db_session.add(contact)
    db_session.commit()
    
    # Mock SMS service
    with patch('app.routes.emergency_alert.send_sms') as mock_sms:
        mock_sms.return_value = {"status": "delivered", "error": None}
        
        response = client.post(
            "/emergency_alert/1",
            data={
                "latitude": "39.9526",
                "longitude": "-75.1652"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Alert sent to your emergency contact"
        assert len(data["results"]) == 1
        assert data["results"][0]["status"] == "delivered"
        
        # Verify SMS was called with location link
        call_args = mock_sms.call_args[0]
        assert "1234567890" in call_args[0]
        assert "39.9526,-75.1652" in call_args[1]


def test_send_alert_with_photo(client, db_session):
    """
    Test: Send alert with uploaded photo
    Confirm: Photo uploaded to S3, URL in SMS
    Input: user_id=1, GPS coords, photo file
    Result: Image uploaded, URL returned, SMS sent
    """
    # Add test contact
    contact = EmergencyContact(user_id=1, name="John Doe", phone="1234567890")
    db_session.add(contact)
    db_session.commit()
    
    # Mock S3 upload and SMS
    with patch('app.routes.emergency_alert.s3_client.upload_fileobj') as mock_s3, \
         patch('app.routes.emergency_alert.send_sms') as mock_sms:
        
        mock_sms.return_value = {"status": "delivered", "error": None}
        
        # Create fake image file
        fake_image = b"fake image data"
        
        response = client.post(
            "/emergency_alert/1",
            data={
                "latitude": "39.9526",
                "longitude": "-75.1652"
            },
            files={"photo": ("test.jpg", fake_image, "image/jpeg")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["photo_included"] is True
        assert "image_url" in data
        assert mock_s3.called


def test_no_contacts_error(client):
    """
    Test: Send alert for user with no contacts
    Confirm: Returns 404 error
    Input: user_id=999
    Result: 404 "No emergency contacts found"
    """
    response = client.post(
        "/emergency_alert/999",
        data={
            "latitude": "39.9526",
            "longitude": "-75.1652"
        }
    )
    
    assert response.status_code == 404
    assert "No emergency contacts found" in response.json()["detail"]
