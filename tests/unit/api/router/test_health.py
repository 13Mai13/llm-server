

def test_health_check(test_client):
    """Test that the health check endpoint returns appropriate status."""
    response = test_client.get("/api/v1/health", headers={"X-API-Key": "test-api-key"})
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == 200
    assert data["description"] == "ok"
    assert "version" in data
