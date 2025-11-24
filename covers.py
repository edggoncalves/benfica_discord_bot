import logging
import re
from io import BytesIO

import aiohttp
from bs4 import BeautifulSoup, element
from PIL import Image

logger = logging.getLogger(__name__)

URL = "https://24.sapo.pt/jornais/desporto"
# Changed to match img alt attributes
NEWSPAPERS = ("a-bola", "o-jogo", "record")
MAX_RETRIES = 3
REQUEST_TIMEOUT = 5.0


async def _fetch_html(url: str) -> bytes | None:
    """Fetch HTML content from URL with retry logic.

    Args:
        url: URL to fetch.

    Returns:
        Raw HTML bytes or None if all retries failed.
    """
    for attempt in range(MAX_RETRIES):
        try:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    return await response.read()
        except aiohttp.ClientError as e:
            if attempt < MAX_RETRIES - 1:
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{MAX_RETRIES}), "
                    f"retrying... Error: {e}"
                )
            else:
                logger.error(f"Max retries exceeded for {url}. Error: {e}")
                return None
        except TimeoutError:
            logger.warning(
                f"Request timeout (attempt {attempt + 1}/{MAX_RETRIES})"
            )
            if attempt == MAX_RETRIES - 1:
                logger.error(f"Max retries exceeded for {url} (timeout)")
                return None
    return None


async def _get_pictures() -> element.ResultSet | None:
    """Get newspaper cover image elements from website.

    Returns:
        BeautifulSoup ResultSet of img elements or None if error.
    """
    html_content = await _fetch_html(URL)
    if html_content is None:
        return None

    try:
        soup = BeautifulSoup(html_content, features="html.parser")
        images = soup.find_all("img")  # Changed from picture to img
        return images
    except Exception as e:
        logger.error(f"Error parsing HTML: {e}")
        return None


def _filter_pictures(
    pictures: element.ResultSet, newspapers: tuple[str, ...]
) -> list[str]:
    """Filter image elements to get desired newspaper covers.

    Args:
        pictures: BeautifulSoup ResultSet of img elements.
        newspapers: Tuple of newspaper names to filter for (lowercase slugs).

    Returns:
        List of high-resolution cover image URLs.
    """
    covers = []
    for cover in pictures:
        if cover.get("alt", "").lower() in newspapers:
            url = cover["src"]
            # SAPO thumbs service uses W= and H= for dimensions
            # Replace with high-res parameters (1000x1500)
            url = re.sub(r"W=\d+", "W=1000", url)
            url = re.sub(r"H=\d+", "H=1500", url)
            covers.append(url)
    return covers


async def _download_image(url: str) -> Image.Image | None:
    """Download image from URL.

    Args:
        url: Image URL to download.

    Returns:
        PIL Image object or None if download failed.
    """
    try:
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                content = await response.read()
                return Image.open(BytesIO(content))
    except (aiohttp.ClientError, OSError) as e:
        logger.error(f"Error downloading image from {url}: {e}")
        return None


async def sports_covers() -> list[str]:
    """Get sports newspaper cover URLs.

    Main entry point for fetching newspaper covers.

    Returns:
        List of high-resolution cover image URLs.

    Raises:
        Exception: If cover retrieval fails.
    """
    pictures = await _get_pictures()
    if pictures is None:
        raise Exception("Failed to fetch newspaper covers")

    covers = _filter_pictures(pictures, NEWSPAPERS)
    if not covers:
        raise Exception("No newspaper covers found")

    logger.info(f"Found {len(covers)} newspaper covers")
    return covers
