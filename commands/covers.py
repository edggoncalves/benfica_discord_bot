"""Discord slash command for newspaper covers."""

import logging
from datetime import datetime

import discord

from config.constants import ERROR_COVERS_FETCH
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


async def capas_command(interaction: discord.Interaction) -> None:
    """Handle /capas slash command.

    Args:
        interaction: Discord interaction from slash command.
    """
    logger.info(f"Capas command triggered by {interaction.user}")

    try:
        discord_files = await get_covers_as_discord_files()
        await interaction.followup.send(files=discord_files)
        last_run.update(_today_key())
        logger.info("Capas command completed successfully")
    except Exception as e:
        logger.error(f"Error in capas command: {e}")
        await interaction.followup.send(ERROR_COVERS_FETCH)
