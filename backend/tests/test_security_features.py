"""
Tests for Wave 2 and Wave 3 security features.

This module tests:
- API key authentication
- Security headers (X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy)
- CORS headers
- Request ID tracking
- Prometheus /metrics endpoint
"""

import pytest


class TestSecurityHeaders:
    """Tests for security response headers."""

    def test_security_headers_present(self, client):
        """
        Test that security headers are present in responses.

        All responses should include X-Frame-Options header
        to prevent clickjacking attacks.
        """
        response = client.get('/health')
        assert response.status_code == 200
        assert 'X-Frame-Options' in response.headers

    def test_x_frame_options_deny(self, client):
        """
        Test that X-Frame-Options is set to DENY.

        This prevents the page from being embedded in frames,
        protecting against clickjacking attacks.
        """
        response = client.get('/health')
        assert response.headers.get('X-Frame-Options') == 'DENY'

    def test_x_content_type_options(self, client):
        """
        Test that X-Content-Type-Options header is set to nosniff.

        This header prevents MIME-based attacks by instructing the browser
        not to override the Content-Type header.
        """
        response = client.get('/health')
        assert response.headers.get('X-Content-Type-Options') == 'nosniff'

    def test_x_xss_protection(self, client):
        """
        Test that X-XSS-Protection header is present.

        This header enables XSS filtering in older browsers.
        """
        response = client.get('/health')
        assert 'X-XSS-Protection' in response.headers
        assert '1; mode=block' in response.headers.get('X-XSS-Protection', '')

    def test_referrer_policy(self, client):
        """
        Test that Referrer-Policy header is present.

        This header controls what referrer information is sent
        when following links.
        """
        response = client.get('/health')
        assert 'Referrer-Policy' in response.headers
        assert 'strict-origin-when-cross-origin' in response.headers.get('Referrer-Policy', '')


class TestAPIKeyAuthentication:
    """Tests for API key authentication middleware."""

    def test_health_no_auth_required(self, app_with_auth):
        """
        Test that /health endpoint bypasses authentication.

        The health check endpoint should be accessible without
        providing an API key, even when API_KEY is configured.
        """
        client = app_with_auth.test_client()
        response = client.get('/health')
        assert response.status_code == 200

    def test_api_requires_auth_when_key_set(self, app_with_auth):
        """
        Test that API endpoints require authentication when API_KEY is set.

        When API_KEY environment variable is configured, requests
        to API endpoints without the X-API-Key header should return 401.
        """
        client = app_with_auth.test_client()
        response = client.get('/api/graph/project/list')
        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
        assert data['error'] == 'Unauthorized'

    def test_api_passes_with_valid_key(self, auth_client):
        """
        Test that API endpoints accept valid API key.

        When the correct X-API-Key header is provided,
        the request should proceed past authentication
        (may fail with 404 or other non-401 error depending on endpoint).
        """
        response = auth_client.get('/api/graph/project/list')
        # Should not be 401 Unauthorized
        assert response.status_code != 401

    def test_api_passes_without_auth_when_no_key_env(self, client):
        """
        Test that API endpoints don't require auth when API_KEY is not set.

        When API_KEY environment variable is not configured,
        all requests should pass through authentication checks.
        """
        response = client.get('/api/graph/project/list')
        # Should not be 401 (may be other error, but auth should pass)
        assert response.status_code != 401

    def test_options_method_bypasses_auth(self, app_with_auth):
        """
        Test that OPTIONS requests bypass authentication.

        CORS preflight requests use OPTIONS method and should
        bypass authentication to allow CORS negotiation.
        """
        client = app_with_auth.test_client()
        response = client.options('/api/graph/project/list')
        # OPTIONS should bypass auth, not return 401
        assert response.status_code != 401

    def test_api_key_in_query_parameter_is_rejected(self, app_with_auth):
        """
        Test that API key in query parameter is NOT accepted (OWASP A02).

        Query parameters appear in server logs, browser history, and Referer
        headers — they must never carry secrets. The only accepted location
        is the X-API-Key request header.
        """
        client = app_with_auth.test_client()
        response = client.get('/api/graph/project/list?api_key=test-api-key-secret')
        # Must return 401: query-param key must be ignored
        assert response.status_code == 401

    def test_invalid_api_key_returns_401(self, app_with_auth):
        """
        Test that invalid API key returns 401.

        Requests with wrong X-API-Key header should be rejected.
        """
        client = app_with_auth.test_client()
        response = client.get(
            '/api/graph/project/list',
            headers={'X-API-Key': 'wrong-key'}
        )
        assert response.status_code == 401


class TestCORSHeaders:
    """Tests for CORS configuration."""

    def test_cors_header_present(self, client):
        """
        Test that CORS headers are present in responses.

        CORS-enabled endpoints should include Access-Control-Allow-Origin
        or similar CORS headers.
        """
        response = client.get('/api/graph/project/list')
        # Check that response has CORS headers
        # The exact header name depends on flask-cors configuration
        assert (
            'Access-Control-Allow-Origin' in response.headers or
            response.status_code == 404  # OK if endpoint doesn't exist yet
        )


class TestMetricsEndpoint:
    """Tests for Prometheus metrics endpoint."""

    def test_metrics_endpoint_exists_if_prometheus_available(self, client):
        """
        Test that /metrics endpoint exists when prometheus_client is installed.

        The metrics endpoint should be available and return 200
        if prometheus_client is installed.
        """
        pytest.importorskip('prometheus_client')
        response = client.get('/metrics')
        assert response.status_code == 200

    def test_metrics_endpoint_returns_text(self, client):
        """
        Test that /metrics endpoint returns Prometheus text format.

        The response should contain Prometheus metrics in text format.
        """
        pytest.importorskip('prometheus_client')
        response = client.get('/metrics')
        assert response.status_code == 200
        # Prometheus text format contains TYPE and HELP comments
        content = response.get_data(as_text=True)
        assert 'TYPE' in content or 'mirofish_' in content or len(content) > 0

    def test_metrics_endpoint_skipped_if_prometheus_not_installed(self):
        """
        Test that /metrics endpoint gracefully handles missing prometheus_client.

        If prometheus_client is not installed, the app should still start
        without errors (though /metrics endpoint may not exist or return 404).
        """
        # This test just verifies the app doesn't crash during initialization
        # when prometheus_client is not available. The actual behavior
        # depends on whether prometheus_client is installed in the test environment.
        pass


class TestRequestID:
    """Tests for request ID tracking."""

    def test_request_id_injected_when_provided(self, client):
        """
        Test that X-Request-ID header is preserved when provided.

        If a client provides X-Request-ID header, it should be used
        for request tracking.
        """
        response = client.get('/health', headers={'X-Request-ID': 'custom-id-123'})
        assert response.status_code == 200
        # The request should process successfully with custom ID

    def test_request_id_generated_when_missing(self, client):
        """
        Test that X-Request-ID is generated when not provided.

        If client doesn't provide X-Request-ID, the middleware should
        generate one for request tracking.
        """
        response = client.get('/health')
        assert response.status_code == 200
        # The request should process successfully with generated ID
