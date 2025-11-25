"""Scheduled tasks for daily bot operations."""

import logging
from datetime import datetime

from core.covers import get_covers_as_discord_files

logger = logging.getLogger(__name__)

# Rate limiting state
last_run = dict()


def _today_key() -> dict:
    """Get today's date as a dict key for rate limiting.

    Returns:
        Dict with month: day mapping for today.
    """
    now = datetime.now()
    return {now.month: now.day}


async def daily_covers(bot, channel_id: int) -> None:
    """Scheduled task to post newspaper covers daily.

    Args:
        bot: Discord bot instance.
        channel_id: ID of channel to post to.
    """
    try:
        # Check if already run today
        if last_run == _today_key():
            logger.info("Daily covers already posted today, skipping")
            return

        channel = bot.get_channel(channel_id)
        if channel is None:
            logger.error(f"Channel {channel_id} not found")
            return

        # Get covers as Discord files
        discord_files = await get_covers_as_discord_files()

        # Send all covers in one message
        await channel.send(files=discord_files)

        last_run.update(_today_key())
        logger.info("Daily covers posted successfully")

    except Exception as e:
        logger.error(f"Error in daily_covers task: {e}")
