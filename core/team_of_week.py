import json
import logging
import re
import time
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any

from curl_cffi import requests
from discord import File as DFile
from PIL import Image
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from core.browser import gen_browser

logger = logging.getLogger(__name__)

# Tournament and fallback configuration
TOURNAMENT_ID = 238  # Liga Portugal Betclic
TOURNAMENT_URL = (
    "https://www.sofascore.com/tournament/football/portugal/liga-portugal/238"
)
# API endpoint that provides TOTW rounds with actual round IDs
SOFASCORE_TOTW_ROUNDS_API = (
    "https://api.sofascore.com/api/v1/unique-tournament/{tournament_id}/"
    "season/{season_id}/team-of-the-week/rounds"
)

# Fallback widget URL (will be used if dynamic extraction fails)
# Updated for 2025/26 season, round 13
FALLBACK_WIDGET_URL = (
    "https://widgets.sofascore.com/embed/unique-tournament/238/season/77806/"
    "round/23075/teamOfTheWeek?showCompetitionLogo=true&widgetTheme=light"
    "&widgetTitle=Liga%20Portugal%20Betclic"
)
PAGE_LOAD_TIMEOUT = 10

# Cache for season ID and matchday with time-based expiration


class CacheEntry:
    """Cache entry with expiration time."""

    def __init__(self, value: Any, expiry_hours: int = 24):
        """Initialize cache entry.

        Args:
            value: Value to cache.
            expiry_hours: Hours until cache expires (default: 24).
        """
        self.value = value
        self.expiry = datetime.now() + timedelta(hours=expiry_hours)

    def is_expired(self) -> bool:
        """Check if cache entry is expired.

        Returns:
            True if expired, False otherwise.
        """
        return datetime.now() > self.expiry


# Cache dictionary with time-based expiration
_cache: dict[str, CacheEntry] = {}


def _get_cached(key: str) -> Any | None:
    """Get cached value if not expired.

    Args:
        key: Cache key.

    Returns:
        Cached value or None if not found or expired.
    """
    if key in _cache and not _cache[key].is_expired():
        return _cache[key].value
    return None


def _set_cached(key: str, value: Any, expiry_hours: int = 24) -> None:
    """Set cached value with expiry.

    Args:
        key: Cache key.
        value: Value to cache.
        expiry_hours: Hours until cache expires (default: 24).
    """
    _cache[key] = CacheEntry(value, expiry_hours)


def _get_latest_totw_round_id(season_id: int) -> int | None:
    """Get the latest Team of the Week round ID from SofaScore API.

    Uses SofaScore's TOTW-specific API to get the most recent published
    Team of the Week. This API returns rounds in reverse chronological order
    (newest first), so the first entry is the latest TOTW available.
    Uses a cache (1h expiry) to avoid repeated lookups.

    Args:
        season_id: SofaScore season ID to query.

    Returns:
        Round ID (internal SofaScore ID) if found, None otherwise.
    """
    # Return cached value if available and not expired
    cached = _get_cached("totw_round_id")
    if cached is not None:
        logger.info(f"Using cached TOTW round ID: {cached}")
        return cached

    try:
        # Build API URL with tournament and season IDs
        api_url = SOFASCORE_TOTW_ROUNDS_API.format(
            tournament_id=TOURNAMENT_ID, season_id=season_id
        )
        logger.info(f"Fetching latest TOTW round from API: {api_url}")

        response = requests.get(api_url, impersonate="chrome", timeout=10)

        if response.status_code != 200:
            logger.warning(
                f"Failed to fetch TOTW rounds API: {response.status_code}"
            )
            return None

        data = response.json()
        rounds = data.get("rounds", [])

        if not rounds:
            logger.warning("No TOTW rounds found in API response")
            return None

        # Rounds are ordered newest first, so first entry is latest TOTW
        latest_round = rounds[0]
        round_id = latest_round.get("id")
        round_num = latest_round.get("roundId")

        if round_id is not None:
            logger.info(
                f"Found latest TOTW: Round {round_num} (ID: {round_id})"
            )

            # Cache the result for 1 hour (shorter than season since TOTW
            # updates weekly)
            _set_cached("totw_round_id", round_id, expiry_hours=1)
            return round_id
        else:
            logger.warning("No round ID found in latest TOTW entry")
            return None

    except Exception as e:
        logger.warning(f"Failed to extract TOTW round ID from API: {e}")
        return None


def _extract_current_season() -> int | None:
    """Extract current season ID from SofaScore tournament page.

    Uses requests instead of Selenium for better performance.
    Uses a cache (24h expiry) to avoid repeated lookups.

    Returns:
        Season ID if found, None otherwise.
    """
    # Return cached value if available and not expired
    cached = _get_cached("season_id")
    if cached is not None:
        logger.info(f"Using cached season ID: {cached}")
        return cached

    try:
        logger.info(f"Extracting current season from {TOURNAMENT_URL}")
        response = requests.get(
            TOURNAMENT_URL, impersonate="chrome", timeout=10
        )

        if response.status_code != 200:
            logger.warning(
                f"Failed to fetch SofaScore page: {response.status_code}"
            )
            return None

        # Extract Next.js data from __NEXT_DATA__ script tag using regex
        # Pattern: <script id="__NEXT_DATA__"
        # type="application/json">...</script>
        match = re.search(
            r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
            response.text,
            re.DOTALL,
        )

        if not match:
            logger.warning("Could not find __NEXT_DATA__ script tag")
            return None

        data = json.loads(match.group(1))

        # Navigate to seasons array
        seasons = (
            data.get("props", {})
            .get("pageProps", {})
            .get("initialProps", {})
            .get("seasons", [])
        )

        if seasons and len(seasons) > 0:
            # First season is the current one
            current_season = seasons[0]
            season_id = current_season.get("id")
            season_year = current_season.get("year", "unknown")

            logger.info(
                f"Found current season: ID={season_id}, Year={season_year}"
            )

            # Cache the result for 24 hours
            _set_cached("season_id", season_id, expiry_hours=24)
            return season_id
        else:
            logger.warning("No seasons found in page data")
            return None

    except Exception as e:
        logger.warning(f"Failed to extract season ID: {e}")
        return None


def _build_widget_url(
    season_id: int | None = None, round_id: int | None = None
) -> str:
    """Build widget URL with current season and round ID, or use fallback.

    Args:
        season_id: Season ID to use. If None, uses fallback URL.
        round_id: Round ID (internal SofaScore ID) from TOTW API. If None,
            uses fallback URL.

    Returns:
        Widget URL string.
    """
    if season_id is None or round_id is None:
        logger.info("Using fallback widget URL (missing season or round ID)")
        return FALLBACK_WIDGET_URL

    # Build URL with dynamic season and round
    url = (
        f"https://widgets.sofascore.com/embed/unique-tournament/"
        f"{TOURNAMENT_ID}/season/{season_id}/round/{round_id}/"
        "teamOfTheWeek?showCompetitionLogo=true&widgetTheme=light"
        "&widgetTitle=Liga%20Portugal%20Betclic"
    )
    logger.info(
        f"Built widget URL with season {season_id} and round ID {round_id}"
    )
    return url


def fetch_team_week() -> DFile:
    """Fetch team of the week screenshot from SofaScore widget.

    Automatically extracts the current season ID and latest TOTW round ID,
    then builds the widget URL dynamically. Falls back to a hardcoded URL
    if extraction fails.

    Returns:
        Discord File object containing team of the week screenshot.

    Raises:
        Exception: If screenshot capture fails.
    """
    # Try to extract current season ID first
    season_id = _extract_current_season()

    # Get the latest TOTW round ID from the API
    round_id = None
    if season_id is not None:
        round_id = _get_latest_totw_round_id(season_id)

    # Build widget URL (will use fallback if either is None)
    widget_url = _build_widget_url(season_id, round_id)

    browser = gen_browser()
    try:
        logger.info("Navigating to SofaScore TOTW widget")
        browser.get(widget_url)

        # Wait for the widget content to load
        # The widget has a div with team of the week data
        wait = WebDriverWait(browser, PAGE_LOAD_TIMEOUT)
        wait.until(
            expected_conditions.presence_of_element_located(
                (By.TAG_NAME, "body")
            )
        )
        logger.info("Widget loaded")

        # Give time for all player images to load
        time.sleep(3)

        # Take screenshot
        logger.info("Taking screenshot")
        screenshot_bytes = browser.get_screenshot_as_png()

        # Open image with PIL for cropping
        img = Image.open(BytesIO(screenshot_bytes))
        width, height = img.size

        # Crop to remove excessive white space and branding at bottom
        # Keep top portion with team formation (roughly 75% of height)
        crop_height = int(height * 0.75)
        cropped_img = img.crop((0, 0, width, crop_height))

        # Save cropped image to BytesIO
        img_bytes = BytesIO()
        cropped_img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        logger.info(
            f"Team of the week screenshot captured and cropped "
            f"({width}x{crop_height})"
        )
        return DFile(img_bytes, filename="image.png")
    except Exception as e:
        logger.error(f"Failed to capture team of the week: {e}")
        raise
    finally:
        browser.quit()


if __name__ == "__main__":
    # Test the team of the week scraper
    import logging

    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s - %(message)s"
    )

    try:
        print("\nFetching team of the week...")
        discord_file = fetch_team_week()

        # Save to local file for inspection
        output_path = "totw_test.png"
        with open(output_path, "wb") as f:
            discord_file.fp.seek(0)  # Reset file pointer
            f.write(discord_file.fp.read())

        print(f"\n✅ Success! Screenshot saved to {output_path}")
        print(f"File size: {discord_file.fp.tell()} bytes")
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        import traceback

        traceback.print_exc()
