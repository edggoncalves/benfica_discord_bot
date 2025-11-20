import logging
import os
from datetime import datetime
from os.path import exists, getctime
from pathlib import Path
from shutil import which

import selenium.webdriver.firefox.webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager

logger = logging.getLogger(__name__)

DRIVER_UPDATE_DAYS = 5


def _get_driver_path() -> str:
    """Get or install geckodriver path.

    Returns:
        Path to geckodriver executable.
    """
    # Check if driver path is stored in environment
    stored_path = os.getenv("SELENIUM_DRIVER_PATH")

    if stored_path and exists(stored_path):
        driver_age = getctime(stored_path)
        days_old = (datetime.now() - datetime.fromtimestamp(driver_age)).days

        if days_old <= DRIVER_UPDATE_DAYS:
            logger.debug(f"Using existing driver: {stored_path}")
            return stored_path

        logger.info(
            f"Driver is {days_old} days old, updating "
            f"(threshold: {DRIVER_UPDATE_DAYS} days)"
        )

    # Install or update driver
    logger.info("Installing/updating geckodriver")
    driver_path = GeckoDriverManager().install()

    # Save path to .env for future use
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            lines = f.readlines()

        # Update or append SELENIUM_DRIVER_PATH
        path_found = False
        for i, line in enumerate(lines):
            if line.startswith("SELENIUM_DRIVER_PATH="):
                lines[i] = f"SELENIUM_DRIVER_PATH={driver_path}\n"
                path_found = True
                break

        if not path_found:
            lines.append("\n# Selenium driver path (auto-managed)\n")
            lines.append(f"SELENIUM_DRIVER_PATH={driver_path}\n")

        with open(env_path, "w") as f:
            f.writelines(lines)

    return driver_path


def gen_browser() -> selenium.webdriver.firefox.webdriver.WebDriver:
    """Generate a headless Firefox WebDriver instance.

    Manages geckodriver installation and updates. Driver is automatically
    updated if older than 5 days.

    Returns:
        Configured Firefox WebDriver instance.

    Raises:
        WebDriverException: If browser creation fails.
    """
    driver_path = _get_driver_path()

    # Force headless mode via environment variable
    os.environ["MOZ_HEADLESS"] = "1"

    opts = Options()
    opts.headless = True
    opts.add_argument("--headless")

    firefox_binary = which("firefox")
    if firefox_binary:
        opts.binary_location = firefox_binary

    # Minimal window size to reduce memory usage
    opts.add_argument("--width=1280")
    opts.add_argument("--height=720")

    # Critical: Disable features that cause crashes
    opts.set_preference("browser.cache.disk.enable", False)
    opts.set_preference("browser.cache.memory.enable", False)
    opts.set_preference("media.autoplay.enabled", False)
    opts.set_preference("media.video_stats.enabled", False)

    # Prevent Firefox from using too much memory
    opts.set_preference("browser.sessionhistory.max_entries", 1)
    opts.set_preference("browser.sessionhistory.max_total_viewers", 0)
    opts.set_preference("javascript.options.mem.max", 256 * 1024 * 1024)  # 256MB limit

    # Disable single-use features that can crash
    opts.set_preference("gfx.webrender.all", False)
    opts.set_preference("layers.acceleration.disabled", True)

    # Create service with minimal logging
    service = Service(
        executable_path=driver_path,
        log_output=os.devnull,
    )

    try:
        logger.info("Initializing Firefox browser in headless mode...")
        browser = Firefox(service=service, options=opts)

        # CRITICAL: Set timeouts BEFORE any page operations
        # These must be set immediately after browser creation
        browser.set_page_load_timeout(120)
        browser.set_script_timeout(120)

        logger.info("Firefox browser created successfully")
        return browser
    except WebDriverException as e:
        logger.error(f"Failed to create browser: {e}")
        raise
