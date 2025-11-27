"""Tests for core.benfica_calendar module."""

from unittest.mock import MagicMock, Mock, patch

import pendulum
import pytest
from curl_cffi import requests as curl_requests

from core.benfica_calendar import (
    CURRENT_SEASON,
    Calendar,
    _parse_match_from_event,
    get_next_match_from_api,
)


@pytest.fixture
def future_match_event():
    """Sample event for a future match."""
    future_date = pendulum.now("Europe/Lisbon").add(days=7)
    return {
        "MatchDate": future_date.to_iso8601_string(),
        "AdversaryName": "FC Porto",
        "StadiumName": "Estádio da Luz",
        "TournamentName": "Liga Portugal",
        "IsHome": True,
    }


@pytest.fixture
def past_match_event():
    """Sample event for a past match."""
    past_date = pendulum.now("Europe/Lisbon").subtract(days=7)
    return {
        "MatchDate": past_date.to_iso8601_string(),
        "AdversaryName": "Sporting CP",
        "StadiumName": "Estádio José Alvalade",
        "TournamentName": "Liga Portugal",
        "IsHome": False,
    }


def test_parse_match_from_event_future_match(future_match_event):
    """Test parsing a future match event."""
    result = _parse_match_from_event(future_match_event)

    assert result is not None
    assert result["adversary"] == "FC Porto"
    assert result["location"] == "Estádio da Luz"
    assert result["competition"] == "Liga Portugal"
    assert result["home"] == "Casa"
    assert "date" in result
    assert "time" in result


def test_parse_match_from_event_past_match(past_match_event):
    """Test parsing a past match returns None."""
    result = _parse_match_from_event(past_match_event)

    # Past matches should be filtered out
    assert result is None


def test_parse_match_from_event_missing_date():
    """Test parsing event with missing date returns None."""
    event = {
        "AdversaryName": "FC Porto",
        "StadiumName": "Estádio da Luz",
        "TournamentName": "Liga Portugal",
        "IsHome": True,
    }

    result = _parse_match_from_event(event)

    assert result is None


def test_parse_match_from_event_away_match(future_match_event):
    """Test parsing an away match."""
    future_match_event["IsHome"] = False

    result = _parse_match_from_event(future_match_event)

    assert result is not None
    assert result["home"] == "Fora"


def test_get_next_match_from_api_success(future_match_event):
    """Test successful API fetch."""
    mock_calendar = MagicMock()
    # get_events() now returns a list directly
    mock_calendar.get_events.return_value = [future_match_event]

    with patch("core.benfica_calendar.Calendar", return_value=mock_calendar):
        result = get_next_match_from_api()

        assert result is not None
        assert result["adversary"] == "FC Porto"


def test_get_next_match_from_api_no_events():
    """Test API with no events."""
    mock_calendar = MagicMock()
    mock_calendar.get_events.return_value = []

    with patch("core.benfica_calendar.Calendar", return_value=mock_calendar):
        result = get_next_match_from_api()

        assert result is None


def test_get_next_match_from_api_only_past_matches(past_match_event):
    """Test API with only past matches."""
    mock_calendar = MagicMock()
    mock_calendar.get_events.return_value = [past_match_event]

    with patch("core.benfica_calendar.Calendar", return_value=mock_calendar):
        result = get_next_match_from_api()

        assert result is None


def test_get_next_match_from_api_error():
    """Test API fetch with exception."""
    with patch(
        "core.benfica_calendar.Calendar", side_effect=Exception("API Error")
    ):
        result = get_next_match_from_api()

        assert result is None


def test_get_next_match_from_api_picks_first_future():
    """Test API returns first future match when multiple exist."""
    now = pendulum.now("Europe/Lisbon")
    first_match = {
        "MatchDate": now.add(days=1).to_iso8601_string(),
        "AdversaryName": "First Opponent",
        "StadiumName": "Stadium 1",
        "TournamentName": "Competition 1",
        "IsHome": True,
    }
    second_match = {
        "MatchDate": now.add(days=7).to_iso8601_string(),
        "AdversaryName": "Second Opponent",
        "StadiumName": "Stadium 2",
        "TournamentName": "Competition 2",
        "IsHome": False,
    }

    mock_calendar = MagicMock()
    mock_calendar.get_events.return_value = [first_match, second_match]

    with patch("core.benfica_calendar.Calendar", return_value=mock_calendar):
        result = get_next_match_from_api()

        assert result is not None
        assert result["adversary"] == "First Opponent"


# Calendar class tests


@pytest.fixture
def mock_calendar_html():
    """Mock HTML response from calendar page with calendar items."""
    return """
    <html>
        <body>
            <input type="hidden" name="__RequestVerificationToken" value="test-token-12345" />
            <div class="modality" id="{ECCFEB41-A0FD-4830-A3BB-7E57A0A15D00}"></div>
        </body>
    </html>
    """


@pytest.fixture
def mock_calendar_events_html():
    """Mock HTML response from calendar events API."""
    future_date = pendulum.now("Europe/Lisbon").add(days=7)
    date_str = future_date.format("MM/DD/YYYY hh:mm:ss A")

    return f"""
    <div class="calendar-item col-12 scheduled">
        <div class="calendar-item-border">
            <div class="row">
                <div class="calendar-item-header">
                    <div class="calendar-date">date</div>
                    <div class="calendar-match-location">Estádio da Luz</div>
                </div>
                <div class="calendar-item-data">
                    <div class="calendar-competition">Liga Portugal 25/26</div>
                    <div class="calendar-match-info">
                        <div style="display: none" class="titleForCalendar">SL Benfica vs FC Porto</div>
                        <div style="display: none" class="locationForCalendar">Estádio da Luz</div>
                        <div style="display: none" class="startDateForCalendar">{date_str}</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """


@pytest.fixture
def mock_curl_response(mock_calendar_html):
    """Mock curl_cffi response."""
    mock_response = Mock()
    mock_response.content = mock_calendar_html.encode("utf-8")
    mock_response.text = mock_calendar_html
    mock_response.cookies = Mock()
    mock_response.cookies.get_dict.return_value = {
        "ASP.NET_SessionId": "session123",
        "benficadp#lang": "pt",
        "SC_ANALYTICS_GLOBAL_COOKIE": "analytics123",
        "__RequestVerificationToken": "token456",
        "TS01810e8d": "ts123",
        "TSbc7b53c7027": "ts456",
    }
    return mock_response


def test_calendar_init_success(mock_curl_response):
    """Test Calendar initialization extracts token correctly."""
    with patch("core.benfica_calendar.requests.get") as mock_get:
        mock_get.return_value = mock_curl_response

        calendar = Calendar()

        # Verify GET request was made
        mock_get.assert_called_once()
        call_args = mock_get.call_args

        # Check URL and impersonation
        assert "slbenfica.pt" in call_args[0][0]
        assert call_args[1]["impersonate"] == "chrome"
        assert call_args[1]["timeout"] == 30

        # Verify token extraction
        assert calendar.request_verification_token == "test-token-12345"


def test_calendar_init_missing_token():
    """Test Calendar initialization fails when token is missing."""
    mock_response = Mock()
    mock_response.content = b"<html><body>No token here</body></html>"
    mock_response.text = "<html><body>No token here</body></html>"
    mock_response.cookies = Mock()
    mock_response.cookies.get_dict.return_value = {}

    with patch("core.benfica_calendar.requests.get") as mock_get:
        mock_get.return_value = mock_response

        # Should raise exception when token not found
        with pytest.raises((TypeError, AttributeError, KeyError)):
            Calendar()


def test_calendar_init_network_error():
    """Test Calendar initialization handles network errors."""
    with patch("core.benfica_calendar.requests.get") as mock_get:
        mock_get.side_effect = curl_requests.RequestsError("Network error")

        with pytest.raises(curl_requests.RequestsError):
            Calendar()


def test_create_payload(mock_curl_response):
    """Test _create_payload creates correct payload structure."""
    with patch("core.benfica_calendar.requests.get") as mock_get:
        mock_get.return_value = mock_curl_response

        calendar = Calendar()
        payload = calendar._create_payload()

        # Verify payload structure
        assert "filters" in payload
        filters = payload["filters"]

        # Check all required fields
        assert filters["Menu"] == "next"
        assert filters["Modality"] == "{ECCFEB41-A0FD-4830-A3BB-7E57A0A15D00}"
        assert filters["IsMaleTeam"] is True  # Boolean, not string
        assert "Rank" in filters
        assert "Tournaments" in filters
        assert isinstance(filters["Tournaments"], list)
        assert len(filters["Tournaments"]) > 0
        assert filters["Seasons"] == [CURRENT_SEASON]
        assert filters["PageNumber"] == 0


def test_create_headers(mock_curl_response):
    """Test _create_headers creates correct headers."""
    with patch("core.benfica_calendar.requests.get") as mock_get:
        mock_get.return_value = mock_curl_response

        calendar = Calendar()
        headers = calendar._create_headers()

        # Verify required headers (curl_cffi handles most headers automatically)
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
        assert "__RequestVerificationToken" in headers
        assert headers["__RequestVerificationToken"] == "test-token-12345"
        assert "Referer" in headers
        assert "slbenfica.pt" in headers["Referer"]
        assert "X-Requested-With" in headers
        assert headers["X-Requested-With"] == "XMLHttpRequest"


def test_get_events_success(mock_curl_response, mock_calendar_events_html):
    """Test get_events successfully fetches and parses calendar data."""
    mock_api_response = Mock()
    mock_api_response.text = mock_calendar_events_html
    mock_api_response.status_code = 200
    mock_api_response.raise_for_status = Mock()

    with patch("core.benfica_calendar.requests.get") as mock_get:
        mock_get.return_value = mock_curl_response

        with patch("core.benfica_calendar.requests.post") as mock_post:
            mock_post.return_value = mock_api_response

            calendar = Calendar()
            events = calendar.get_events()

            # Verify POST was called with correct parameters
            mock_post.assert_called_once()
            call_args = mock_post.call_args

            # Check API URL
            assert "slbenfica.pt" in call_args[0][0]

            # Verify curl_cffi parameters
            assert call_args[1]["impersonate"] == "chrome"
            assert call_args[1]["timeout"] == 30

            # Verify response is a list
            assert isinstance(events, list)
            assert len(events) == 1

            # Verify parsed event structure
            event = events[0]
            assert "MatchDate" in event
            assert "AdversaryName" in event
            assert "StadiumName" in event
            assert "TournamentName" in event
            assert "IsHome" in event


def test_get_events_http_error(mock_curl_response):
    """Test get_events handles HTTP errors."""
    mock_api_response = Mock()
    mock_api_response.raise_for_status.side_effect = (
        curl_requests.RequestsError("404 Not Found")
    )

    with patch("core.benfica_calendar.requests.get") as mock_get:
        mock_get.return_value = mock_curl_response

        with patch("core.benfica_calendar.requests.post") as mock_post:
            mock_post.return_value = mock_api_response

            calendar = Calendar()

            with pytest.raises(curl_requests.RequestsError):
                calendar.get_events()


def test_get_events_timeout(mock_curl_response):
    """Test get_events handles timeout errors."""
    with patch("core.benfica_calendar.requests.get") as mock_get:
        mock_get.return_value = mock_curl_response

        with patch("core.benfica_calendar.requests.post") as mock_post:
            mock_post.side_effect = curl_requests.RequestsError(
                "Request timed out"
            )

            calendar = Calendar()

            with pytest.raises(curl_requests.RequestsError):
                calendar.get_events()


# Additional edge case tests


def test_parse_match_from_event_malformed_date():
    """Test parsing event with malformed date."""
    event = {
        "MatchDate": "not-a-valid-date",
        "AdversaryName": "FC Porto",
        "StadiumName": "Estádio da Luz",
        "TournamentName": "Liga Portugal",
        "IsHome": True,
    }

    result = _parse_match_from_event(event)

    # Should handle error gracefully and return None
    assert result is None


def test_parse_match_from_event_with_z_suffix():
    """Test parsing date with Z suffix (UTC indicator)."""
    future_date = pendulum.now("UTC").add(days=7)
    event = {
        "MatchDate": future_date.format("YYYY-MM-DDTHH:mm:ss") + "Z",
        "AdversaryName": "Sporting CP",
        "StadiumName": "Estádio José Alvalade",
        "TournamentName": "Taça de Portugal",
        "IsHome": False,
    }

    result = _parse_match_from_event(event)

    # Should parse correctly and convert to Lisbon timezone
    assert result is not None
    assert result["adversary"] == "Sporting CP"
    assert result["home"] == "Fora"


def test_parse_match_from_event_missing_optional_fields():
    """Test parsing event with missing optional fields uses defaults."""
    future_date = pendulum.now("Europe/Lisbon").add(days=3)
    event = {
        "MatchDate": future_date.to_iso8601_string(),
        # Missing all optional fields
    }

    result = _parse_match_from_event(event)

    assert result is not None
    assert result["adversary"] == "Unknown"
    assert result["location"] == "Unknown"
    assert result["competition"] == "Unknown"
    assert result["home"] == "Casa"  # Default is True


def test_parse_match_from_event_exactly_now():
    """Test parsing event that is happening right now (edge case)."""
    now = pendulum.now("Europe/Lisbon")
    event = {
        "MatchDate": now.to_iso8601_string(),
        "AdversaryName": "FC Porto",
        "StadiumName": "Estádio da Luz",
        "TournamentName": "Liga Portugal",
        "IsHome": True,
    }

    result = _parse_match_from_event(event)

    # Matches happening now or in the past should return None
    assert result is None


def test_get_next_match_from_api_empty_list():
    """Test API with empty list."""
    mock_calendar = MagicMock()
    mock_calendar.get_events.return_value = []

    with patch("core.benfica_calendar.Calendar", return_value=mock_calendar):
        result = get_next_match_from_api()

        assert result is None


def test_get_next_match_from_api_none_response():
    """Test API returns None."""
    mock_calendar = MagicMock()
    mock_calendar.get_events.return_value = None

    with patch("core.benfica_calendar.Calendar", return_value=mock_calendar):
        result = get_next_match_from_api()

        assert result is None
