"""Tests for the Mergington High School FastAPI application."""

import pytest
from app import activities


class TestRootRedirect:
    """Tests for the root endpoint."""

    def test_root_redirects_to_static_index(self, client):
        """Test that GET / redirects to /static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for the GET /activities endpoint."""

    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        # Should have 9 activities
        assert len(data) == 9
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Basketball Team" in data

    def test_get_activities_returns_correct_structure(self, client, reset_activities):
        """Test that activities have the expected structure"""
        response = client.get("/activities")
        data = response.json()
        
        activity = data["Chess Club"]
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
        
        # Verify participants is a list
        assert isinstance(activity["participants"], list)

    def test_get_activities_includes_initial_participants(self, client, reset_activities):
        """Test that initial participants are included"""
        response = client.get("/activities")
        data = response.json()
        
        # Chess Club should have 2 participants
        assert len(data["Chess Club"]["participants"]) == 2
        assert "michael@mergington.edu" in data["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in data["Chess Club"]["participants"]


class TestSignupForActivity:
    """Tests for the POST /activities/{activity_name}/signup endpoint."""

    def test_signup_success_new_participant(self, client, reset_activities):
        """Test successful signup for a new participant"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu",
            follow_redirects=False
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up newstudent@mergington.edu for Chess Club" in data["message"]

    def test_signup_adds_participant_to_activity(self, client, reset_activities):
        """Test that signup actually adds the participant"""
        client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        
        # Verify participant was added
        assert "newstudent@mergington.edu" in activities["Chess Club"]["participants"]
        assert len(activities["Chess Club"]["participants"]) == 3

    def test_signup_activity_not_found(self, client, reset_activities):
        """Test signup for non-existent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_signup_already_registered(self, client, reset_activities):
        """Test that duplicate signup returns 400"""
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_multiple_different_activities(self, client, reset_activities):
        """Test that same student can signup for multiple activities"""
        # Sign up for Chess Club
        response1 = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response1.status_code == 200
        
        # Sign up for same student in different activity
        response2 = client.post(
            "/activities/Programming Class/signup?email=newstudent@mergington.edu"
        )
        assert response2.status_code == 200
        
        # Verify in both activities
        assert "newstudent@mergington.edu" in activities["Chess Club"]["participants"]
        assert "newstudent@mergington.edu" in activities["Programming Class"]["participants"]

    def test_signup_with_encoded_email(self, client, reset_activities):
        """Test signup with URL-encoded email containing special characters"""
        # Email with plus sign (common in email addresses)
        response = client.post(
            "/activities/Chess Club/signup?email=student%2Bdev@mergington.edu"
        )
        assert response.status_code == 200
        assert "student+dev@mergington.edu" in activities["Chess Club"]["participants"]

    def test_signup_response_format(self, client, reset_activities):
        """Test that signup response has correct format"""
        response = client.post(
            "/activities/Chess Club/signup?email=test@mergington.edu"
        )
        data = response.json()
        assert "message" in data
        assert isinstance(data["message"], str)


class TestUnregisterParticipant:
    """Tests for the POST /activities/{activity_name}/unregister endpoint."""

    def test_unregister_success(self, client, reset_activities):
        """Test successful unregistration"""
        response = client.post(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered michael@mergington.edu from Chess Club" in data["message"]

    def test_unregister_removes_participant(self, client, reset_activities):
        """Test that unregister actually removes the participant"""
        client.post(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        
        # Verify participant was removed
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]
        assert len(activities["Chess Club"]["participants"]) == 1

    def test_unregister_not_found_participant(self, client, reset_activities):
        """Test unregister for non-existent participant"""
        response = client.post(
            "/activities/Chess Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"]

    def test_unregister_not_found_activity(self, client, reset_activities):
        """Test unregister for non-existent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent Club/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_unregister_response_format(self, client, reset_activities):
        """Test that unregister response has correct format"""
        response = client.post(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        data = response.json()
        assert "message" in data
        assert isinstance(data["message"], str)


class TestActivityCapacity:
    """Tests for activity capacity constraints."""

    def test_activities_have_max_participants(self, client, reset_activities):
        """Test that activities have a max_participants field"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "max_participants" in activity_data
            assert isinstance(activity_data["max_participants"], int)
            assert activity_data["max_participants"] > 0

    def test_participant_count_does_not_exceed_max(self, client, reset_activities):
        """Test that participant count never exceeds max_participants"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            participants_count = len(activity_data["participants"])
            max_participants = activity_data["max_participants"]
            assert participants_count <= max_participants
