import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    """Test basic health check endpoint"""
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"

def test_internal_auth_required():
    """Test that internal endpoints require API key"""
    response = client.get("/internal/auth/status/test_user")
    assert response.status_code == 401

def test_with_invalid_api_key():
    """Test with invalid API key"""
    headers = {"X-API-Key": "invalid_key"}
    response = client.get("/internal/auth/status/test_user", headers=headers)
    assert response.status_code == 401