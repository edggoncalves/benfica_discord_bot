"""Health check utilities for bot monitoring."""

import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Health check file path (can be monitored by external tools)
HEALTH_CHECK_FILE = Path(__file__).parent.parent / "bot_health.txt"


def update_health_check() -> None:
    """Update health check file with current timestamp.

    This function writes the current timestamp to a health check file
    that can be monitored by external tools (cron, systemd, etc.) to
    ensure the bot is running.

    The file contains ISO format timestamp that can be easily parsed
    and compared to detect if the bot has stopped responding.
    """
    try:
        timestamp = datetime.now().isoformat()
        HEALTH_CHECK_FILE.write_text(f"{timestamp}\n")
        logger.debug(f"Health check updated: {timestamp}")
    except OSError as e:
        logger.error(f"Failed to update health check file: {e}")


def read_health_check() -> datetime | None:
    """Read the last health check timestamp.

    Returns:
        Last health check datetime, or None if file doesn't exist or
        can't be parsed.
    """
    try:
        if not HEALTH_CHECK_FILE.exists():
            return None

        content = HEALTH_CHECK_FILE.read_text().strip()
        return datetime.fromisoformat(content)
    except (OSError, ValueError) as e:
        logger.error(f"Failed to read health check file: {e}")
        return None
