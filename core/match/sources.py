"""Match data sources - Benfica API (primary) and ESPN (fallback)."""

import json
import logging
import re
from datetime import datetime

import requests
from fake_useragent import UserAgent

from core.benfica_calendar import get_next_match_from_api
from core.retry import retry_on_failure
from core.utils.date_parser import parse_dd_mm_yyyy_time

logger = logging.getLogger(__name__)

# ESPN configuration
ESPN_URL = "https://www.espn.com/soccer/team/fixtures/_/id/1929"

# Initialize user agent generator
ua = UserAgent()


def _get_headers() -> dict:
    """Generate realistic browser headers.

    Returns:
        Dictionary with User-Agent header.
    """
    return {"User-Agent": ua.random}


@retry_on_failure(
    max_attempts=3,
    delay=1.0,
    exceptions=(requests.RequestException, TimeoutError),
)
def get_next_match_from_espn() -> dict | None:
    """Scrape next match from ESPN (fallback source).

    Returns:
        Dict with match data (date, adversary, location, competition)
        or None if no match found or error occurs.
    """
    try:
        logger.info(f"Fetching ESPN fixtures from {ESPN_URL}")
        response = requests.get(ESPN_URL, headers=_get_headers(), timeout=30)
        response.raise_for_status()
        logger.info(f"Page fetched successfully ({len(response.text)} bytes)")

        # Extract embedded JSON data from window['__espnfitt__']
        pattern = r"window\['__espnfitt__'\]\s*=\s*({.*?});"
        matches = re.findall(pattern, response.text, re.DOTALL)

        if not matches:
            logger.error("Could not find __espnfitt__ data in page")
            return None

        logger.info("Found __espnfitt__ data, parsing JSON...")
        data = json.loads(matches[0])

        # Navigate to fixtures
        fixtures = data.get("page", {}).get("content", {}).get("fixtures", {})
        events = fixtures.get("events", [])

        if not events:
            logger.error("No events found in fixtures data")
            return None

        logger.info(f"Found {len(events)} upcoming matches")

        # Get first event (they're sorted chronologically)
        event = events[0]

        # Extract match data
        date_str = event.get("date")
        if not date_str:
            logger.error("No date in first event")
            return None

        # Parse ISO 8601 date
        match_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

        # Get competition info
        competition = event.get("league", "Unknown Competition")

        # Get teams (directly from event.competitors)
        competitors = event.get("competitors", [])
        home_team = away_team = None
        for team in competitors:
            if team.get("isHome"):
                home_team = team.get("displayName")
            else:
                away_team = team.get("displayName")

        # Determine adversary and home/away status
        if home_team and "Benfica" in home_team:
            adversary = away_team or "Unknown"
            is_home = True
        else:
            adversary = home_team or "Unknown"
            is_home = False

        # Get venue
        venue = event.get("venue", {})
        location = venue.get("fullName", "Unknown Venue")

        # Try to extract TV channel from broadcasts
        tv_channel = None
        broadcasts = event.get("broadcasts")
        if broadcasts and isinstance(broadcasts, list) and len(broadcasts) > 0:
            # Get first broadcast entry
            first_broadcast = broadcasts[0]
            if isinstance(first_broadcast, dict):
                tv_channel = first_broadcast.get("name")

        match_data = {
            "date": match_date,
            "adversary": adversary,
            "location": location,
            "competition": competition,
            "is_home": is_home,
        }

        # Add TV channel if available
        if tv_channel:
            match_data["tv_channel"] = tv_channel

        logger.info(
            f"Match data scraped: {adversary} on {match_date} at {location}"
        )
        return match_data

    except requests.RequestException as e:
        logger.error(f"HTTP request failed: {e}", exc_info=True)
        return None
    except (json.JSONDecodeError, KeyError, IndexError, ValueError) as e:
        logger.error(f"Failed to parse ESPN data: {e}", exc_info=True)
        return None


def normalize_match_data(match_data: dict, source: str) -> dict:
    """Normalize match data from different sources to standard format.

    Args:
        match_data: Raw match data from API or scraper.
        source: Source of data ("benfica_api" or "espn").

    Returns:
        Normalized dict with datetime object and consistent keys.
    """
    if source == "benfica_api":
        # Benfica API returns: date="DD-MM-YYYY", time="HH:mm",
        # home="Casa"/"Fora"
        match_dt = parse_dd_mm_yyyy_time(
            match_data["date"], match_data["time"]
        )
        normalized = {
            "date": match_dt,
            "adversary": match_data["adversary"],
            "location": match_data["location"],
            "competition": match_data["competition"],
            "is_home": match_data["home"] == "Casa",
        }
        # Include TV channel if available
        if "tv_channel" in match_data and match_data["tv_channel"]:
            normalized["tv_channel"] = match_data["tv_channel"]
        return normalized
    else:  # espn
        # ESPN already returns datetime object and is_home boolean
        return match_data


def fetch_next_match() -> dict | None:
    """Fetch next match using hybrid approach (Benfica API + ESPN fallback).

    Tries to fetch match data from Benfica's official API first.
    Falls back to ESPN scraping if API fails.

    Returns:
        Normalized dict with match data or None if both sources fail.
    """
    # Try Benfica API first (more reliable, official source)
    logger.info("Attempting to fetch match data from Benfica API")
    match_data = get_next_match_from_api()

    if match_data is not None:
        # Normalize Benfica API data format
        return normalize_match_data(match_data, "benfica_api")

    # Fallback to ESPN if API fails
    logger.warning("Benfica API failed, falling back to ESPN scraping")
    match_data = get_next_match_from_espn()

    if match_data is not None:
        return normalize_match_data(match_data, "espn")

    logger.error("Failed to get match data from both sources")
    return None
