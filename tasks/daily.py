"""Scheduled tasks for daily bot operations."""

import json
import logging
from datetime import datetime
from pathlib import Path

from core.covers import get_covers_as_discord_files

logger = logging.getLogger(__name__)

# File to track last run date
LAST_RUN_FILE = Path("last_run.json")


def _get_today_date() -> str:
    """Get today's date as a string for comparison.

    Returns:
        Date string in YYYY-MM-DD format.
    """
    return datetime.now().strftime("%Y-%m-%d")


def _get_last_run_date(channel_id: int) -> str | None:
    """Get the last run date for a specific channel from file.

    Args:
        channel_id: Discord channel ID to check.

    Returns:
        Date string or None if file doesn't exist or channel not found.
    """
    try:
        if LAST_RUN_FILE.exists():
            data = json.loads(LAST_RUN_FILE.read_text())
            return data.get(str(channel_id))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Error reading last run file: {e}")
    return None


def _save_last_run_date(channel_id: int, date: str) -> None:
    """Save the last run date for a specific channel to file.

    Args:
        channel_id: Discord channel ID.
        date: Date string in YYYY-MM-DD format.
    """
    try:
        # Load existing data
        data = {}
        if LAST_RUN_FILE.exists():
            data = json.loads(LAST_RUN_FILE.read_text())

        # Update channel's date
        data[str(channel_id)] = date

        # Save back to file
        LAST_RUN_FILE.write_text(json.dumps(data, indent=2))
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Error saving last run file: {e}")


async def daily_covers(bot, channel_id: int) -> None:
    """Scheduled task to post newspaper covers daily.

    Args:
        bot: Discord bot instance.
        channel_id: ID of channel to post to.
    """
    try:
        logger.info(f"Daily covers task started for channel {channel_id}")
        today = _get_today_date()
        last_run = _get_last_run_date(channel_id)
        logger.info(
            f"Channel {channel_id}: last_run={last_run}, today={today}"
        )

        # Check if already run today for this channel
        if last_run == today:
            logger.info(
                f"Daily covers already posted today for channel {channel_id}, "
                "skipping"
            )
            return

        logger.info(f"Looking for channel {channel_id}")
        channel = bot.get_channel(channel_id)
        if channel is None:
            logger.error(f"Channel {channel_id} not found")
            return
        logger.info(f"Found channel: {channel.name}")

        # Get covers as Discord files
        logger.info("Fetching covers...")
        discord_files = await get_covers_as_discord_files()
        logger.info(f"Got {len(discord_files)} covers")

        # Send all covers in one message
        logger.info("Sending covers to Discord...")
        await channel.send(files=discord_files)

        _save_last_run_date(channel_id, today)
        logger.info(
            f"Daily covers posted successfully to channel {channel_id}"
        )

    except Exception as e:
        logger.error(
            f"Error in daily_covers task for channel {channel_id}: {e}",
            exc_info=True,
        )
