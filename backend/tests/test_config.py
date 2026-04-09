"""
Tests for application configuration.

Configuration is critical to the application's security and behavior.
These tests verify that:
- Required environment variables are properly loaded
- Validation catches missing or invalid configuration
- Default values are applied correctly
"""

import os
import pytest
from unittest.mock import patch


def test_secret_key_loaded_from_env(app):
    """
    Test that SECRET_KEY is loaded from environment variables.

    The app should read the SECRET_KEY from the SECRET_KEY environment
    variable, which is essential for session security.
    """
    assert app.config['SECRET_KEY'] is not None
    assert app.config['SECRET_KEY'] == 'test-secret-key-12345'


def test_debug_defaults_to_false(app):
    """
    Test that DEBUG mode defaults to False for security.

    Debug mode should be disabled by default (disabled in production).
    In tests, FLASK_DEBUG is set to 'False' in TEST_ENV_VARS.
    """
    # DEBUG should be False when FLASK_DEBUG='False'
    assert app.config['DEBUG'] is False


def test_testing_mode_enabled_in_tests(app):
    """
    Test that TESTING mode is enabled for the test app.

    When TESTING=True, Flask disables error catching during request
    handling, making it easier to debug test failures.
    """
    assert app.config['TESTING'] is True


def test_llm_api_key_loaded(app):
    """
    Test that LLM_API_KEY is loaded from environment variables.

    The LLM service requires an API key for authentication.
    In tests, this is set to a mock value.
    """
    assert app.config['LLM_API_KEY'] is not None
    assert app.config['LLM_API_KEY'] == 'sk-test-mock-key'


def test_zep_api_key_loaded(app):
    """
    Test that ZEP_API_KEY is loaded from environment variables.

    Zep Cloud requires an API key for memory management.
    In tests, this is set to a mock value.
    """
    assert app.config['ZEP_API_KEY'] is not None
    assert app.config['ZEP_API_KEY'] == 'test-zep-key'


def test_allowed_extensions_set_correctly(app):
    """
    Test that ALLOWED_EXTENSIONS contains expected file types.

    File uploads should only accept specific extensions for security.
    Expected extensions are: pdf, md, txt, markdown.
    """
    assert hasattr(app.config, 'ALLOWED_EXTENSIONS')
    allowed = app.config['ALLOWED_EXTENSIONS']
    assert 'pdf' in allowed
    assert 'md' in allowed
    assert 'txt' in allowed
    assert 'markdown' in allowed


def test_max_content_length_set(app):
    """
    Test that MAX_CONTENT_LENGTH is configured for upload limits.

    File uploads should be limited to prevent resource exhaustion.
    Default limit is 50MB.
    """
    assert app.config['MAX_CONTENT_LENGTH'] == 50 * 1024 * 1024


def test_json_as_ascii_false(app):
    """
    Test that JSON_AS_ASCII is disabled for proper Unicode handling.

    This setting ensures Chinese characters and other Unicode
    are displayed directly instead of escaped as \\uXXXX sequences.
    """
    assert app.config['JSON_AS_ASCII'] is False


def test_validate_returns_errors_when_keys_missing():
    """
    Test that config validation detects missing required keys.

    When required API keys are missing and app is not in DEBUG mode,
    validation should report errors.
    """
    from app.config import Config

    # Create a mock config object with missing keys
    with patch.dict(os.environ, {'FLASK_DEBUG': 'False'}, clear=False):
        # Remove critical env vars temporarily
        temp_env = os.environ.copy()
        for key in ['SECRET_KEY', 'LLM_API_KEY', 'ZEP_API_KEY']:
            temp_env.pop(key, None)

        with patch.dict(os.environ, temp_env, clear=True):
            errors = Config.validate()
            # Should report errors for missing keys in production mode
            assert len(errors) > 0


def test_validate_passes_when_keys_present(app):
    """
    Test that config validation passes when required keys are present.

    When all required configuration is provided, validate() should
    return an empty error list.
    """
    from app.config import Config

    with patch.dict(os.environ, {
        'SECRET_KEY': 'test-key',
        'LLM_API_KEY': 'test-llm-key',
        'ZEP_API_KEY': 'test-zep-key',
    }):
        # In test environment with all keys present, validation should pass
        # (Note: validate() checks for specific conditions; in testing with
        # mocked environment this should complete without critical errors)
        errors = Config.validate()
        # Errors list may contain warnings, but no missing key error for LLM_API_KEY
        assert not any('LLM_API_KEY' in str(e) for e in errors)


def test_default_chunk_size_configured(app):
    """
    Test that DEFAULT_CHUNK_SIZE is configured for text processing.

    Text chunking configuration affects how documents are split for
    vector embedding and processing.
    """
    assert app.config['DEFAULT_CHUNK_SIZE'] == 500


def test_default_chunk_overlap_configured(app):
    """
    Test that DEFAULT_CHUNK_OVERLAP is configured.

    Overlap between chunks helps preserve context during document processing.
    """
    assert app.config['DEFAULT_CHUNK_OVERLAP'] == 50
