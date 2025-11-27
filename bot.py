"""Benfica Discord Bot - Main entry point.

A Discord bot that posts sports newspaper covers and Benfica match information.
"""

import logging

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from discord.ext import commands

from commands.covers import capas_command
from commands.events import criar_evento_command
from commands.match import (
    actualizar_data_command,
    quando_joga_command,
    quanto_falta_command,
)
from commands.totw import equipa_semana_command
from config import settings
from config.constants import TIMEZONE
from tasks.daily import daily_covers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler("bot.log"),  # File output
    ],
)
logger = logging.getLogger(__name__)

# Configure bot with minimal required intents
intents = discord.Intents.default()
description = "Um bot para obter capas de jornais."
bot = commands.Bot(
    command_prefix="!", description=description, intents=intents
)

# Configuration variables (loaded at startup)
channel_id: int
hour: str


def load_configuration() -> tuple[str, int, str]:
    """Load configuration from .env file or run setup wizard.

    Returns:
        Tuple of (token, channel_id, hour).

    Raises:
        ValueError: If configuration is invalid.
    """
    # Check if configuration exists, run setup wizard if not
    if not settings.exists():
        logger.info("No configuration found, running setup wizard")
        settings.setup_interactive()

    # Get configuration parameters
    try:
        token = settings.get_required("DISCORD_TOKEN")
        channel_id = int(settings.get_required("DISCORD_CHANNEL_ID"))
        hour = settings.get("SCHEDULE_HOUR", "8")
        return token, channel_id, hour
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise


async def safe_defer(interaction: discord.Interaction) -> bool:
    """Safely defer an interaction with fallback error handling.

    Args:
        interaction: Discord interaction to defer.

    Returns:
        True if defer succeeded, False if it failed.
    """
    try:
        logger.debug(f"Attempting to defer interaction {interaction.id}")
        await interaction.response.defer()
        logger.debug(f"Successfully deferred interaction {interaction.id}")
        return True
    except discord.NotFound:
        # Interaction expired - this is a hard failure
        logger.warning(
            f"Interaction {interaction.id} expired (10062). "
            "This usually means network latency >3s."
        )
        # Don't send fallback message - interaction is truly dead
        return False
    except discord.HTTPException as e:
        # Other HTTP errors - might be transient
        logger.error(f"HTTP error deferring interaction {interaction.id}: {e}")
        return False


# Command registration
@bot.tree.command(
    name="capas", description="Obter capas dos jornais desportivos"
)
async def capas(interaction: discord.Interaction) -> None:
    """Post newspaper covers on demand."""
    if not await safe_defer(interaction):
        logger.warning("Defer failed, aborting capas command")
        return
    await capas_command(interaction)


@bot.tree.command(name="quanto_falta", description="Tempo até ao próximo jogo")
async def quanto_falta(interaction: discord.Interaction) -> None:
    """Show time remaining until next match."""
    if not await safe_defer(interaction):
        return
    await quanto_falta_command(interaction)


@bot.tree.command(name="quando_joga", description="Quando joga o Benfica")
async def quando_joga(interaction: discord.Interaction) -> None:
    """Show when next match is scheduled."""
    if not await safe_defer(interaction):
        return
    await quando_joga_command(interaction)


@bot.tree.command(
    name="actualizar_data", description="Atualizar dados do próximo jogo"
)
async def actualizar_data(interaction: discord.Interaction) -> None:
    """Update next match date from website."""
    if not await safe_defer(interaction):
        return
    await actualizar_data_command(interaction)


@bot.tree.command(
    name="equipa_semana", description="Equipa da semana da Liga Portugal"
)
async def equipa_semana(interaction: discord.Interaction) -> None:
    """Post team of the week screenshot."""
    if not await safe_defer(interaction):
        return
    await equipa_semana_command(interaction)


@bot.tree.command(
    name="criar_evento",
    description="Criar evento no Discord para o próximo jogo",
)
async def criar_evento(interaction: discord.Interaction) -> None:
    """Create a Discord scheduled event for the next match."""
    if not await safe_defer(interaction):
        return
    await criar_evento_command(interaction)


@bot.event
async def on_ready() -> None:
    """Event handler for bot ready state."""
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    logger.info("------")

    # Sync slash commands with Discord
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

    # Start scheduler with Lisbon timezone
    scheduler = AsyncIOScheduler()

    # Create wrapper to ensure async function is properly scheduled
    async def scheduled_daily_covers():
        await daily_covers(bot, channel_id)

    scheduler.add_job(
        scheduled_daily_covers,
        CronTrigger(hour=hour, timezone=TIMEZONE),
    )
    scheduler.start()
    logger.info(f"Scheduler started, daily covers at {hour}:00 Lisbon time")

    # Send startup message to configured channel
    try:
        channel = bot.get_channel(channel_id)
        if channel:
            startup_msg = (
                "🔴⚪ **Bot Iniciado!** ⚪🔴\n\n"
                f"✅ Online e pronto para usar!\n"
                f"📅 Capas diárias agendadas para as {hour}:00\n\n"
                "**Comandos disponíveis:**\n"
                "`/capas` - Capas dos jornais\n"
                "`/equipa_semana` - Equipa da semana\n"
                "`/actualizar_data` - Atualizar dados do jogo\n"
                "`/quanto_falta` - Tempo até ao próximo jogo\n"
                "`/quando_joga` - Quando joga o Benfica\n"
                "`/criar_evento` - Criar evento no Discord"
            )
            await channel.send(startup_msg)
            logger.info("Startup message sent to channel")
        else:
            logger.warning(
                f"Could not find channel {channel_id} for startup message"
            )
    except Exception as e:
        logger.error(f"Error sending startup message: {e}")


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: discord.app_commands.AppCommandError,
) -> None:
    """Global error handler for slash commands."""
    if isinstance(error, discord.app_commands.CommandNotFound):
        return  # Ignore unknown commands

    logger.error(f"App command error: {error}", exc_info=True)

    # Try to send error message to user
    try:
        error_msg = "Ocorreu um erro ao executar o comando."
        if isinstance(error, discord.app_commands.MissingPermissions):
            error_msg = "Erro: Não tens permissões para usar este comando."

        if not interaction.response.is_done():
            await interaction.response.send_message(error_msg, ephemeral=True)
        else:
            await interaction.followup.send(error_msg, ephemeral=True)
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")


if __name__ == "__main__":
    token, channel_id, hour = load_configuration()
    bot.run(token)
