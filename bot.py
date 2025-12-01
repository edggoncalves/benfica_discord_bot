"""Benfica Discord Bot - Main entry point.

A Discord bot that posts sports newspaper covers and Benfica match information.
"""

import asyncio
import logging
import logging.handlers
import signal

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from discord.ext import commands

from commands.calendar import calendario_command
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
from config.paths import LOG_FILE
from config.validation import validate_config
from core.health_check import update_health_check

# Configure logging
from core.logging_config import StructuredFormatter
from tasks.daily import daily_covers

# Console handler - human-readable format
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
console_handler.setFormatter(console_formatter)

# File handler - JSON format for easier parsing
file_handler = logging.handlers.RotatingFileHandler(
    str(LOG_FILE),
    maxBytes=10_000_000,  # 10MB
    backupCount=5,
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(StructuredFormatter())

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler, file_handler],
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
        channel_id_str = settings.get_required("DISCORD_CHANNEL_ID")
        hour = settings.get("SCHEDULE_HOUR", "8")

        # Validate configuration
        config = {
            "DISCORD_TOKEN": token,
            "DISCORD_CHANNEL_ID": channel_id_str,
            "SCHEDULE_HOUR": hour,
        }
        validation_errors = validate_config(config)

        if validation_errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(
                f"  - {err}" for err in validation_errors
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        channel_id = int(channel_id_str)
        logger.info("Configuration loaded and validated successfully")
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


@bot.tree.command(
    name="calendario", description="Mostra os próximos jogos do Benfica"
)
@discord.app_commands.describe(
    quantidade="Número de jogos a mostrar (1-10, padrão: 5)"
)
async def calendario(
    interaction: discord.Interaction, quantidade: int = 5
) -> None:
    """Show upcoming Benfica matches."""
    if not await safe_defer(interaction):
        return
    await calendario_command(interaction, quantidade)


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

    # Daily covers job
    scheduler.add_job(
        scheduled_daily_covers,
        CronTrigger(hour=hour, timezone=TIMEZONE),
    )

    # Health check job - updates every minute for monitoring
    scheduler.add_job(
        update_health_check,
        CronTrigger(minute="*", timezone=TIMEZONE),
    )

    scheduler.start()
    logger.info(f"Scheduler started, daily covers at {hour}:00 Lisbon time")
    logger.info("Health check updates every minute")

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


async def shutdown(sig):
    """Cleanup tasks on shutdown.

    Args:
        sig: Signal received (SIGTERM or SIGINT).
    """
    logger.info(f"Received exit signal {sig.name}...")

    # Cancel all running tasks
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    logger.info(f"Cancelling {len(tasks)} outstanding tasks")
    for task in tasks:
        task.cancel()

    # Wait for all tasks to complete cancellation
    await asyncio.gather(*tasks, return_exceptions=True)

    # Close bot connection
    await bot.close()
    logger.info("Bot shutdown complete")


if __name__ == "__main__":
    token, channel_id, hour = load_configuration()

    # Set up signal handlers for graceful shutdown
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig, lambda s=sig: asyncio.create_task(shutdown(s))
        )

    try:
        bot.run(token)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        logger.info("Bot stopped")
