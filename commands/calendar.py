"""Discord slash command for showing upcoming matches."""

import asyncio
import logging

import discord

from commands.decorators import sync_command
from core.benfica_calendar import get_upcoming_matches
from core.match.formatter import format_upcoming_matches_message

logger = logging.getLogger(__name__)


@sync_command(
    error_message="❌ Erro ao obter calendário.",
    file_not_found_message=None,
)
async def calendario_command(
    interaction: discord.Interaction, quantidade: int = 5
) -> None:
    """Handle /calendario slash command.

    Args:
        interaction: Discord interaction from slash command.
        quantidade: Number of matches to show (1-10, default 5).
    """
    # Validate quantidade (clamp between 1 and 10)
    quantidade = min(max(quantidade, 1), 10)

    logger.info(
        f"Fetching {quantidade} upcoming matches for user {interaction.user}"
    )

    # Fetch matches in thread executor to avoid blocking event loop
    loop = asyncio.get_event_loop()
    matches = await loop.run_in_executor(
        None, get_upcoming_matches, quantidade
    )

    # Handle no matches found (return None or empty list)
    if not matches:
        logger.info("No upcoming matches found")
        await interaction.followup.send(
            "❌ Não há jogos futuros disponíveis no calendário."
        )
        return

    # Format and send (handles case with fewer than requested)
    logger.info(f"Sending {len(matches)} upcoming matches to user")
    message = format_upcoming_matches_message(matches)
    await interaction.followup.send(message)
