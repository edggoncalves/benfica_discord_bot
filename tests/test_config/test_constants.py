"""Tests for config.constants module."""

from config.constants import (
    CALENDAR_API_URL,
    CALENDAR_URL,
    NEWSPAPER_NAMES,
    TIMEZONE,
    WEEKDAY,
)


def test_timezone_is_lisbon():
    """Test that timezone is set to Europe/Lisbon."""
    assert TIMEZONE == "Europe/Lisbon"


def test_newspaper_names_list():
    """Test that newspaper names list contains expected newspapers."""
    assert isinstance(NEWSPAPER_NAMES, list)
    assert len(NEWSPAPER_NAMES) == 3
    assert "a_bola" in NEWSPAPER_NAMES
    assert "o_jogo" in NEWSPAPER_NAMES
    assert "record" in NEWSPAPER_NAMES


def test_weekday_mapping():
    """Test that weekday mapping contains all 7 days."""
    assert isinstance(WEEKDAY, dict)
    assert len(WEEKDAY) == 7
    assert WEEKDAY[1] == "Segunda-feira"
    assert WEEKDAY[7] == "Domingo"


def test_calendar_urls_are_valid():
    """Test that calendar URLs are properly formatted."""
    assert CALENDAR_URL.startswith("https://")
    assert "slbenfica.pt" in CALENDAR_URL
    assert CALENDAR_API_URL.startswith("https://")
    assert "slbenfica.pt" in CALENDAR_API_URL
