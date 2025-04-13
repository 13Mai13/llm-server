def test_auth_success(test_client):
    """Test successful authentication with valid API key."""
    response = test_client.get("/api/v1/health", headers={"X-API-Key": "test-api-key"})
    assert response.status_code == 200


def test_auth_failure(test_client):
    """Test authentication failure with invalid API key."""
    response = test_client.get("/api/v1/health", headers={"X-API-Key": "wrong-api-key"})
    assert response.status_code == 401


def test_auth_missing_key(test_client):
    """Test authentication failure with missing API key."""
    response = test_client.get("/api/v1/health")
    assert response.status_code == 401


def test_auth_query_param(test_client):
    """Test authentication using query parameter."""
    response = test_client.get("/api/v1/health?api_key=test-api-key")
    assert response.status_code == 200
