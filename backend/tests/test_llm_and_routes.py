"""
Tests for LLMClient JSON handling and graph API routes.

This module contains comprehensive tests for:
1. LLMClient initialization, chat methods, and JSON parsing
2. Graph API routes for project management
"""

import pytest
import json
from unittest.mock import patch, MagicMock

from app.utils.llm_client import LLMClient


# ============== LLMClient Tests ==============

class TestLLMClientInitialization:
    """Tests for LLMClient initialization."""

    def test_llm_client_raises_without_api_key(self):
        """LLMClient raises ValueError when no API key is available."""
        with patch.dict('os.environ', {'LLM_API_KEY': ''}, clear=False):
            with patch('app.utils.llm_client.Config.LLM_API_KEY', None):
                with pytest.raises(ValueError) as exc_info:
                    LLMClient(api_key=None)
                assert "LLM_API_KEY 未配置" in str(exc_info.value)

    def test_llm_client_accepts_api_key_parameter(self):
        """LLMClient initializes successfully with provided API key."""
        with patch('app.utils.llm_client.OpenAI') as mock_openai:
            client = LLMClient(api_key="sk-test-key")
            assert client.api_key == "sk-test-key"
            mock_openai.assert_called_once()

    def test_llm_client_accepts_custom_base_url(self):
        """LLMClient accepts custom base_url parameter."""
        with patch('app.utils.llm_client.OpenAI') as mock_openai:
            client = LLMClient(api_key="sk-test", base_url="https://custom.api.com")
            assert client.base_url == "https://custom.api.com"

    def test_llm_client_accepts_custom_model(self):
        """LLMClient accepts custom model parameter."""
        with patch('app.utils.llm_client.OpenAI') as mock_openai:
            client = LLMClient(api_key="sk-test", model="custom-model-1")
            assert client.model == "custom-model-1"


class TestChatThinkTagHandling:
    """Tests for <think> tag stripping in chat responses."""

    @pytest.fixture
    def mock_llm_client(self):
        """Fixture providing a mocked LLMClient."""
        with patch('app.utils.llm_client.OpenAI') as mock_openai:
            mock_instance = MagicMock()
            mock_openai.return_value = mock_instance
            client = LLMClient(api_key="sk-test-key")
            yield client, mock_instance

    def test_chat_strips_think_tags(self, mock_llm_client):
        """chat() removes <think>reasoning</think> tags from response."""
        client, mock_openai = mock_llm_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "<think>reasoning</think>answer"
        mock_openai.chat.completions.create.return_value = mock_response

        result = client.chat([{"role": "user", "content": "hi"}])
        assert result == "answer"

    def test_chat_strips_multiline_think_tags(self, mock_llm_client):
        """chat() removes multiline <think>...</think> tags."""
        client, mock_openai = mock_llm_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = (
            "<think>\nmulti\nline\nreasoning\n</think>final response"
        )
        mock_openai.chat.completions.create.return_value = mock_response

        result = client.chat([{"role": "user", "content": "test"}])
        assert result == "final response"

    def test_chat_no_think_tags_unchanged(self, mock_llm_client):
        """chat() returns response unchanged when no think tags present."""
        client, mock_openai = mock_llm_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "plain response without tags"
        mock_openai.chat.completions.create.return_value = mock_response

        result = client.chat([{"role": "user", "content": "test"}])
        assert result == "plain response without tags"

    def test_chat_handles_think_tags_with_whitespace(self, mock_llm_client):
        """chat() removes think tags even with extra whitespace."""
        client, mock_openai = mock_llm_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = (
            "<think>   \n   reasoning   \n   </think>   answer   "
        )
        mock_openai.chat.completions.create.return_value = mock_response

        result = client.chat([{"role": "user", "content": "test"}])
        assert result == "answer"

    def test_chat_multiple_think_tags(self, mock_llm_client):
        """chat() removes multiple <think> sections from response."""
        client, mock_openai = mock_llm_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = (
            "<think>first</think>text<think>second</think>more"
        )
        mock_openai.chat.completions.create.return_value = mock_response

        result = client.chat([{"role": "user", "content": "test"}])
        assert result == "textmore"

    def test_chat_respects_temperature_parameter(self, mock_llm_client):
        """chat() passes temperature parameter to OpenAI API."""
        client, mock_openai = mock_llm_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "response"
        mock_openai.chat.completions.create.return_value = mock_response

        client.chat(
            [{"role": "user", "content": "test"}],
            temperature=0.5
        )

        call_kwargs = mock_openai.chat.completions.create.call_args[1]
        assert call_kwargs["temperature"] == 0.5

    def test_chat_respects_max_tokens_parameter(self, mock_llm_client):
        """chat() passes max_tokens parameter to OpenAI API."""
        client, mock_openai = mock_llm_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "response"
        mock_openai.chat.completions.create.return_value = mock_response

        client.chat(
            [{"role": "user", "content": "test"}],
            max_tokens=2048
        )

        call_kwargs = mock_openai.chat.completions.create.call_args[1]
        assert call_kwargs["max_tokens"] == 2048


class TestChatJsonParsing:
    """Tests for chat_json() JSON parsing and cleanup."""

    @pytest.fixture
    def mock_llm_client(self):
        """Fixture providing a mocked LLMClient."""
        with patch('app.utils.llm_client.OpenAI') as mock_openai:
            mock_instance = MagicMock()
            mock_openai.return_value = mock_instance
            client = LLMClient(api_key="sk-test-key")
            yield client, mock_instance

    def test_chat_json_parses_valid_json(self, mock_llm_client):
        """chat_json() parses and returns valid JSON object."""
        client, mock_openai = mock_llm_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"key": "value", "count": 42}'
        mock_openai.chat.completions.create.return_value = mock_response

        result = client.chat_json([{"role": "user", "content": "test"}])
        assert result == {"key": "value", "count": 42}

    def test_chat_json_strips_markdown_json_wrapper(self, mock_llm_client):
        """chat_json() removes ```json...``` code block wrapper."""
        client, mock_openai = mock_llm_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '```json\n{"key": "value"}\n```'
        mock_openai.chat.completions.create.return_value = mock_response

        result = client.chat_json([{"role": "user", "content": "test"}])
        assert result == {"key": "value"}

    def test_chat_json_strips_plain_code_block(self, mock_llm_client):
        """chat_json() removes plain ``` ``` code block without json label."""
        client, mock_openai = mock_llm_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '```\n{"key": "value"}\n```'
        mock_openai.chat.completions.create.return_value = mock_response

        result = client.chat_json([{"role": "user", "content": "test"}])
        assert result == {"key": "value"}

    def test_chat_json_handles_newlines_in_wrapper(self, mock_llm_client):
        """chat_json() handles various newline patterns in code blocks."""
        client, mock_openai = mock_llm_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '```json\n\n{"a": 1}\n\n```'
        mock_openai.chat.completions.create.return_value = mock_response

        result = client.chat_json([{"role": "user", "content": "test"}])
        assert result == {"a": 1}

    def test_chat_json_raises_on_invalid_json(self, mock_llm_client):
        """chat_json() raises ValueError when response is not valid JSON."""
        client, mock_openai = mock_llm_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "not valid json at all"
        mock_openai.chat.completions.create.return_value = mock_response

        with pytest.raises(ValueError) as exc_info:
            client.chat_json([{"role": "user", "content": "test"}])
        assert "LLM返回的JSON格式无效" in str(exc_info.value)

    def test_chat_json_raises_with_partial_json(self, mock_llm_client):
        """chat_json() raises ValueError on incomplete JSON."""
        client, mock_openai = mock_llm_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"incomplete": '
        mock_openai.chat.completions.create.return_value = mock_response

        with pytest.raises(ValueError) as exc_info:
            client.chat_json([{"role": "user", "content": "test"}])
        assert "LLM返回的JSON格式无效" in str(exc_info.value)

    def test_chat_json_with_nested_objects(self, mock_llm_client):
        """chat_json() correctly parses nested JSON structures."""
        client, mock_openai = mock_llm_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = (
            '{"user": {"name": "Alice", "age": 30}, "roles": ["admin", "user"]}'
        )
        mock_openai.chat.completions.create.return_value = mock_response

        result = client.chat_json([{"role": "user", "content": "test"}])
        assert result["user"]["name"] == "Alice"
        assert result["user"]["age"] == 30
        assert result["roles"] == ["admin", "user"]

    def test_chat_json_respects_temperature_parameter(self, mock_llm_client):
        """chat_json() passes custom temperature to chat()."""
        client, mock_openai = mock_llm_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"key": "value"}'
        mock_openai.chat.completions.create.return_value = mock_response

        client.chat_json(
            [{"role": "user", "content": "test"}],
            temperature=0.2
        )

        call_kwargs = mock_openai.chat.completions.create.call_args[1]
        assert call_kwargs["temperature"] == 0.2


# ============== Graph API Route Tests ==============

class TestGetProjectRoute:
    """Tests for GET /api/graph/project/<project_id> route."""

    def test_get_project_not_found_returns_404(self, client):
        """GET /api/graph/project/nonexistent returns 404 status code."""
        response = client.get('/api/graph/project/nonexistent')
        assert response.status_code == 404

    def test_get_project_not_found_returns_success_false(self, client):
        """GET /api/graph/project/nonexistent has success=False in response."""
        response = client.get('/api/graph/project/nonexistent')
        data = response.get_json()
        assert data["success"] is False

    def test_get_project_not_found_has_error_message(self, client):
        """GET /api/graph/project/nonexistent includes error message."""
        response = client.get('/api/graph/project/nonexistent')
        data = response.get_json()
        assert "error" in data
        assert isinstance(data["error"], str)


class TestListProjectsRoute:
    """Tests for GET /api/graph/project/list route."""

    def test_list_projects_returns_200(self, client):
        """GET /api/graph/project/list returns 200 status code."""
        response = client.get('/api/graph/project/list')
        assert response.status_code == 200

    def test_list_projects_returns_success_true(self, client):
        """GET /api/graph/project/list has success=True in response."""
        response = client.get('/api/graph/project/list')
        data = response.get_json()
        assert data["success"] is True

    def test_list_projects_has_data_and_count(self, client):
        """GET /api/graph/project/list includes data list and count integer."""
        response = client.get('/api/graph/project/list')
        data = response.get_json()
        assert "data" in data
        assert isinstance(data["data"], list)
        assert "count" in data
        assert isinstance(data["count"], int)

    def test_list_projects_count_matches_data_length(self, client):
        """GET /api/graph/project/list count matches length of data array."""
        response = client.get('/api/graph/project/list')
        data = response.get_json()
        assert data["count"] == len(data["data"])

    def test_list_projects_respects_limit_parameter(self, client):
        """GET /api/graph/project/list accepts limit query parameter."""
        response = client.get('/api/graph/project/list?limit=10')
        assert response.status_code == 200
        data = response.get_json()
        # Count should not exceed the limit
        assert data["count"] <= 10


class TestDeleteProjectRoute:
    """Tests for DELETE /api/graph/project/<project_id> route."""

    def test_delete_nonexistent_project_returns_404(self, client):
        """DELETE /api/graph/project/fake returns 404 status code."""
        response = client.delete('/api/graph/project/nonexistent-id-12345')
        assert response.status_code == 404

    def test_delete_nonexistent_project_has_error(self, client):
        """DELETE /api/graph/project/fake has success=False in response."""
        response = client.delete('/api/graph/project/nonexistent-id-12345')
        data = response.get_json()
        assert data["success"] is False

    def test_delete_nonexistent_project_includes_error_message(self, client):
        """DELETE /api/graph/project/fake includes error field."""
        response = client.delete('/api/graph/project/nonexistent-id-12345')
        data = response.get_json()
        assert "error" in data
        assert isinstance(data["error"], str)


class TestProjectResponseFormats:
    """Tests for consistent response format across project routes."""

    def test_list_projects_json_format_valid(self, client):
        """GET /api/graph/project/list returns valid JSON."""
        response = client.get('/api/graph/project/list')
        try:
            data = response.get_json()
            assert isinstance(data, dict)
        except Exception as e:
            pytest.fail(f"Response is not valid JSON: {e}")

    def test_list_projects_has_required_fields(self, client):
        """GET /api/graph/project/list response includes required fields."""
        response = client.get('/api/graph/project/list')
        data = response.get_json()
        required_fields = ["success", "data", "count"]
        for field in required_fields:
            assert field in data

    def test_delete_error_response_has_success_false(self, client):
        """DELETE route error response has success=False."""
        response = client.delete('/api/graph/project/invalid-id')
        data = response.get_json()
        assert "success" in data
        assert data["success"] is False
