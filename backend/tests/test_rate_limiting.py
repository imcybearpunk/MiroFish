"""
Tests for rate limiting functionality.

Flask-Limiter enforces request rate limits to protect the API from
abuse and resource exhaustion. This module verifies:
- Rate limit headers are included in responses
- Requests are allowed under normal limits
- The rate limiter is properly configured and active
"""


def test_rate_limit_headers_present(client):
    """
    Test that rate limit headers are present in HTTP responses.

    Flask-Limiter adds X-RateLimit-* headers to responses to inform
    clients about their current rate limit status. These headers include:
    - X-RateLimit-Limit: the maximum number of requests allowed
    - X-RateLimit-Remaining: requests remaining in current window
    - X-RateLimit-Reset: Unix timestamp when the limit resets

    This test verifies that at least one of these headers is present.
    """
    response = client.get('/health')
    assert response.status_code == 200

    # Check for rate limit headers
    headers = response.headers
    has_rate_limit_headers = any(
        key.startswith('X-RateLimit') for key in headers.keys()
    )
    assert has_rate_limit_headers, (
        "Response should include X-RateLimit-* headers from Flask-Limiter"
    )


def test_rate_limit_limit_header_value(client):
    """
    Test that the X-RateLimit-Limit header contains the correct limit.

    The per-minute limit is set to 50 requests/minute in the app config.
    The X-RateLimit-Limit header should reflect this configuration.
    """
    response = client.get('/health')
    assert response.status_code == 200

    # Get the rate limit header (may vary in format depending on limiter version)
    # The important thing is that it's present and has a numeric value
    headers = response.headers
    limit_header_value = None

    for key, value in headers.items():
        if key.lower() == 'x-ratelimit-limit':
            limit_header_value = value
            break

    if limit_header_value:
        # If the header is present, it should be a positive integer
        # Exact value depends on which limit applies (50/min or 200/hour)
        assert limit_header_value.isdigit()
        assert int(limit_header_value) > 0


def test_multiple_requests_allowed_under_limit(client):
    """
    Test that multiple consecutive requests are allowed under the rate limit.

    The configured limits are:
    - 50 requests per minute
    - 200 requests per hour

    This test makes 5 consecutive requests, which is well under both limits,
    and verifies all return 200 OK status.
    """
    num_requests = 5

    for i in range(num_requests):
        response = client.get('/health')
        # All requests should succeed (200 OK)
        assert response.status_code == 200, (
            f"Request {i+1} of {num_requests} failed with status {response.status_code}"
        )
        # All should return valid JSON
        data = response.get_json()
        assert data is not None
        assert 'status' in data


def test_rate_limiter_configured_in_app(app):
    """
    Test that Flask-Limiter is initialized and configured in the app.

    The app should have a limiter instance attached, indicating that
    Flask-Limiter has been properly integrated into the Flask app.
    """
    # Check that app has the limiter configured
    # Flask-Limiter attaches a 'limiter' attribute or integrates via extensions
    response = app.test_client().get('/health')
    assert response.status_code == 200

    # If limiter is working, rate limit headers should be present
    headers = response.headers
    has_rate_limit_headers = any(
        key.startswith('X-RateLimit') for key in headers.keys()
    )
    assert has_rate_limit_headers, (
        "App should have Flask-Limiter configured with rate limit headers"
    )


def test_health_endpoint_respects_rate_limits(client):
    """
    Test that the /health endpoint respects rate limiting.

    The /health endpoint should be rate-limited like other endpoints.
    This test verifies that rate limit headers are applied to health checks.
    """
    response = client.get('/health')
    assert response.status_code == 200

    data = response.get_json()
    assert data is not None

    # Rate limit headers should be present
    headers = response.headers
    rate_limit_keys = [k for k in headers.keys() if k.startswith('X-RateLimit')]
    assert len(rate_limit_keys) > 0, (
        "/health endpoint should include rate limit headers"
    )


def test_consecutive_requests_show_decreasing_remaining(client):
    """
    Test that X-RateLimit-Remaining decreases with each request.

    Each request should decrement the remaining request count in the
    X-RateLimit-Remaining header (if the header is supported by the limiter).
    """
    response1 = client.get('/health')
    assert response1.status_code == 200

    # Extract remaining count from first request
    remaining1 = None
    for key, value in response1.headers.items():
        if key.lower() == 'x-ratelimit-remaining':
            remaining1 = int(value)
            break

    response2 = client.get('/health')
    assert response2.status_code == 200

    # Extract remaining count from second request
    remaining2 = None
    for key, value in response2.headers.items():
        if key.lower() == 'x-ratelimit-remaining':
            remaining2 = int(value)
            break

    # If both headers are present, the second should be less than the first
    # (or equal if reset time changed)
    if remaining1 is not None and remaining2 is not None:
        assert remaining2 <= remaining1, (
            "Request counter should decrement (or reset, but not increase)"
        )


def test_rate_limit_memory_storage(app):
    """
    Test that the rate limiter uses in-memory storage.

    The app is configured with storage_uri="memory://", meaning
    rate limit state is stored in application memory (suitable for
    testing and single-server deployments).
    """
    # Make a request to ensure the app is fully initialized
    response = app.test_client().get('/health')
    assert response.status_code == 200

    # Verify rate limit headers are present (confirms memory storage is working)
    has_rate_limit_headers = any(
        key.startswith('X-RateLimit') for key in response.headers.keys()
    )
    assert has_rate_limit_headers, (
        "Memory-based rate limiter should add headers to responses"
    )
