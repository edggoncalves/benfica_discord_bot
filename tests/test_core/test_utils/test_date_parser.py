"""Tests for date parsing utilities."""

import pendulum
import pytest

from core.utils.date_parser import (
    format_to_dd_mm_yyyy,
    format_to_hh_mm,
    parse_dd_mm_yyyy_time,
    parse_iso_datetime,
    parse_match_data_dict,
    parse_us_datetime_12h,
)


class TestParseDdMmYyyyTime:
    """Tests for parse_dd_mm_yyyy_time function."""

    def test_valid_date_time(self):
        """Test parsing valid DD-MM-YYYY HH:mm format."""
        dt = parse_dd_mm_yyyy_time("29-11-2025", "18:00")
        assert dt.year == 2025
        assert dt.month == 11
        assert dt.day == 29
        assert dt.hour == 18
        assert dt.minute == 0
        assert dt.timezone_name == "Europe/Lisbon"

    def test_valid_with_single_digit_time(self):
        """Test parsing with single digit hour."""
        dt = parse_dd_mm_yyyy_time("05-12-2025", "20:15")
        assert dt.year == 2025
        assert dt.month == 12
        assert dt.day == 5
        assert dt.hour == 20
        assert dt.minute == 15

    def test_midnight(self):
        """Test parsing midnight time."""
        dt = parse_dd_mm_yyyy_time("01-01-2025", "00:00")
        assert dt.hour == 0
        assert dt.minute == 0

    def test_custom_timezone(self):
        """Test specifying custom timezone."""
        dt = parse_dd_mm_yyyy_time("29-11-2025", "18:00", timezone="UTC")
        assert dt.timezone_name == "UTC"

    def test_invalid_date_format_wrong_order(self):
        """Test error handling for wrong date format (YYYY-MM-DD)."""
        with pytest.raises(ValueError, match="Invalid date/time format"):
            parse_dd_mm_yyyy_time("2025-11-29", "18:00")

    def test_invalid_date_format_too_few_parts(self):
        """Test error handling for incomplete date."""
        with pytest.raises(ValueError, match="Invalid date/time format"):
            parse_dd_mm_yyyy_time("29-11", "18:00")

    def test_invalid_time_format(self):
        """Test error handling for wrong time format."""
        with pytest.raises(ValueError, match="Invalid date/time format"):
            parse_dd_mm_yyyy_time("29-11-2025", "18")

    def test_invalid_date_values(self):
        """Test error handling for invalid date values."""
        with pytest.raises(ValueError, match="Invalid date/time format"):
            parse_dd_mm_yyyy_time("32-13-2025", "18:00")


class TestParseIsoDatetime:
    """Tests for parse_iso_datetime function."""

    def test_iso_with_z_suffix(self):
        """Test parsing ISO datetime with Z suffix."""
        dt = parse_iso_datetime("2025-11-29T18:00:00Z")
        assert dt.year == 2025
        assert dt.month == 11
        assert dt.day == 29
        # Note: Hour will be converted to Lisbon time
        assert dt.timezone_name == "Europe/Lisbon"

    def test_iso_with_offset(self):
        """Test parsing ISO datetime with timezone offset."""
        dt = parse_iso_datetime("2025-11-29T18:00:00+00:00")
        assert dt.year == 2025
        assert dt.month == 11
        assert dt.day == 29

    def test_custom_timezone(self):
        """Test converting to custom timezone."""
        dt = parse_iso_datetime(
            "2025-11-29T18:00:00Z", timezone="America/New_York"
        )
        assert dt.timezone_name == "America/New_York"

    def test_invalid_iso_format(self):
        """Test error handling for invalid ISO format."""
        with pytest.raises(ValueError, match="Invalid ISO datetime"):
            parse_iso_datetime("not-a-date")


class TestParseUsDdatetime12h:
    """Tests for parse_us_datetime_12h function."""

    def test_valid_pm_time(self):
        """Test parsing PM time."""
        dt = parse_us_datetime_12h("11/29/2025 6:00:00 PM")
        assert dt.year == 2025
        assert dt.month == 11
        assert dt.day == 29
        assert dt.hour == 18  # 6 PM = 18:00

    def test_valid_am_time(self):
        """Test parsing AM time."""
        dt = parse_us_datetime_12h("11/29/2025 6:00:00 AM")
        assert dt.hour == 6

    def test_noon(self):
        """Test parsing noon (12 PM)."""
        dt = parse_us_datetime_12h("11/29/2025 12:00:00 PM")
        assert dt.hour == 12

    def test_midnight_12h(self):
        """Test parsing midnight (12 AM)."""
        dt = parse_us_datetime_12h("11/29/2025 12:00:00 AM")
        assert dt.hour == 0

    def test_invalid_format(self):
        """Test error handling for invalid format."""
        with pytest.raises(ValueError, match="Invalid US datetime"):
            parse_us_datetime_12h("11-29-2025 6:00 PM")


class TestParseMatchDataDict:
    """Tests for parse_match_data_dict function."""

    def test_valid_match_data(self):
        """Test parsing valid match_data.json format."""
        data = {
            "year": 2025,
            "month": 11,
            "day": 29,
            "hour": 18,
            "minute": 0,
        }
        dt = parse_match_data_dict(data)
        assert dt.year == 2025
        assert dt.month == 11
        assert dt.day == 29
        assert dt.hour == 18
        assert dt.minute == 0
        assert dt.timezone_name == "Europe/Lisbon"

    def test_custom_timezone(self):
        """Test specifying custom timezone."""
        data = {
            "year": 2025,
            "month": 11,
            "day": 29,
            "hour": 18,
            "minute": 0,
        }
        dt = parse_match_data_dict(data, timezone="UTC")
        assert dt.timezone_name == "UTC"

    def test_missing_field(self):
        """Test error when required field is missing."""
        data = {"year": 2025, "month": 11, "day": 29}
        with pytest.raises(ValueError, match="Invalid match data format"):
            parse_match_data_dict(data)

    def test_invalid_type(self):
        """Test error when field has wrong type."""
        data = {
            "year": "2025",  # String instead of int
            "month": 11,
            "day": 29,
            "hour": 18,
            "minute": 0,
        }
        # Should still work due to int() conversion
        dt = parse_match_data_dict(data)
        assert dt.year == 2025


class TestFormatFunctions:
    """Tests for date formatting functions."""

    def test_format_to_dd_mm_yyyy(self):
        """Test formatting datetime to DD-MM-YYYY."""
        dt = pendulum.datetime(2025, 11, 29, tz="Europe/Lisbon")
        assert format_to_dd_mm_yyyy(dt) == "29-11-2025"

    def test_format_to_dd_mm_yyyy_single_digit(self):
        """Test formatting with single digit day/month."""
        dt = pendulum.datetime(2025, 1, 5, tz="Europe/Lisbon")
        assert format_to_dd_mm_yyyy(dt) == "05-01-2025"

    def test_format_to_hh_mm(self):
        """Test formatting datetime to HH:mm."""
        dt = pendulum.datetime(2025, 11, 29, 18, 0, tz="Europe/Lisbon")
        assert format_to_hh_mm(dt) == "18:00"

    def test_format_to_hh_mm_single_digit(self):
        """Test formatting with single digit hour/minute."""
        dt = pendulum.datetime(2025, 11, 29, 9, 5, tz="Europe/Lisbon")
        assert format_to_hh_mm(dt) == "09:05"

    def test_format_to_hh_mm_midnight(self):
        """Test formatting midnight."""
        dt = pendulum.datetime(2025, 11, 29, 0, 0, tz="Europe/Lisbon")
        assert format_to_hh_mm(dt) == "00:00"
