"""Tests for match message formatters."""

import pendulum
import pytest

from config.constants import TIMEZONE
from core.match.formatter import format_upcoming_matches_message


@pytest.fixture
def sample_matches():
    """Sample match data for testing."""
    return [
        {
            "date": "01-12-2025",
            "time": "20:45",
            "adversary": "FC Porto",
            "location": "Estádio da Luz",
            "competition": "Liga Portugal",
            "home": "Casa",
            "tv_channel": "Sport TV",
        },
        {
            "date": "08-12-2025",
            "time": "18:30",
            "adversary": "Sporting CP",
            "location": "Estádio José Alvalade",
            "competition": "Liga Portugal",
            "home": "Fora",
            "tv_channel": None,
        },
    ]


@pytest.fixture
def single_match():
    """Single match fixture for edge case testing."""
    return [
        {
            "date": "15-12-2025",
            "time": "21:00",
            "adversary": "SC Braga",
            "location": "Estádio Municipal de Braga",
            "competition": "Taça de Portugal",
            "home": "Fora",
            "tv_channel": "RTP 1",
        }
    ]


def test_format_upcoming_matches_with_discord_timestamps(sample_matches):
    """Test that formatter uses Discord timestamp format."""
    result = format_upcoming_matches_message(sample_matches)

    # Should contain Discord timestamp format
    assert "<t:" in result
    assert ":F>" in result

    # Should contain match details
    assert "FC Porto" in result
    assert "Sporting CP" in result
    assert "Sport TV" in result


def test_format_upcoming_matches_timestamp_calculation(sample_matches):
    """Test that timestamps are calculated correctly."""
    result = format_upcoming_matches_message(sample_matches)

    # Calculate expected timestamp for first match
    match_dt = pendulum.datetime(
        year=2025, month=12, day=1, hour=20, minute=45, tz=TIMEZONE
    )
    expected_timestamp = int(match_dt.timestamp())

    # Verify timestamp appears in output
    assert f"<t:{expected_timestamp}:F>" in result


def test_format_upcoming_matches_empty_list():
    """Test formatter with empty match list."""
    result = format_upcoming_matches_message([])

    assert "Não há jogos futuros" in result


def test_format_upcoming_matches_none():
    """Test formatter with None."""
    result = format_upcoming_matches_message(None)

    assert "Não há jogos futuros" in result


def test_format_upcoming_matches_home_away_display(sample_matches):
    """Test home/away indicators are correct."""
    result = format_upcoming_matches_message(sample_matches)

    # First match is home
    assert "🏠 Casa" in result
    # Second match is away
    assert "✈️ Fora" in result


def test_format_upcoming_matches_single_match(single_match):
    """Test formatter with single match."""
    result = format_upcoming_matches_message(single_match)

    # Should contain the match
    assert "SC Braga" in result
    assert "Taça de Portugal" in result
    assert "RTP 1" in result
    assert "✈️ Fora" in result


def test_format_upcoming_matches_without_tv_channel():
    """Test formatter handles matches without TV channel."""
    matches = [
        {
            "date": "20-12-2025",
            "time": "19:00",
            "adversary": "Vitória SC",
            "location": "Estádio da Luz",
            "competition": "Liga Portugal",
            "home": "Casa",
            "tv_channel": None,
        }
    ]

    result = format_upcoming_matches_message(matches)

    # Should contain match details but not TV channel section
    assert "Vitória SC" in result
    assert "📺" not in result  # TV emoji should not appear


def test_format_upcoming_matches_preserves_order(sample_matches):
    """Test that matches are displayed in order."""
    result = format_upcoming_matches_message(sample_matches)

    # FC Porto should appear before Sporting CP
    fc_porto_pos = result.index("FC Porto")
    sporting_pos = result.index("Sporting CP")

    assert fc_porto_pos < sporting_pos


def test_format_upcoming_matches_number_emojis(sample_matches):
    """Test that number emojis are used for first 10 matches."""
    result = format_upcoming_matches_message(sample_matches)

    # Should use emoji numbers for first two matches
    assert "1️⃣" in result
    assert "2️⃣" in result


def test_format_upcoming_matches_all_fields_present(sample_matches):
    """Test that all match fields are displayed."""
    result = format_upcoming_matches_message(sample_matches)

    # Should contain header
    assert "Próximos Jogos do Benfica" in result

    # Should contain locations
    assert "Estádio da Luz" in result
    assert "Estádio José Alvalade" in result

    # Should contain competitions
    assert "Liga Portugal" in result

    # Should contain emojis
    assert "⚽" in result
    assert "🏟️" in result
    assert "🏆" in result
