"""Auto-refresh logic for match data."""

import logging

import pendulum

from config.constants import TIMEZONE
from core.match.repository import (
    load_match_data,
    match_data_to_pendulum,
    save_match_data,
)
from core.match.sources import fetch_next_match

logger = logging.getLogger(__name__)


def update_match_data() -> bool:
    """Update match data using hybrid approach (Benfica API + ESPN fallback).

    Tries to fetch match data from Benfica's official API first.
    Falls back to ESPN scraping if API fails.

    Returns:
        True if update successful, False otherwise.
    """
    match_data = fetch_next_match()

    if match_data is None:
        logger.error("Failed to get match data from both sources")
        return False

    save_match_data(match_data)
    logger.info("Match data updated successfully")
    return True


def get_match_data_with_refresh() -> tuple[dict | None, bool]:
    """Get match data, automatically refreshing if it's in the past.

    Returns:
        Tuple of (match_data dict or None, was_refreshed bool).
    """
    try:
        match_data = load_match_data()
    except FileNotFoundError:
        return None, False

    # Check if match is in the past
    match_dt = match_data_to_pendulum(match_data)
    now_lisbon = pendulum.now(TIMEZONE)

    if match_dt < now_lisbon:
        # Match is in the past, refresh data
        logger.info("Stored match is in the past, refreshing from sources")
        success = update_match_data()

        if not success:
            logger.warning("No upcoming matches found")
            return None, False

        # Re-read the updated data
        match_data = load_match_data()
        match_dt = match_data_to_pendulum(match_data)

        # Double-check the new data isn't also in the past
        if match_dt < now_lisbon:
            logger.warning("Refreshed match is still in the past")
            return None, False

        return match_data, True

    return match_data, False
