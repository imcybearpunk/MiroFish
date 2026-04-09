"""
Pytest configuration and shared fixtures for MiroFish backend tests.

This module provides:
- Flask app fixture configured for testing
- Test client fixture for making requests
- Mocked environment variables to avoid requiring real API keys
"""

import os
import sys
import pytest
from unittest.mock import patch
import importlib.util

# Mock environment variables before importing the app
# This prevents errors from missing API keys during fixture setup
TEST_ENV_VARS = {
    'SECRET_KEY': 'test-secret-key-12345',
    'LLM_API_KEY': 'sk-test-mock-key',
    'ZEP_API_KEY': 'test-zep-key',
    'FLASK_DEBUG': 'False',
}


@pytest.fixture
def app():
    """
    Create and configure a Flask test application.

    Returns an app instance with:
    - TESTING=True (disables error catching during request handling)
    - Temporary secret key and fake API keys
    - All blueprints registered at correct prefixes

    Yields the app instance, then cleans up after tests complete.
    """
    # Patch environment variables during app creation
    with patch.dict(os.environ, TEST_ENV_VARS):
        from app import create_app
        from app.config import Config

        # Create test config by loading the standard Config
        # and overriding for testing
        app = create_app(Config)
        app.config['TESTING'] = True

        yield app


@pytest.fixture
def client(app):
    """
    Create a Flask test client.

    The test client allows making requests to the application
    without running a live server, enabling fast unit testing
    of API endpoints.

    Args:
        app: The Flask app fixture

    Returns:
        A Flask test client instance
    """
    return app.test_client()


@pytest.fixture
def app_with_auth():
    """
    Create and configure a Flask test application with API key authentication enabled.

    Returns an app instance with:
    - API_KEY environment variable set to 'test-api-key-secret'
    - TESTING=True
    - All other test environment variables configured

    Yields the app instance, then cleans up after tests complete.
    """
    env_with_auth = {**TEST_ENV_VARS, 'API_KEY': 'test-api-key-secret'}
    with patch.dict(os.environ, env_with_auth):
        from app import create_app
        from app.config import Config

        app = create_app(Config)
        app.config['TESTING'] = True

        yield app


@pytest.fixture
def auth_client(app_with_auth):
    """
    Test client pre-configured with valid API key header.

    Automatically includes the X-API-Key header in all requests
    to simplify testing authenticated endpoints.

    Args:
        app_with_auth: The Flask app fixture with API_KEY enabled

    Returns:
        A wrapper around Flask test client that automatically adds X-API-Key header
    """
    client = app_with_auth.test_client()

    class AuthClient:
        """Wrapper that automatically includes API key in requests."""
        def __init__(self, test_client):
            self._c = test_client

        def get(self, *args, **kwargs):
            kwargs.setdefault('headers', {})['X-API-Key'] = 'test-api-key-secret'
            return self._c.get(*args, **kwargs)

        def post(self, *args, **kwargs):
            kwargs.setdefault('headers', {})['X-API-Key'] = 'test-api-key-secret'
            return self._c.post(*args, **kwargs)

        def put(self, *args, **kwargs):
            kwargs.setdefault('headers', {})['X-API-Key'] = 'test-api-key-secret'
            return self._c.put(*args, **kwargs)

        def delete(self, *args, **kwargs):
            kwargs.setdefault('headers', {})['X-API-Key'] = 'test-api-key-secret'
            return self._c.delete(*args, **kwargs)

        def patch(self, *args, **kwargs):
            kwargs.setdefault('headers', {})['X-API-Key'] = 'test-api-key-secret'
            return self._c.patch(*args, **kwargs)

    return AuthClient(client)
