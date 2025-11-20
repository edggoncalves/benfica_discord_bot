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

    opts = Options()
    opts.headless = True
    firefox_binary = which("firefox")
    if firefox_binary:
        opts.binary_location = firefox_binary

    # Additional options for stability in headless environments
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")

    # Set preferences to avoid potential issues
    opts.set_preference("browser.cache.disk.enable", False)
    opts.set_preference("browser.cache.memory.enable", False)
    opts.set_preference("browser.cache.offline.enable", False)
    opts.set_preference("network.http.use-cache", False)

    # Create service with explicit driver path
    service = Service(executable_path=driver_path)

    try:
        browser = Firefox(service=service, options=opts)
        logger.debug("Firefox browser created successfully")
        return browser
    except WebDriverException as e:
        logger.error(f"Failed to create browser: {e}")
        raise
