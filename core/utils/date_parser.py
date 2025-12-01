"""Date parsing utilities for Benfica Discord Bot.

Centralizes all date parsing logic to ensure consistency across the codebase.
Supports multiple input formats from different data sources.
"""

import logging
from datetime import datetime
from typing import Any

import pendulum

from config.constants import TIMEZONE

logger = logging.getLogger(__name__)


def parse_dd_mm_yyyy_time(
    date_str: str, time_str: str, timezone: str = TIMEZONE
) -> pendulum.DateTime:
    """Parse DD-MM-YYYY date and HH:mm time into pendulum datetime.

    Used by:
    - Benfica Calendar API responses
    - Match data normalization
    - Discord event creation

    Args:
        date_str: Date in DD-MM-YYYY format (e.g., "29-11-2025")
        time_str: Time in HH:mm format (e.g., "18:00")
        timezone: Timezone name (default: Europe/Lisbon)

    Returns:
        Timezone-aware pendulum datetime

    Raises:
        ValueError: If strings are invalid or cannot be parsed
    """
    try:
        date_parts = date_str.split("-")
        time_parts = time_str.split(":")

        if len(date_parts) != 3 or len(time_parts) != 2:
            raise ValueError(
                f"Invalid format: date='{date_str}', time='{time_str}'"
            )

        return pendulum.datetime(
            year=int(date_parts[2]),
            month=int(date_parts[1]),
            day=int(date_parts[0]),
            hour=int(time_parts[0]),
            minute=int(time_parts[1]),
            tz=timezone,
        )
    except (ValueError, IndexError) as e:
        logger.error(f"Parse error: date='{date_str}', time='{time_str}': {e}")
        raise ValueError(
            f"Invalid date/time format: '{date_str}' '{time_str}'"
        ) from e


def parse_iso_datetime(
    datetime_str: str, timezone: str = TIMEZONE
) -> pendulum.DateTime:
    """Parse ISO 8601 datetime into pendulum datetime.

    Used by ESPN API and Benfica Calendar API responses.

    Args:
        datetime_str: ISO 8601 string (e.g., "2025-11-29T18:00:00Z")
        timezone: Target timezone (default: Europe/Lisbon)

    Returns:
        Timezone-aware pendulum datetime in specified timezone

    Raises:
        ValueError: If datetime_str is invalid
    """
    try:
        clean_str = datetime_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        return pendulum.instance(dt).in_timezone(timezone)
    except (ValueError, AttributeError) as e:
        logger.error(f"ISO parse error: '{datetime_str}': {e}")
        raise ValueError(f"Invalid ISO datetime: '{datetime_str}'") from e


def parse_us_datetime_12h(
    datetime_str: str, timezone: str = TIMEZONE
) -> pendulum.DateTime:
    """Parse US-style 12-hour datetime into pendulum datetime.

    Format: "MM/DD/YYYY HH:MM:SS AM/PM"
    Used by Benfica Calendar calendar export fields.

    Args:
        datetime_str: US datetime (e.g., "11/29/2025 6:00:00 PM")
        timezone: Timezone to assign (default: Europe/Lisbon)

    Returns:
        Timezone-aware pendulum datetime

    Raises:
        ValueError: If datetime_str is invalid
    """
    try:
        dt = datetime.strptime(datetime_str, "%m/%d/%Y %I:%M:%S %p")
        return pendulum.instance(dt, tz=timezone)
    except ValueError as e:
        logger.error(f"US datetime parse error: '{datetime_str}': {e}")
        raise ValueError(f"Invalid US datetime: '{datetime_str}'") from e


def parse_match_data_dict(
    match_data: dict[str, Any], timezone: str = TIMEZONE
) -> pendulum.DateTime:
    """Parse match_data.json dictionary into pendulum datetime.

    Supports old format with separate fields: year, month, day, hour, minute
    Maintains backward compatibility with existing match_data.json files.

    Args:
        match_data: Dict with year, month, day, hour, minute integer fields
        timezone: Timezone to assign (default: Europe/Lisbon)

    Returns:
        Timezone-aware pendulum datetime

    Raises:
        ValueError: If match_data is missing required fields or invalid
    """
    try:
        return pendulum.datetime(
            year=int(match_data["year"]),
            month=int(match_data["month"]),
            day=int(match_data["day"]),
            hour=int(match_data["hour"]),
            minute=int(match_data["minute"]),
            tz=timezone,
        )
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Match data parse error: {match_data}: {e}")
        raise ValueError("Invalid match data format") from e


def format_to_dd_mm_yyyy(dt: pendulum.DateTime) -> str:
    """Format pendulum datetime to DD-MM-YYYY string.

    Args:
        dt: Pendulum datetime to format

    Returns:
        Date string in DD-MM-YYYY format
    """
    return dt.format("DD-MM-YYYY")


def format_to_hh_mm(dt: pendulum.DateTime) -> str:
    """Format pendulum datetime to HH:mm string.

    Args:
        dt: Pendulum datetime to format

    Returns:
        Time string in HH:mm format
    """
    return dt.format("HH:mm")
