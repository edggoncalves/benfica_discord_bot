"""Tests for config.validation module."""

from config.validation import validate_rate_limit_hours


def test_validate_rate_limit_hours_with_valid_values():
    """Test validate_rate_limit_hours() with valid positive integers."""
    assert validate_rate_limit_hours("1") is True
    assert validate_rate_limit_hours("24") is True
    assert validate_rate_limit_hours("100") is True
    assert validate_rate_limit_hours("999") is True


def test_validate_rate_limit_hours_with_zero():
    """Test validate_rate_limit_hours() with zero returns False."""
    assert validate_rate_limit_hours("0") is False


def test_validate_rate_limit_hours_with_negative():
    """Test validate_rate_limit_hours() with negative number returns False."""
    assert validate_rate_limit_hours("-1") is False
    assert validate_rate_limit_hours("-24") is False


def test_validate_rate_limit_hours_with_non_digit():
    """Test validate_rate_limit_hours() with non-digit strings."""
    assert validate_rate_limit_hours("abc") is False
    assert validate_rate_limit_hours("12.5") is False
    assert validate_rate_limit_hours("") is False
    assert validate_rate_limit_hours(" ") is False


def test_validate_rate_limit_hours_with_mixed():
    """Test validate_rate_limit_hours() with mixed alphanumeric."""
    assert validate_rate_limit_hours("12abc") is False
    assert validate_rate_limit_hours("ab12") is False
