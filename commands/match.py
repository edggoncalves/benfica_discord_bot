"""Discord slash commands for match information."""

import asyncio
import logging

import discord

from config.constants import (
    ERROR_MATCH_COUNTDOWN,
    ERROR_MATCH_DATA_NOT_FOUND,
    ERROR_MATCH_DATA_UPDATE,
    ERROR_MATCH_DATE,
    SUCCESS_MATCH_DATA_UPDATED,
)
from core import match

logger = logging.getLogger(__name__)


async def quanto_falta_command(interaction: discord.Interaction) -> None:
    """Handle /quanto_falta slash command.

    Args:
        interaction: Discord interaction from slash command.
    """
    try:
        # Run in executor since it's a synchronous function
        loop = asyncio.get_event_loop()
        message = await loop.run_in_executor(None, match.how_long_until)
        await interaction.followup.send(message)
    except FileNotFoundError:
        await interaction.followup.send(ERROR_MATCH_DATA_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error in quanto_falta command: {e}")
        await interaction.followup.send(ERROR_MATCH_COUNTDOWN)


async def quando_joga_command(interaction: discord.Interaction) -> None:
    """Handle /quando_joga slash command.

    Args:
        interaction: Discord interaction from slash command.
    """
    try:
        # Run in executor since it's a synchronous function
        loop = asyncio.get_event_loop()
        message = await loop.run_in_executor(None, match.when_is_it)
        await interaction.followup.send(message)
    except FileNotFoundError:
        await interaction.followup.send(ERROR_MATCH_DATA_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error in quando_joga command: {e}")
        await interaction.followup.send(ERROR_MATCH_DATE)


async def actualizar_data_command(interaction: discord.Interaction) -> None:
    """Handle /actualizar_data slash command.

    Args:
        interaction: Discord interaction from slash command.
    """
    try:
        # Fast requests-only operation (no thread executor needed)
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(None, match.update_match_date)
        if success:
            await interaction.followup.send(SUCCESS_MATCH_DATA_UPDATED)
        else:
            await interaction.followup.send(ERROR_MATCH_DATA_UPDATE)
    except Exception as e:
        logger.error(f"Error updating match date: {e}")
        await interaction.followup.send(ERROR_MATCH_DATA_UPDATE)
