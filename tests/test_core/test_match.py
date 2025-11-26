"""Tests for core.match module."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pendulum
import pytest

from core.match import (
    _normalize_match_data,
    how_long_until,
    match_data_to_pendulum,
    read_match_data,
    update_match_date,
    when_is_it,
    write_match_data,
)


@pytest.fixture
def sample_match_data():
    """Sample match data for testing (format from ESPN scraper)."""
    return {
        "date": datetime(2025, 11, 25, 20, 15),
        "adversary": "FC Porto",
        "location": "Estádio da Luz",
        "competition": "Liga Portugal",
        "is_home": True,
    }


@pytest.fixture
def temp_match_file(tmp_path):
    """Create a temporary match data file."""
    file_path = tmp_path / "match_data.json"
    return file_path


def test_write_match_data(sample_match_data, temp_match_file):
    """Test writing match data to file."""
    with patch("core.match.MATCH_DATA_FILE", temp_match_file):
        write_match_data(sample_match_data)

        assert temp_match_file.exists()
        with open(temp_match_file) as f:
            data = json.load(f)
            assert data["adversary"] == "FC Porto"
            assert "year" in data
            assert "month" in data


def test_read_match_data(sample_match_data, temp_match_file):
    """Test reading match data from file."""
    # First write data
    with patch("core.match.MATCH_DATA_FILE", temp_match_file):
        write_match_data(sample_match_data)

        # Then read it back
        data = read_match_data()
        assert data["adversary"] == "FC Porto"
        assert "year" in data


def test_read_match_data_raises_when_missing():
    """Test that read_match_data raises FileNotFoundError when file missing."""
    with patch("core.match.MATCH_DATA_FILE", Path("/nonexistent/file.json")):
        with pytest.raises(FileNotFoundError):
            read_match_data()


def test_match_data_to_pendulum(sample_match_data, temp_match_file):
    """Test converting match data to pendulum datetime."""
    with patch("core.match.MATCH_DATA_FILE", temp_match_file):
        write_match_data(sample_match_data)
        data = read_match_data()

        result = match_data_to_pendulum(data)

        assert isinstance(result, pendulum.DateTime)
        assert result.timezone_name == "Europe/Lisbon"


def test_when_is_it(sample_match_data, temp_match_file):
    """Test when_is_it message formatting."""
    with patch("core.match.MATCH_DATA_FILE", temp_match_file):
        write_match_data(sample_match_data)

        result = when_is_it()

        assert "FC Porto" in result
        assert "Estádio da Luz" in result
        assert "Liga Portugal" in result


def test_how_long_until_future_match(temp_match_file):
    """Test countdown message for future match."""
    # Set match to tomorrow
    tomorrow = pendulum.tomorrow("Europe/Lisbon").set(hour=20, minute=15)
    match_data = {
        "date": tomorrow.naive(),
        "adversary": "FC Porto",
        "location": "Estádio da Luz",
        "competition": "Liga Portugal",
        "is_home": True,
    }

    with patch("core.match.MATCH_DATA_FILE", temp_match_file):
        write_match_data(match_data)

        result = how_long_until()

        # Should contain countdown
        assert "dia" in result or "hora" in result


def test_update_match_date_with_api_success():
    """Test update_match_date using API successfully."""
    # Benfica API returns this format
    api_data = {
        "date": "25-11-2025",
        "time": "20:15",
        "adversary": "FC Porto",
        "location": "Estádio da Luz",
        "competition": "Liga Portugal",
        "home": "Casa",
    }

    with patch("core.match.get_next_match_from_api", return_value=api_data):
        with patch("core.match.write_match_data") as mock_write:
            result = update_match_date()

            assert result is True
            # Verify write_match_data was called once
            mock_write.assert_called_once()
            # Verify the normalized data has a datetime object
            written_data = mock_write.call_args[0][0]
            assert "date" in written_data
            assert hasattr(written_data["date"], "year")
            assert written_data["adversary"] == "FC Porto"
            assert written_data["is_home"] is True


def test_update_match_date_with_espn_fallback():
    """Test update_match_date falls back to ESPN when API fails."""
    # ESPN returns this format (already with datetime object)
    espn_data = {
        "date": pendulum.datetime(2025, 11, 25, 20, 15, tz="Europe/Lisbon"),
        "adversary": "FC Porto",
        "location": "Estádio da Luz",
        "competition": "Liga Portugal",
        "is_home": True,
    }

    with patch("core.match.get_next_match_from_api", return_value=None):
        with patch("core.match.get_next_match", return_value=espn_data):
            with patch("core.match.write_match_data") as mock_write:
                result = update_match_date()

                assert result is True
                # Verify write_match_data was called once
                mock_write.assert_called_once()
                # ESPN data is already normalized, should be passed through
                written_data = mock_write.call_args[0][0]
                assert written_data["adversary"] == "FC Porto"
                assert written_data["is_home"] is True


def test_update_match_date_fails_when_both_fail():
    """Test update_match_date returns False when both sources fail."""
    with patch("core.match.get_next_match_from_api", return_value=None):
        with patch("core.match.get_next_match", return_value=None):
            result = update_match_date()

            assert result is False


def test_normalize_match_data_from_benfica_api():
    """Test normalizing data from Benfica Calendar API."""
    api_data = {
        "date": "25-11-2025",
        "time": "20:15",
        "adversary": "FC Porto",
        "location": "Estádio da Luz",
        "competition": "Liga Portugal",
        "home": "Casa",
    }

    result = _normalize_match_data(api_data, "benfica_api")

    # Verify datetime object was created correctly
    assert isinstance(result["date"], pendulum.DateTime)
    assert result["date"].year == 2025
    assert result["date"].month == 11
    assert result["date"].day == 25
    assert result["date"].hour == 20
    assert result["date"].minute == 15
    assert result["date"].timezone_name == "Europe/Lisbon"

    # Verify other fields
    assert result["adversary"] == "FC Porto"
    assert result["location"] == "Estádio da Luz"
    assert result["competition"] == "Liga Portugal"
    assert result["is_home"] is True


def test_normalize_match_data_from_benfica_api_away():
    """Test normalizing away match from Benfica Calendar API."""
    api_data = {
        "date": "28-11-2025",
        "time": "18:30",
        "adversary": "Sporting CP",
        "location": "Estádio José Alvalade",
        "competition": "Liga Portugal",
        "home": "Fora",
    }

    result = _normalize_match_data(api_data, "benfica_api")

    assert result["is_home"] is False
    assert result["adversary"] == "Sporting CP"


def test_normalize_match_data_from_espn():
    """Test normalizing data from ESPN (should pass through)."""
    espn_data = {
        "date": pendulum.datetime(2025, 11, 25, 20, 15, tz="Europe/Lisbon"),
        "adversary": "FC Porto",
        "location": "Estádio da Luz",
        "competition": "Liga Portugal",
        "is_home": True,
    }

    result = _normalize_match_data(espn_data, "espn")

    # Should return the same data unchanged
    assert result == espn_data
    assert result["is_home"] is True
