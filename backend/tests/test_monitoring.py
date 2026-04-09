"""
Tests for monitoring and observability features.

This module tests:
- Sentry error tracking initialization
- Health endpoint enhancements (version, config validation)
- Configuration warnings in health responses
"""

import os
import pytest
from unittest.mock import patch

import sentry_sdk


def test_health_has_version_field(client):
    """
    Test that the health endpoint response includes a version field.

    The version field identifies the current API version and helps with
    client compatibility checks and debugging.
    """
    response = client.get('/health')
    data = response.get_json()
    assert 'version' in data
    assert data['version'] == '0.1.0'


def test_health_ok_when_config_valid(client):
    """
    Test that health status is 'ok' when all required env vars are set.

    When LLM_API_KEY, ZEP_API_KEY, and other required configuration
    are present and valid, the health endpoint should report status 'ok'.
    """
    response = client.get('/health')
    data = response.get_json()
    assert data['status'] == 'ok'
    assert data['service'] == 'MiroFish Backend'


def test_health_degraded_when_missing_keys():
    """
    Test that health status is 'degraded' when required env vars are missing.

    When critical API keys are missing (LLM_API_KEY or ZEP_API_KEY),
    the health endpoint should return status 'degraded' and include
    warnings in the config_warnings field.

    This test creates a new app instance with minimal environment
    to simulate production failures.
    """
    from app import create_app
    from app.config import Config

    # Create a minimal environment without critical API keys
    minimal_env = {
        'SECRET_KEY': 'test-secret-key',
        'FLASK_DEBUG': 'False',
    }

    with patch.dict(os.environ, minimal_env, clear=True):
        app = create_app(Config)
        app.config['TESTING'] = True
        test_client = app.test_client()

        response = test_client.get('/health')
        data = response.get_json()

        # Should report degraded status when keys are missing
        assert data['status'] == 'degraded'
        assert data['service'] == 'MiroFish Backend'
        # config_warnings should contain reported issues
        assert isinstance(data['config_warnings'], list)
        assert len(data['config_warnings']) > 0


def test_health_config_warnings_empty_when_valid(client):
    """
    Test that config_warnings is empty when all configuration is valid.

    The config_warnings field should be an empty list [] when all
    required environment variables are properly configured.
    """
    response = client.get('/health')
    data = response.get_json()
    assert 'config_warnings' in data
    assert isinstance(data['config_warnings'], list)
    # With valid config (from test fixtures), warnings should be empty
    assert len(data['config_warnings']) == 0


def test_sentry_not_initialized_without_dsn():
    """
    Test that Sentry is not initialized when SENTRY_DSN is not set.

    When the SENTRY_DSN environment variable is not configured,
    Sentry initialization should be skipped. This is verified by
    checking that sentry_sdk.get_client() returns None.

    The app should start normally without Sentry, allowing graceful
    degradation when error tracking is not available.
    """
    from app import create_app
    from app.config import Config

    # Create environment without SENTRY_DSN
    env_without_sentry = {
        'SECRET_KEY': 'test-secret-key-12345',
        'LLM_API_KEY': 'sk-test-mock-key',
        'ZEP_API_KEY': 'test-zep-key',
        'FLASK_DEBUG': 'False',
    }

    with patch.dict(os.environ, env_without_sentry, clear=True):
        app = create_app(Config)

        # Get the current Sentry client
        current_client = sentry_sdk.get_client()

        # When SENTRY_DSN is not set, the client should be None
        # or the hub should not have an active client
        # (depends on sentry_sdk version; we check both)
        if current_client is not None:
            # If there's a client, it should not have a DSN
            # (it's a no-op client)
            assert current_client.dsn is None or str(current_client.dsn) == 'None'


def test_health_returns_degraded_status_field():
    """
    Test that health endpoint can return 'degraded' status.

    The status field should only contain 'ok' or 'degraded' values,
    and 'degraded' is used when config validation fails.
    """
    from app import create_app
    from app.config import Config

    minimal_env = {
        'SECRET_KEY': 'test-secret-key',
        'FLASK_DEBUG': 'False',
    }

    with patch.dict(os.environ, minimal_env, clear=True):
        app = create_app(Config)
        app.config['TESTING'] = True
        test_client = app.test_client()

        response = test_client.get('/health')
        data = response.get_json()

        # Status should be one of the valid values
        assert data['status'] in ['ok', 'degraded']


def test_health_endpoint_response_format(client):
    """
    Test that the health endpoint returns properly formatted response.

    The response should be JSON with all required fields:
    - status: string ('ok' or 'degraded')
    - service: string identifying the service
    - version: string with API version
    - config_warnings: array of warning strings
    """
    response = client.get('/health')
    assert response.status_code == 200
    assert response.content_type == 'application/json'

    data = response.get_json()
    assert isinstance(data, dict)
    assert 'status' in data
    assert 'service' in data
    assert 'version' in data
    assert 'config_warnings' in data

    # Type checks
    assert isinstance(data['status'], str)
    assert isinstance(data['service'], str)
    assert isinstance(data['version'], str)
    assert isinstance(data['config_warnings'], list)
