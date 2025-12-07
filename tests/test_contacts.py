"""
Test cases for Emergency Contacts API
"""
import pytest
from app.models import EmergencyContact


def test_add_contact(client, sample_contact_data):
    """
    Test: Add emergency contact to database
    Confirm: Contact saved with correct data
    Input: user_id=1, name="John Doe", phone="1234567890"
    Result: Returns 200, contact_id created
    """
    response = client.post("/contacts/", data=sample_contact_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Contact added"
    assert data["contact"]["name"] == "John Doe"
    assert data["contact"]["phone"] == "1234567890"
    assert "id" in data["contact"]


def test_get_contacts(client, db_session, sample_user_id):
    """
    Test: Get all contacts for user
    Confirm: Returns list of user's contacts
    Input: user_id=1
    Result: Returns array of contacts
    """
    # Add test contacts
    contact1 = EmergencyContact(user_id=1, name="John Doe", phone="1111111111")
    contact2 = EmergencyContact(user_id=1, name="Jane Smith", phone="2222222222")
    contact3 = EmergencyContact(user_id=2, name="Bob Jones", phone="3333333333")
    
    db_session.add_all([contact1, contact2, contact3])
    db_session.commit()
    
    response = client.get(f"/contacts/{sample_user_id}")
    
    assert response.status_code == 200
    contacts = response.json()
    assert len(contacts) == 2
    assert contacts[0]["name"] == "John Doe"
    assert contacts[1]["name"] == "Jane Smith"


def test_delete_contact(client, db_session):
    """
    Test: Delete contact by ID
    Confirm: Contact removed from database
    Input: contact_id=5
    Result: Returns "Contact deleted"
    """
    # Add a test contact
    contact = EmergencyContact(user_id=1, name="Test Contact", phone="5555555555")
    db_session.add(contact)
    db_session.commit()
    db_session.refresh(contact)
    
    contact_id = contact.contact_id
    
    response = client.delete(f"/contacts/{contact_id}")
    
    assert response.status_code == 200
    assert response.json()["message"] == "Contact deleted"
    
    # Verify contact is deleted
    deleted_contact = db_session.query(EmergencyContact).filter_by(contact_id=contact_id).first()
    assert deleted_contact is None


def test_delete_nonexistent_contact(client):
    """
    Test: Attempt to delete contact that doesn't exist
    Confirm: Returns 404 error
    Input: contact_id=999
    Result: 404 "Contact not found"
    """
    response = client.delete("/contacts/999")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Contact not found"


def test_add_contact_database_error(client, db_session, monkeypatch):
    """
    Test: Handle database error when adding contact
    Confirm: Returns 500 error with error message
    Input: Valid contact data but DB fails
    Result: 500 error with detail
    """
    def mock_commit_error():
        raise Exception("Database connection lost")
    
    monkeypatch.setattr(db_session, "commit", mock_commit_error)
    
    response = client.post(
        "/contacts/",
        data={
            "user_id": 1,
            "name": "Test User",
            "phone": "1234567890",
            "relationship": "Friend"
        }
    )
    
    assert response.status_code == 500
    assert "Error adding Contact" in response.json()["detail"]
