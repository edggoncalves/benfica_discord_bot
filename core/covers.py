import asyncio
import logging
import re
from io import BytesIO

import aiohttp
import discord
from bs4 import BeautifulSoup, element
from PIL import Image

from config.constants import NEWSPAPER_NAMES

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
    except (AttributeError, ValueError) as e:
        logger.error(f"Error parsing HTML: {e}", exc_info=True)
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
            # Replace with high-res parameters and remove cropping
            url = re.sub(r"W=\d+", "W=1000", url)
            url = re.sub(r"H=\d+", "H=1500", url)
            # Remove crop parameter to get full uncropped image
            url = re.sub(r"&crop=center", "", url)
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


async def _download_covers_data(cover_urls: list[str]) -> list[bytes]:
    """Download newspaper cover images from URLs.

    Args:
        cover_urls: List of cover image URLs.

    Returns:
        List of image data as bytes.
    """
    images_data = []
    async with aiohttp.ClientSession() as session:
        for url in cover_urls:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.read()
                        images_data.append(data)
            except (
                aiohttp.ClientError,
                asyncio.TimeoutError,
                OSError,
            ) as e:
                logger.error(
                    f"Error downloading {url}: {e}", exc_info=True
                )
    return images_data


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


async def download_covers(cover_urls: list[str]) -> list[bytes]:
    """Download newspaper cover images and return as bytes.

    Args:
        cover_urls: List of cover image URLs.

    Returns:
        List of image data as bytes.

    Raises:
        Exception: If no covers could be downloaded.
    """
    images_data = await _download_covers_data(cover_urls)
    if not images_data:
        raise Exception("Failed to download any covers")
    return images_data


async def get_covers_as_discord_files() -> list[discord.File]:
    """Get newspaper covers as Discord File objects ready to send.

    This is the main entry point for getting covers to post to Discord.
    It handles fetching URLs, downloading images, and creating Discord Files.

    Returns:
        List of Discord File objects.

    Raises:
        Exception: If cover retrieval or download fails.
    """
    # Get cover URLs
    cover_urls = await sports_covers()

    # Download the images
    images_data = await download_covers(cover_urls)

    # Create Discord File objects
    discord_files = []
    for i, image_data in enumerate(images_data):
        newspaper = (
            NEWSPAPER_NAMES[i] if i < len(NEWSPAPER_NAMES) else f"jornal_{i+1}"
        )
        discord_file = discord.File(
            BytesIO(image_data), filename=f"{newspaper}.jpg"
        )
        discord_files.append(discord_file)

    return discord_files
