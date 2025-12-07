"""
Test cases for SMS Routes
"""
import pytest
from unittest.mock import patch


def test_send_test_sms(client):
    """
    Test: Send test SMS message
    Confirm: SMS sent successfully
    Input: to_number="1234567890", message="Test"
    Result: Returns success message
    """
    with patch('app.routes.sms_routes.send_sms') as mock_sms:
        mock_sms.return_value = {"status": "delivered", "error": None}
        
        response = client.post(
            "/sms/send?to_number=1234567890&message=Test message"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "sucess"  # Note: typo in original code
        assert data["to"] == "1234567890"
        assert mock_sms.called


def test_send_sms_failure(client):
    """
    Test: Handle SMS sending failure
    Confirm: Returns 500 error on exception
    Input: SMS service throws exception
    Result: Returns 500 error
    """
    with patch('app.routes.sms_routes.send_sms') as mock_sms:
        mock_sms.side_effect = Exception("SMS service unavailable")
        
        response = client.post(
            "/sms/send?to_number=1234567890&message=Test"
        )
        
        assert response.status_code == 500
        assert "SMS service unavailable" in response.json()["detail"]
