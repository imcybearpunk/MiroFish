"""Tests for retry utilities in app.utils.retry module.

Tests cover:
- retry_with_backoff decorator behavior
- RetryableAPIClient retry and batch retry functionality
- Exception handling and filtering
- Callback invocation during retries
- Jitter in exponential backoff calculation
"""

import unittest
from unittest.mock import patch, MagicMock, call
import pytest

from app.utils.retry import retry_with_backoff, RetryableAPIClient


class TestRetryWithBackoffDecorator(unittest.TestCase):
    """Test suite for retry_with_backoff decorator."""

    @patch('app.utils.retry.time.sleep')
    def test_success_on_first_try(self, mock_sleep):
        """Function succeeds immediately without triggering retries."""
        @retry_with_backoff(max_retries=3)
        def successful_function():
            return "success"

        result = successful_function()

        assert result == "success"
        mock_sleep.assert_not_called()

    @patch('app.utils.retry.time.sleep')
    def test_retries_on_failure_then_succeeds(self, mock_sleep):
        """Function fails twice then succeeds on third attempt."""
        call_count = 0

        @retry_with_backoff(max_retries=3, initial_delay=1.0)
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = flaky_function()

        assert result == "success"
        assert call_count == 3
        assert mock_sleep.call_count == 2

    @patch('app.utils.retry.time.sleep')
    def test_raises_after_max_retries(self, mock_sleep):
        """Function always fails and raises exception after max_retries exhausted."""
        @retry_with_backoff(max_retries=3, initial_delay=1.0)
        def always_fails():
            raise ValueError("Persistent failure")

        with pytest.raises(ValueError, match="Persistent failure"):
            always_fails()

        assert mock_sleep.call_count == 3

    @patch('app.utils.retry.time.sleep')
    def test_on_retry_callback_called(self, mock_sleep):
        """Verify on_retry callback is invoked with correct attempt numbers."""
        callback = MagicMock()
        call_count = 0

        @retry_with_backoff(
            max_retries=3,
            initial_delay=1.0,
            on_retry=callback
        )
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("Retry me")
            return "done"

        result = flaky_function()

        assert result == "done"
        assert callback.call_count == 2
        # Verify callback was called with exception and attempt numbers
        calls_args = [call_obj[0] for call_obj in callback.call_args_list]
        assert len(calls_args) == 2
        assert isinstance(calls_args[0][0], RuntimeError)  # exception
        assert calls_args[0][1] == 1  # attempt number
        assert isinstance(calls_args[1][0], RuntimeError)
        assert calls_args[1][1] == 2

    @patch('app.utils.retry.time.sleep')
    def test_only_retries_specified_exceptions(self, mock_sleep):
        """Function raises ValueError but exceptions=(RuntimeError,) → no retry."""
        @retry_with_backoff(
            max_retries=3,
            exceptions=(RuntimeError,)
        )
        def fails_with_value_error():
            raise ValueError("Not in retry list")

        with pytest.raises(ValueError, match="Not in retry list"):
            fails_with_value_error()

        # Should raise immediately without retries
        mock_sleep.assert_not_called()

    @patch('app.utils.retry.time.sleep')
    def test_only_retries_specified_exceptions_matching(self, mock_sleep):
        """Function raises RuntimeError which is in exceptions tuple → retries."""
        call_count = 0

        @retry_with_backoff(
            max_retries=3,
            initial_delay=1.0,
            exceptions=(RuntimeError, ValueError)
        )
        def fails_with_runtime_error():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("Retryable error")
            return "recovered"

        result = fails_with_runtime_error()

        assert result == "recovered"
        assert mock_sleep.call_count == 1

    @patch('app.utils.retry.time.sleep')
    def test_max_retries_zero_no_retry(self, mock_sleep):
        """max_retries=0 means try once, fail immediately on exception."""
        @retry_with_backoff(max_retries=0)
        def always_fails():
            raise RuntimeError("Fail now")

        with pytest.raises(RuntimeError, match="Fail now"):
            always_fails()

        mock_sleep.assert_not_called()

    @patch('app.utils.retry.time.sleep')
    def test_return_value_preserved(self, mock_sleep):
        """Decorator preserves function return value without modification."""
        @retry_with_backoff(max_retries=2)
        def returns_dict():
            return {"key": "value", "number": 42, "nested": {"data": True}}

        result = returns_dict()

        assert result == {"key": "value", "number": 42, "nested": {"data": True}}
        mock_sleep.assert_not_called()

    @patch('app.utils.retry.time.sleep')
    def test_return_value_preserved_none(self, mock_sleep):
        """Decorator preserves None return value."""
        @retry_with_backoff(max_retries=2)
        def returns_none():
            return None

        result = returns_none()

        assert result is None
        mock_sleep.assert_not_called()

    @patch('app.utils.retry.time.sleep')
    def test_backoff_factor_increases_delay(self, mock_sleep):
        """Verify exponential backoff: each retry multiplies delay by backoff_factor."""
        @retry_with_backoff(
            max_retries=3,
            initial_delay=1.0,
            backoff_factor=2.0,
            jitter=False
        )
        def always_fails():
            raise RuntimeError("Fail")

        with pytest.raises(RuntimeError):
            always_fails()

        # Expected delays: 1.0, 2.0, 4.0
        assert mock_sleep.call_count == 3
        sleep_calls = [call_args[0][0] for call_args in mock_sleep.call_args_list]
        assert sleep_calls[0] == 1.0
        assert sleep_calls[1] == 2.0
        assert sleep_calls[2] == 4.0

    @patch('app.utils.retry.time.sleep')
    def test_max_delay_cap(self, mock_sleep):
        """Verify delay never exceeds max_delay even with large backoff_factor."""
        @retry_with_backoff(
            max_retries=4,
            initial_delay=2.0,
            backoff_factor=3.0,
            max_delay=10.0,
            jitter=False
        )
        def always_fails():
            raise RuntimeError("Fail")

        with pytest.raises(RuntimeError):
            always_fails()

        sleep_calls = [call_args[0][0] for call_args in mock_sleep.call_args_list]
        # Expected: 2.0, 6.0, 18.0 (capped at 10.0), 30.0 (capped at 10.0)
        assert sleep_calls[0] == 2.0
        assert sleep_calls[1] == 6.0
        assert sleep_calls[2] == 10.0  # capped
        assert sleep_calls[3] == 10.0  # capped

    @patch('app.utils.retry.time.sleep')
    def test_jitter_adds_randomness(self, mock_sleep):
        """With jitter=True, delay is randomized between 50% and 100% of calculated value."""
        call_count = 0

        @retry_with_backoff(
            max_retries=2,
            initial_delay=10.0,
            backoff_factor=1.0,
            jitter=True,
            exceptions=(RuntimeError,)
        )
        def fails_once():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Fail once")
            return "success"

        result = fails_once()

        assert result == "success"
        assert mock_sleep.call_count == 1
        # Jittered delay should be between 5.0 and 10.0
        sleep_value = mock_sleep.call_args_list[0][0][0]
        assert 5.0 <= sleep_value <= 10.0

    @patch('app.utils.retry.time.sleep')
    def test_function_with_args_and_kwargs(self, mock_sleep):
        """Decorator works with functions that have arguments."""
        @retry_with_backoff(max_retries=2, initial_delay=0.1)
        def function_with_args(a, b, multiplier=1):
            return (a + b) * multiplier

        result = function_with_args(3, 4, multiplier=2)

        assert result == 14
        mock_sleep.assert_not_called()

    @patch('app.utils.retry.time.sleep')
    def test_retries_with_args_on_failure(self, mock_sleep):
        """Retries function with same args/kwargs on failure."""
        call_count = 0

        @retry_with_backoff(max_retries=2, initial_delay=0.1)
        def function_with_args(a, b, multiplier=1):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Try again")
            return (a + b) * multiplier

        result = function_with_args(5, 3, multiplier=3)

        assert result == 24
        assert call_count == 2
        assert mock_sleep.call_count == 1


class TestRetryableAPIClient(unittest.TestCase):
    """Test suite for RetryableAPIClient class."""

    @patch('app.utils.retry.time.sleep')
    def test_call_with_retry_success(self, mock_sleep):
        """RetryableAPIClient.call_with_retry succeeds on first attempt."""
        client = RetryableAPIClient()
        func = MagicMock(return_value="api_response")

        result = client.call_with_retry(func, "arg1", "arg2", kwarg1="value1")

        assert result == "api_response"
        func.assert_called_once_with("arg1", "arg2", kwarg1="value1")
        mock_sleep.assert_not_called()

    @patch('app.utils.retry.time.sleep')
    def test_call_with_retry_fails_then_succeeds(self, mock_sleep):
        """RetryableAPIClient.call_with_retry retries on failure."""
        client = RetryableAPIClient()
        func = MagicMock(side_effect=[
            RuntimeError("Fail once"),
            "success"
        ])

        result = client.call_with_retry(
            func,
            exceptions=(RuntimeError,)
        )

        assert result == "success"
        assert func.call_count == 2
        assert mock_sleep.call_count == 1

    @patch('app.utils.retry.time.sleep')
    def test_call_with_retry_raises_after_max_retries(self, mock_sleep):
        """RetryableAPIClient.call_with_retry raises after exhausting retries."""
        client = RetryableAPIClient()
        func = MagicMock(side_effect=RuntimeError("Always fails"))

        with pytest.raises(RuntimeError, match="Always fails"):
            client.call_with_retry(
                func,
                exceptions=(RuntimeError,)
            )

        assert mock_sleep.call_count > 0

    @patch('app.utils.retry.time.sleep')
    def test_call_with_retry_respects_exception_filter(self, mock_sleep):
        """RetryableAPIClient respects exceptions parameter."""
        client = RetryableAPIClient()
        func = MagicMock(side_effect=ValueError("Not retryable"))

        with pytest.raises(ValueError, match="Not retryable"):
            client.call_with_retry(
                func,
                exceptions=(RuntimeError,)
            )

        func.assert_called_once()
        mock_sleep.assert_not_called()


class TestBatchWithRetry(unittest.TestCase):
    """Test suite for RetryableAPIClient.call_batch_with_retry method."""

    @patch('app.utils.retry.time.sleep')
    def test_batch_with_retry_all_success(self, mock_sleep):
        """All items process successfully, failures list is empty."""
        client = RetryableAPIClient()
        items = ["item1", "item2", "item3"]
        process_func = MagicMock(side_effect=lambda x: x.upper())

        results, failures = client.call_batch_with_retry(
            items,
            process_func,
            exceptions=(Exception,),
            continue_on_failure=True
        )

        assert results == ["ITEM1", "ITEM2", "ITEM3"]
        assert failures == []
        assert process_func.call_count == 3

    @patch('app.utils.retry.time.sleep')
    def test_batch_with_retry_partial_failure_continue(self, mock_sleep):
        """Some items fail, continue_on_failure=True returns partial results + failures."""
        client = RetryableAPIClient()
        items = ["good1", "bad1", "good2", "bad2"]

        def process_func(item):
            if "bad" in item:
                raise ValueError(f"Error processing {item}")
            return item.upper()

        results, failures = client.call_batch_with_retry(
            items,
            process_func,
            exceptions=(ValueError,),
            continue_on_failure=True
        )

        assert "GOOD1" in results
        assert "GOOD2" in results
        assert len(failures) == 2
        assert failures[0]["index"] == 1
        assert failures[0]["item"] == "bad1"
        assert "bad1" in str(failures[0]["error"])
        assert failures[1]["index"] == 3
        assert failures[1]["item"] == "bad2"

    @patch('app.utils.retry.time.sleep')
    def test_batch_with_retry_stop_on_first_failure(self, mock_sleep):
        """continue_on_failure=False raises on first failure."""
        client = RetryableAPIClient()
        items = ["good1", "bad1", "good2"]

        def process_func(item):
            if "bad" in item:
                raise ValueError(f"Error processing {item}")
            return item.upper()

        with pytest.raises(ValueError, match="Error processing bad1"):
            client.call_batch_with_retry(
                items,
                process_func,
                exceptions=(ValueError,),
                continue_on_failure=False
            )

    @patch('app.utils.retry.time.sleep')
    def test_batch_with_retry_empty_list(self, mock_sleep):
        """Empty item list returns empty results and failures."""
        client = RetryableAPIClient()
        process_func = MagicMock()

        results, failures = client.call_batch_with_retry(
            [],
            process_func,
            continue_on_failure=True
        )

        assert results == []
        assert failures == []
        process_func.assert_not_called()

    @patch('app.utils.retry.time.sleep')
    def test_batch_with_retry_preserves_order(self, mock_sleep):
        """Results maintain order corresponding to input items."""
        client = RetryableAPIClient()
        items = [10, 20, 30, 40, 50]
        process_func = MagicMock(side_effect=lambda x: x * 2)

        results, failures = client.call_batch_with_retry(
            items,
            process_func,
            continue_on_failure=True
        )

        assert results == [20, 40, 60, 80, 100]
        assert failures == []

    @patch('app.utils.retry.time.sleep')
    def test_batch_with_retry_retries_individual_items(self, mock_sleep):
        """Batch retries individual failing items according to retry settings."""
        client = RetryableAPIClient()
        items = ["a", "b", "c"]
        call_counts = {"a": 0, "b": 0, "c": 0}

        def process_func(item):
            call_counts[item] += 1
            if item == "b" and call_counts[item] < 2:
                raise RuntimeError(f"Fail {item}")
            return item.upper()

        results, failures = client.call_batch_with_retry(
            items,
            process_func,
            exceptions=(RuntimeError,),
            continue_on_failure=True
        )

        assert "A" in results
        assert "B" in results
        assert "C" in results
        assert failures == []
        # "b" should have been retried
        assert call_counts["b"] == 2

    @patch('app.utils.retry.time.sleep')
    def test_batch_failure_contains_original_exception(self, mock_sleep):
        """Failure entries contain the original exception instance/message."""
        client = RetryableAPIClient()
        items = ["item"]
        error_msg = "Specific error message"

        def process_func(item):
            raise RuntimeError(error_msg)

        results, failures = client.call_batch_with_retry(
            items,
            process_func,
            exceptions=(RuntimeError,),
            continue_on_failure=True
        )

        assert len(failures) == 1
        failure = failures[0]
        assert error_msg in str(failure["error"])

    @patch('app.utils.retry.time.sleep')
    def test_batch_multiple_exception_types(self, mock_sleep):
        """Batch respects multiple exception types in exceptions parameter."""
        client = RetryableAPIClient()
        items = ["will_raise_value_error", "will_raise_type_error", "good"]

        def process_func(item):
            if "value_error" in item:
                raise ValueError("Value error")
            elif "type_error" in item:
                raise TypeError("Type error")
            return "success"

        results, failures = client.call_batch_with_retry(
            items,
            process_func,
            exceptions=(ValueError, TypeError),
            continue_on_failure=True
        )

        assert "success" in results
        assert len(failures) == 2


if __name__ == "__main__":
    unittest.main()
