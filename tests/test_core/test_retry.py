"""Tests for core.retry module."""

import time
from unittest.mock import MagicMock

import pytest

from core.retry import retry_on_failure


def test_retry_on_failure_success_first_try():
    """Test that function succeeds on first try."""
    mock_func = MagicMock(return_value="success")
    decorated = retry_on_failure(max_attempts=3, delay=0.1)(mock_func)

    result = decorated()

    assert result == "success"
    assert mock_func.call_count == 1


def test_retry_on_failure_success_after_retries():
    """Test that function succeeds after some retries."""
    mock_func = MagicMock(
        __name__="mock_func",
        side_effect=[
            Exception("Fail 1"),
            Exception("Fail 2"),
            "success",
        ],
    )
    decorated = retry_on_failure(max_attempts=3, delay=0.1)(mock_func)

    result = decorated()

    assert result == "success"
    assert mock_func.call_count == 3


def test_retry_on_failure_all_attempts_fail():
    """Test that function raises exception after all attempts fail."""
    mock_func = MagicMock(
        __name__="mock_func", side_effect=ValueError("Always fails")
    )
    decorated = retry_on_failure(max_attempts=3, delay=0.1)(mock_func)

    with pytest.raises(ValueError, match="Always fails"):
        decorated()

    assert mock_func.call_count == 3


def test_retry_on_failure_exponential_backoff():
    """Test that retry uses exponential backoff."""
    mock_func = MagicMock(
        __name__="mock_func",
        side_effect=[Exception("Fail 1"), Exception("Fail 2"), "success"],
    )
    decorated = retry_on_failure(max_attempts=3, delay=0.1)(mock_func)

    start_time = time.time()
    result = decorated()
    elapsed_time = time.time() - start_time

    assert result == "success"
    # First retry: 0.1s, second retry: 0.2s = 0.3s minimum
    # Allow some overhead
    assert elapsed_time >= 0.25


def test_retry_on_failure_specific_exceptions():
    """Test that only specified exceptions are retried."""
    mock_func = MagicMock(side_effect=ValueError("Wrong exception"))
    decorated = retry_on_failure(
        max_attempts=3, delay=0.1, exceptions=(ConnectionError,)
    )(mock_func)

    # ValueError should not be retried, should fail immediately
    with pytest.raises(ValueError):
        decorated()

    assert mock_func.call_count == 1


def test_retry_on_failure_with_args_and_kwargs():
    """Test that function arguments are passed correctly."""
    mock_func = MagicMock(return_value="success")
    decorated = retry_on_failure(max_attempts=3, delay=0.1)(mock_func)

    result = decorated("arg1", "arg2", kwarg1="value1")

    assert result == "success"
    mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")


def test_retry_on_failure_preserves_function_name():
    """Test that decorator preserves original function metadata."""

    @retry_on_failure(max_attempts=3, delay=0.1)
    def my_function():
        """My docstring."""
        return "result"

    assert my_function.__name__ == "my_function"
    assert my_function.__doc__ == "My docstring."
