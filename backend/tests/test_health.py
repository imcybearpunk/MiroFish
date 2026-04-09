"""
Tests for the health check endpoint.

The health endpoint is used by load balancers and monitoring
systems to verify the service is running and responsive.
"""


def test_health_returns_200(client):
    """
    Test that the health endpoint returns HTTP 200 OK.

    A successful health check should return status code 200,
    indicating the service is operational.
    """
    response = client.get('/health')
    assert response.status_code == 200


def test_health_returns_ok_status(client):
    """
    Test that the health endpoint returns 'ok' status.

    The response body should contain a 'status' field set to 'ok',
    confirming the service is healthy.
    """
    response = client.get('/health')
    data = response.get_json()
    assert data['status'] == 'ok'


def test_health_returns_json(client):
    """
    Test that the health endpoint returns valid JSON.

    The response should be properly formatted JSON with both
    'status' and 'service' fields identifying this as MiroFish Backend.
    """
    response = client.get('/health')
    data = response.get_json()
    assert data is not None
    assert 'status' in data
    assert 'service' in data
    assert data['service'] == 'MiroFish Backend'
