"""Discord slash command for team of the week."""

import asyncio
import logging
from datetime import timedelta

import discord

from config.constants import ERROR_TOTW_FETCH
from core.rate_limit import rate_limit
from core.team_of_week import fetch_team_week

logger = logging.getLogger(__name__)


@rate_limit(
    per_user=False,
    interval=timedelta(hours=24),
    message="Equipa da semana já foi pedida hoje. Tenta amanhã!",
)
async def equipa_semana_command(interaction: discord.Interaction) -> None:
    """Handle /equipa_semana slash command.

    Args:
        interaction: Discord interaction from slash command.
    """
    try:
        # Run blocking Selenium operation in thread executor
        loop = asyncio.get_event_loop()
        discord_file = await loop.run_in_executor(None, fetch_team_week)
        await interaction.followup.send(file=discord_file)

        logger.info("Team of the week posted successfully")
    except Exception as e:
        logger.error(f"Error fetching team of the week: {e}")
        await interaction.followup.send(ERROR_TOTW_FETCH)
