"""Discord slash command for team of the week."""

import asyncio
import logging
from datetime import datetime

import discord

from config.constants import ERROR_TOTW_FETCH, RATE_LIMIT_TOTW
from core.team_of_week import fetch_team_week

logger = logging.getLogger(__name__)

# Rate limiting state
last_totw_run = dict()


def _today_key() -> dict:
    """Get today's date as a dict key for rate limiting.

    Returns:
        Dict with month: day mapping for today.
    """
    now = datetime.now()
    return {now.month: now.day}


async def equipa_semana_command(interaction: discord.Interaction) -> None:
    """Handle /equipa_semana slash command.

    Args:
        interaction: Discord interaction from slash command.
    """
    # Check if already run today (rate limiting)
    if last_totw_run == _today_key():
        logger.info(
            f"Team of the week already fetched today by "
            f"{interaction.user}, denying request"
        )
        await interaction.followup.send(RATE_LIMIT_TOTW)
        return

    try:
        # Run blocking Selenium operation in thread executor
        loop = asyncio.get_event_loop()
        discord_file = await loop.run_in_executor(None, fetch_team_week)
        await interaction.followup.send(file=discord_file)

        # Mark as run today
        last_totw_run.update(_today_key())
        logger.info(
            "Team of the week posted successfully, marked as run today"
        )
    except Exception as e:
        logger.error(f"Error fetching team of the week: {e}")
        await interaction.followup.send(ERROR_TOTW_FETCH)
