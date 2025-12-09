"""Tests for core.team_of_week module."""

from unittest.mock import MagicMock, patch

import pytest
from discord import File as DFile

from core.team_of_week import (
    _build_widget_url,
    _extract_current_season,
    _get_cached,
    _get_latest_totw_round_id,
    _set_cached,
    fetch_team_week,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    # Import the _cache dict directly to clear it
    from core.team_of_week import _cache

    _cache.clear()
    yield
    _cache.clear()


def test_cache_get_set():
    """Test cache get/set functionality."""
    _set_cached("test_key", "test_value", expiry_hours=24)
    result = _get_cached("test_key")
    assert result == "test_value"


def test_cache_expired():
    """Test that expired cache returns None."""
    # Set with 0 hour expiry (immediately expired)
    _set_cached("test_key", "test_value", expiry_hours=-1)
    result = _get_cached("test_key")
    assert result is None


def test_cache_miss():
    """Test cache miss returns None."""
    result = _get_cached("nonexistent_key")
    assert result is None


def test_build_widget_url_with_valid_params():
    """Test building widget URL with valid season and round ID."""
    season_id = 77806
    round_id = 23075

    url = _build_widget_url(season_id, round_id)

    assert "season/77806" in url
    assert "round/23075" in url
    assert "teamOfTheWeek" in url
    assert "unique-tournament/238" in url


def test_build_widget_url_with_missing_season():
    """Test building widget URL falls back when season is None."""
    round_id = 23075

    url = _build_widget_url(None, round_id)

    # Should use fallback URL
    assert "widgets.sofascore.com" in url
    assert "teamOfTheWeek" in url


def test_build_widget_url_with_missing_round():
    """Test building widget URL falls back when round is None."""
    season_id = 77806

    url = _build_widget_url(season_id, None)

    # Should use fallback URL
    assert "widgets.sofascore.com" in url
    assert "teamOfTheWeek" in url


@patch("core.team_of_week.requests.get")
def test_extract_current_season_success(mock_get):
    """Test successful extraction of current season."""
    # Mock response with __NEXT_DATA__ containing season info
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """
    <script id="__NEXT_DATA__" type="application/json">
    {
        "props": {
            "pageProps": {
                "initialProps": {
                    "seasons": [
                        {"id": 77806, "year": "25/26"}
                    ]
                }
            }
        }
    }
    </script>
    """
    mock_get.return_value = mock_response

    season_id = _extract_current_season()

    assert season_id == 77806
    mock_get.assert_called_once()


@patch("core.team_of_week.requests.get")
def test_extract_current_season_failure(mock_get):
    """Test extraction failure returns None."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    season_id = _extract_current_season()

    assert season_id is None


@patch("core.team_of_week.requests.get")
def test_extract_current_season_caching(mock_get):
    """Test that season ID is cached."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """
    <script id="__NEXT_DATA__" type="application/json">
    {
        "props": {
            "pageProps": {
                "initialProps": {
                    "seasons": [{"id": 77806, "year": "25/26"}]
                }
            }
        }
    }
    </script>
    """
    mock_get.return_value = mock_response

    # First call should hit the API
    season_id_1 = _extract_current_season()
    assert season_id_1 == 77806
    assert mock_get.call_count == 1

    # Second call should use cache
    season_id_2 = _extract_current_season()
    assert season_id_2 == 77806
    assert mock_get.call_count == 1  # No additional call


@patch("core.team_of_week.requests.get")
def test_get_latest_totw_round_id_success(mock_get):
    """Test successful retrieval of latest TOTW round ID."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "rounds": [
            {"id": 23075, "roundId": 13, "roundName": "13"},
            {"id": 22963, "roundId": 12, "roundName": "12"},
        ]
    }
    mock_get.return_value = mock_response

    round_id = _get_latest_totw_round_id(77806)

    assert round_id == 23075
    mock_get.assert_called_once()


@patch("core.team_of_week.requests.get")
def test_get_latest_totw_round_id_empty_rounds(mock_get):
    """Test that empty rounds list returns None."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"rounds": []}
    mock_get.return_value = mock_response

    round_id = _get_latest_totw_round_id(77806)

    assert round_id is None


@patch("core.team_of_week.requests.get")
def test_get_latest_totw_round_id_api_error(mock_get):
    """Test that API errors return None."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_get.return_value = mock_response

    round_id = _get_latest_totw_round_id(77806)

    assert round_id is None


@patch("core.team_of_week.requests.get")
def test_get_latest_totw_round_id_caching(mock_get):
    """Test that TOTW round ID is cached."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "rounds": [{"id": 23075, "roundId": 13, "roundName": "13"}]
    }
    mock_get.return_value = mock_response

    # First call should hit the API
    round_id_1 = _get_latest_totw_round_id(77806)
    assert round_id_1 == 23075
    assert mock_get.call_count == 1

    # Second call should use cache
    round_id_2 = _get_latest_totw_round_id(77806)
    assert round_id_2 == 23075
    assert mock_get.call_count == 1  # No additional call


@patch("core.team_of_week.gen_browser")
@patch("core.team_of_week._extract_current_season")
@patch("core.team_of_week._get_latest_totw_round_id")
def test_fetch_team_week_success(
    mock_get_round, mock_get_season, mock_gen_browser
):
    """Test successful TOTW screenshot fetch."""
    # Mock season and round ID extraction
    mock_get_season.return_value = 77806
    mock_get_round.return_value = 23075

    # Mock browser and screenshot
    mock_browser = MagicMock()
    mock_browser.get_screenshot_as_png.return_value = (
        b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    )  # Minimal PNG
    mock_gen_browser.return_value = mock_browser

    # Mock PIL Image operations
    with patch("core.team_of_week.Image") as mock_image:
        mock_img = MagicMock()
        mock_img.size = (1280, 800)
        mock_image.open.return_value = mock_img

        result = fetch_team_week()

        assert isinstance(result, DFile)
        assert result.filename == "image.png"
        mock_browser.get.assert_called_once()
        mock_browser.quit.assert_called_once()


@patch("core.team_of_week.gen_browser")
@patch("core.team_of_week._extract_current_season")
@patch("core.team_of_week._get_latest_totw_round_id")
def test_fetch_team_week_uses_fallback_on_extraction_failure(
    mock_get_round, mock_get_season, mock_gen_browser
):
    """Test that fetch_team_week uses fallback URL when extraction fails."""
    # Simulate extraction failure
    mock_get_season.return_value = None
    mock_get_round.return_value = None

    mock_browser = MagicMock()
    mock_browser.get_screenshot_as_png.return_value = (
        b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    )
    mock_gen_browser.return_value = mock_browser

    with patch("core.team_of_week.Image") as mock_image:
        mock_img = MagicMock()
        mock_img.size = (1280, 800)
        mock_image.open.return_value = mock_img

        result = fetch_team_week()

        # Should still succeed using fallback URL
        assert isinstance(result, DFile)
        mock_browser.get.assert_called_once()
        # Verify fallback URL was used (contains round/23075
        # from FALLBACK_WIDGET_URL)
        call_args = mock_browser.get.call_args[0][0]
        assert "widgets.sofascore.com" in call_args


@patch("core.team_of_week.gen_browser")
@patch("core.team_of_week._extract_current_season")
@patch("core.team_of_week._get_latest_totw_round_id")
def test_fetch_team_week_browser_cleanup_on_error(
    mock_get_round, mock_get_season, mock_gen_browser
):
    """Test that browser is cleaned up even on errors."""
    mock_get_season.return_value = 77806
    mock_get_round.return_value = 23075

    mock_browser = MagicMock()
    mock_browser.get.side_effect = Exception("Browser error")
    mock_gen_browser.return_value = mock_browser

    with pytest.raises(Exception, match="Browser error"):
        fetch_team_week()

    # Browser should still be cleaned up
    mock_browser.quit.assert_called_once()
