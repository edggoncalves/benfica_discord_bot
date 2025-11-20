import asyncio
import logging
from io import BytesIO
from pathlib import Path
from sys import platform

import aiohttp
from bs4 import BeautifulSoup, element
from PIL import Image

logger = logging.getLogger(__name__)

URL = "https://24.sapo.pt/jornais/desporto"
NEWSPAPERS = ("a-bola", "o-jogo", "record")  # Changed to match img alt attributes
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
                logger.error(
                    f"Max retries exceeded for {url} (timeout)"
                )
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
    pictures: element.ResultSet,
    newspapers: tuple[str, ...]
) -> list[str]:
    """Filter image elements to get desired newspaper covers.

    Args:
        pictures: BeautifulSoup ResultSet of img elements.
        newspapers: Tuple of newspaper names to filter for (lowercase slugs).

    Returns:
        List of cover image URLs.
    """
    covers = [
        cover["src"]  # Changed from data-original-src to src
        for cover in pictures
        if cover.get("alt", "").lower() in newspapers  # Check alt attribute
    ]
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


async def create_collage(urls: list[str]) -> str:
    """Create collage from newspaper cover URLs.

    Downloads images and combines them side-by-side with uniform width.

    Args:
        urls: List of image URLs to combine.

    Returns:
        Path to saved collage file.

    Raises:
        Exception: If collage creation fails.
    """
    # Download all images concurrently
    tasks = [_download_image(url) for url in urls]
    downloaded_images = await asyncio.gather(*tasks)

    images = [img for img in downloaded_images if img is not None]
    if not images:
        raise Exception("Failed to download any images")

    if len(images) < len(urls):
        logger.warning(
            f"Only downloaded {len(images)}/{len(urls)} images"
        )

    # Find maximum width
    max_width = max(img.width for img in images)

    # Scale images to same width
    scaled_images = []
    for img in images:
        if img.width == max_width:
            scaled_images.append(img)
        else:
            new_height = (img.height * max_width) // img.width
            scaled_img = img.resize(
                (max_width, new_height),
                Image.Resampling.BICUBIC
            )
            scaled_images.append(scaled_img)

    max_height = max(img.height for img in scaled_images)

    # Create collage
    collage_width = max_width * len(scaled_images)
    collage = Image.new("RGB", (collage_width, max_height), "#FFF")

    for i, img in enumerate(scaled_images):
        collage.paste(img, (max_width * i, 0))

    # Save collage
    if platform == "win32":
        file_path = Path.home() / "AppData" / "Local" / "Temp" / "collage.jpg"
    else:
        file_path = Path("/tmp/collage.jpg")

    try:
        collage.save(file_path, "JPEG")
        logger.info(f"Collage saved to {file_path}")
        return str(file_path)
    except OSError as e:
        logger.error(f"Error saving collage: {e}")
        raise


async def sports_covers() -> str:
    """Get sports newspaper covers and create collage.

    Main entry point for fetching newspaper covers.

    Returns:
        Path to collage image file.

    Raises:
        Exception: If cover retrieval or collage creation fails.
    """
    pictures = await _get_pictures()
    if pictures is None:
        raise Exception("Failed to fetch newspaper covers")

    covers = _filter_pictures(pictures, NEWSPAPERS)
    if not covers:
        raise Exception("No newspaper covers found")

    logger.info(f"Found {len(covers)} newspaper covers")
    return await create_collage(covers)
