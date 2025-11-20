import json
import logging
import re
import time
from io import BytesIO

from bs4 import BeautifulSoup
from curl_cffi import requests
from discord import File as DFile
from PIL import Image
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from gen_browser import gen_browser

logger = logging.getLogger(__name__)

# Tournament and fallback configuration
TOURNAMENT_ID = 238  # Liga Portugal Betclic
TOURNAMENT_URL = (
    "https://www.sofascore.com/tournament/football/portugal/"
    "liga-portugal/238"
)
TRANSFERMARKT_URL = (
    "https://www.transfermarkt.com/liga-portugal/startseite/wettbewerb/PO1"
)

# Round ID calculation: Based on observation, SofaScore round_id =
# BASE_ROUND_ID + matchday. This was derived from: Matchday 13 → Round ID
# 22537, therefore base = 22537 - 13 = 22524. Note: This may need
# adjustment if SofaScore changes their ID scheme
BASE_ROUND_ID = 22524

# Fallback widget URL (will be used if dynamic extraction fails)
FALLBACK_WIDGET_URL = (
    "https://widgets.sofascore.com/embed/unique-tournament/238/season/77806/"
    "round/22537/teamOfTheWeek?showCompetitionLogo=true&widgetTheme=light"
    "&widgetTitle=Liga%20Portugal%20Betclic"
)
PAGE_LOAD_TIMEOUT = 10

# Cache for season ID and matchday to avoid repeated lookups
_cached_season_id: int | None = None
_cached_matchday: int | None = None


def _extract_current_matchday() -> int | None:
    """Extract current matchday from Transfermarkt.

    Uses a cache to avoid repeated lookups during the same bot session.

    Returns:
        Matchday number if found, None otherwise.
    """
    global _cached_matchday

    # Return cached value if available
    if _cached_matchday is not None:
        logger.info(f"Using cached matchday: {_cached_matchday}")
        return _cached_matchday

    try:
        logger.info(f"Extracting current matchday from {TRANSFERMARKT_URL}")
        response = requests.get(
            TRANSFERMARKT_URL, impersonate="chrome", timeout=10
        )

        if response.status_code != 200:
            logger.warning(
                f"Failed to fetch Transfermarkt page: {response.status_code}"
            )
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # Find all matchday mentions
        matchday_pattern = re.compile(
            r"(?i)(?:All games from )?(?:matchday|jornada|round)\s+(\d+)"
        )
        texts = soup.find_all(string=matchday_pattern)

        matchdays = []
        for text in texts:
            match = matchday_pattern.search(text)
            if match:
                matchday_num = int(match.group(1))
                matchdays.append(matchday_num)

        if matchdays:
            # Use the highest matchday number (most recent)
            current_matchday = max(matchdays)
            logger.info(f"Found current matchday: {current_matchday}")

            # Cache the result
            _cached_matchday = current_matchday
            return current_matchday
        else:
            logger.warning("No matchdays found on Transfermarkt page")
            return None

    except Exception as e:
        logger.warning(f"Failed to extract matchday: {e}")
        return None


def _extract_current_season() -> int | None:
    """Extract current season ID from SofaScore tournament page.

    Uses requests instead of Selenium for better performance.
    Uses a cache to avoid repeated lookups during the same bot session.

    Returns:
        Season ID if found, None otherwise.
    """
    global _cached_season_id

    # Return cached value if available
    if _cached_season_id is not None:
        logger.info(f"Using cached season ID: {_cached_season_id}")
        return _cached_season_id

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

            # Cache the result
            _cached_season_id = season_id
            return season_id
        else:
            logger.warning("No seasons found in page data")
            return None

    except Exception as e:
        logger.warning(f"Failed to extract season ID: {e}")
        return None


def _build_widget_url(
    season_id: int | None = None, matchday: int | None = None
) -> str:
    """Build widget URL with current season and matchday, or use fallback.

    The widget URL requires both season and round parameters. The round ID
    is calculated from the matchday using:
    round_id = BASE_ROUND_ID + matchday.

    Args:
        season_id: Season ID to use. If None, uses fallback URL.
        matchday: Current matchday number. If None, extracts from
            fallback URL.

    Returns:
        Widget URL string.
    """
    if season_id is None and matchday is None:
        logger.info("Using fallback widget URL")
        return FALLBACK_WIDGET_URL

    # Calculate round ID from matchday
    if matchday is not None:
        round_id = BASE_ROUND_ID + matchday
        logger.info(f"Calculated round ID {round_id} from matchday {matchday}")
    else:
        # Extract the round ID from the fallback URL
        round_match = re.search(r"/round/(\d+)/", FALLBACK_WIDGET_URL)
        if not round_match:
            logger.warning("Could not extract round from fallback URL")
            return FALLBACK_WIDGET_URL
        round_id = int(round_match.group(1))
        logger.info(f"Using fallback round ID: {round_id}")

    # Use provided season_id or extract from fallback
    if season_id is None:
        season_match = re.search(r"/season/(\d+)/", FALLBACK_WIDGET_URL)
        if not season_match:
            logger.warning("Could not extract season from fallback URL")
            return FALLBACK_WIDGET_URL
        season_id = int(season_match.group(1))
        logger.info(f"Using fallback season ID: {season_id}")

    # Build URL with dynamic season and round
    url = (
        f"https://widgets.sofascore.com/embed/unique-tournament/"
        f"{TOURNAMENT_ID}/season/{season_id}/round/{round_id}/"
        "teamOfTheWeek?showCompetitionLogo=true&widgetTheme=light"
        "&widgetTitle=Liga%20Portugal%20Betclic"
    )
    logger.info(
        f"Built widget URL with season {season_id} and round {round_id}"
    )
    return url


def fetch_team_week() -> DFile:
    """Fetch team of the week screenshot from SofaScore widget.

    Automatically extracts the current season ID and matchday, then builds
    the widget URL dynamically. Falls back to a hardcoded URL if extraction
    fails.

    Returns:
        Discord File object containing team of the week screenshot.

    Raises:
        Exception: If screenshot capture fails.
    """
    # Try to extract current season ID and matchday
    season_id = _extract_current_season()
    matchday = _extract_current_matchday()

    # Build widget URL (will use fallback if both are None)
    widget_url = _build_widget_url(season_id, matchday)

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
