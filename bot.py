import asyncio
import logging
from datetime import datetime
from pathlib import Path

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from discord.ext import commands

import configuration
import covers
import next_match
import totw

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

last_run = dict()
last_totw_run = dict()  # Track last team of the week command execution

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
    if not configuration.exists():
        logger.info("No configuration found, running setup wizard")
        configuration.setup_interactive()

    # Get configuration parameters
    try:
        token = configuration.get_required("DISCORD_TOKEN")
        channel_id = int(configuration.get_required("DISCORD_CHANNEL_ID"))
        hour = configuration.get("SCHEDULE_HOUR", "8")
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


async def send_collage(
    interaction: discord.Interaction, file_path: str
) -> None:
    """Send newspaper collage file to Discord.

    Args:
        interaction: Discord interaction from slash command.
        file_path: Path to collage image file.
    """
    try:
        path = Path(file_path)
        if not path.exists():
            await interaction.followup.send(
                "Erro: Ficheiro de capas não encontrado."
            )
            return

        with open(path, "rb") as fp:
            discord_file = discord.File(fp, filename="collage.jpg")
        await interaction.followup.send(file=discord_file)
    except OSError as e:
        logger.error(f"File operation error: {e}")
        await interaction.followup.send("Erro ao ler o ficheiro de capas.")
    except discord.DiscordException as e:
        logger.error(f"Discord error sending file: {e}")
        await interaction.followup.send("Erro ao enviar capas.")


@bot.tree.command(
    name="capas", description="Obter capas dos jornais desportivos"
)
async def capas(interaction: discord.Interaction) -> None:
    """Post newspaper covers on demand."""
    logger.info(f"Capas command triggered by {interaction.user}")

    if not await safe_defer(interaction):
        logger.warning("Defer failed, aborting capas command")
        return

    logger.info("Defer succeeded, fetching covers")
    try:
        file_path = await covers.sports_covers()
        last_run[datetime.now().month] = datetime.now().day
        logger.info(f"Covers fetched, sending collage from {file_path}")
        await send_collage(interaction, file_path)
        logger.info("Capas command completed successfully")
    except Exception as e:
        logger.error(f"Error in capas command: {e}")
        await interaction.followup.send("Erro ao obter capas dos jornais.")


@bot.tree.command(
    name="quanto_falta", description="Tempo até ao próximo jogo"
)
async def quanto_falta(interaction: discord.Interaction) -> None:
    """Show time remaining until next match."""
    if not await safe_defer(interaction):
        return

    try:
        # Run in executor since it's a synchronous function
        loop = asyncio.get_event_loop()
        message = await loop.run_in_executor(
            None, next_match.how_long_until
        )
        await interaction.followup.send(message)
    except FileNotFoundError:
        await interaction.followup.send(
            "Dados do jogo não encontrados. "
            "Usa `/actualizar_data` primeiro."
        )
    except Exception as e:
        logger.error(f"Error in quanto_falta command: {e}")
        await interaction.followup.send("Erro ao calcular tempo até ao jogo.")


@bot.tree.command(
    name="quando_joga", description="Quando joga o Benfica"
)
async def quando_joga(interaction: discord.Interaction) -> None:
    """Show when next match is scheduled."""
    if not await safe_defer(interaction):
        return

    try:
        # Run in executor since it's a synchronous function
        loop = asyncio.get_event_loop()
        message = await loop.run_in_executor(None, next_match.when_is_it)
        await interaction.followup.send(message)
    except FileNotFoundError:
        await interaction.followup.send(
            "Dados do jogo não encontrados. "
            "Usa `/actualizar_data` primeiro."
        )
    except Exception as e:
        logger.error(f"Error in quando_joga command: {e}")
        await interaction.followup.send("Erro ao obter data do jogo.")


@bot.tree.command(
    name="actualizar_data", description="Atualizar dados do próximo jogo"
)
async def actualizar_data(interaction: discord.Interaction) -> None:
    """Update next match date from website."""
    if not await safe_defer(interaction):
        return

    try:
        # Fast requests-only operation (no thread executor needed)
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None, next_match.update_match_date
        )
        if success:
            await interaction.followup.send(
                "✅ Data do jogo actualizada. "
                "Testa com `/quando_joga` ou `/quanto_falta`"
            )
        else:
            await interaction.followup.send(
                "❌ Erro ao actualizar data do jogo."
            )
    except Exception as e:
        logger.error(f"Error updating match date: {e}")
        await interaction.followup.send("❌ Erro ao actualizar data do jogo.")


@bot.tree.command(
    name="evento", description="Gerar texto formatado do evento do jogo"
)
async def evento(interaction: discord.Interaction) -> None:
    """Generate formatted event text for next match."""
    if not await safe_defer(interaction):
        return

    try:
        # Run in executor since it's a synchronous function
        loop = asyncio.get_event_loop()
        event_text = await loop.run_in_executor(
            None, next_match.generate_event
        )
        await interaction.followup.send(event_text)
    except Exception as e:
        logger.error(f"Error generating event: {e}")
        await interaction.followup.send("Erro ao gerar evento.")


@bot.tree.command(
    name="equipa_semana", description="Equipa da semana da Liga Portugal"
)
async def equipa_semana(interaction: discord.Interaction) -> None:
    """Post team of the week screenshot."""
    if not await safe_defer(interaction):
        return

    # Check if already run today (rate limiting)
    today = {datetime.now().month: datetime.now().day}
    if last_totw_run == today:
        logger.info(
            f"Team of the week already fetched today by "
            f"{interaction.user}, denying request"
        )
        await interaction.followup.send(
            "⏰ Este comando já foi executado hoje. "
            "Por favor tenta novamente amanhã.\n"
            "(Este comando é pesado e só pode ser usado uma vez por dia)"
        )
        return

    try:
        # Run blocking Selenium operation in thread executor
        loop = asyncio.get_event_loop()
        discord_file = await loop.run_in_executor(None, totw.fetch_team_week)
        await interaction.followup.send(file=discord_file)

        # Mark as run today
        last_totw_run.update(today)
        logger.info("Team of the week posted successfully, marked as run today")
    except Exception as e:
        logger.error(f"Error fetching team of the week: {e}")
        await interaction.followup.send("Erro ao obter equipa da semana.")


@bot.tree.command(
    name="criar_evento",
    description="Criar evento no Discord para o próximo jogo",
)
async def criar_evento(interaction: discord.Interaction) -> None:
    """Create a Discord scheduled event for the next match."""
    if not await safe_defer(interaction):
        return

    try:
        # Check if we have a guild (server) context
        if interaction.guild is None:
            await interaction.followup.send(
                "Este comando só funciona em servidores."
            )
            return

        # Read match data
        try:
            match_data = next_match.read_match_data()
        except FileNotFoundError:
            await interaction.followup.send(
                "Dados do jogo não encontrados. "
                "Usa `/actualizar_data` primeiro."
            )
            return

        # Parse match datetime with Lisbon timezone
        # Match data is already in Lisbon time, so we create a
        # timezone-aware datetime directly
        import pendulum

        match_dt_aware = pendulum.datetime(
            year=match_data["year"],
            month=match_data["month"],
            day=match_data["day"],
            hour=match_data["hour"],
            minute=match_data["minute"],
            tz="Europe/Lisbon",
        )

        # Build event details
        event_name = f"⚽ Benfica vs {match_data['adversary']}"
        event_description = (
            f"🏟️ **Local:** {match_data['location']}\n"
            f"🏆 **Competição:** {match_data['competition']}\n\n"
            "Força Benfica! 🦅"
        )

        # Check if event already exists
        existing_events = interaction.guild.scheduled_events
        for existing_event in existing_events:
            if existing_event.name == event_name:
                # Discord timestamp: <t:unix:F> = full date and time
                timestamp = int(existing_event.start_time.timestamp())
                await interaction.followup.send(
                    f"❌ Já existe um evento com este nome!\n"
                    f"📅 {event_name}\n"
                    f"🕐 <t:{timestamp}:F>"
                )
                logger.info(
                    f"Event creation skipped - already exists: {event_name}"
                )
                return

        # Create the scheduled event
        # Event end time is 2 hours after start (typical match duration)
        end_time = match_dt_aware.add(hours=2)

        event = await interaction.guild.create_scheduled_event(
            name=event_name,
            description=event_description,
            start_time=match_dt_aware,
            end_time=end_time,
            entity_type=discord.EntityType.external,
            location=match_data["location"],
            privacy_level=discord.PrivacyLevel.guild_only,
        )

        # Discord timestamp: <t:unix:F> = full date and time
        timestamp = int(match_dt_aware.timestamp())
        await interaction.followup.send(
            f"✅ Evento criado com sucesso!\n"
            f"📅 {event_name}\n"
            f"🕐 <t:{timestamp}:F>"
        )
        logger.info(f"Created event: {event.name} (ID: {event.id})")

    except Exception as e:
        logger.error(f"Error creating event: {e}", exc_info=True)
        await interaction.followup.send(f"Erro ao criar evento: {str(e)}")


async def daily_covers() -> None:
    """Scheduled task to post newspaper covers daily."""
    try:
        # Check if already run today
        today = {datetime.now().month: datetime.now().day}
        if last_run == today:
            logger.info("Daily covers already posted today, skipping")
            return

        channel = bot.get_channel(channel_id)
        if channel is None:
            logger.error(f"Channel {channel_id} not found")
            return

        file_path = await covers.sports_covers()
        path = Path(file_path)
        if not path.exists():
            logger.error(f"Collage file not found: {file_path}")
            return

        with open(path, "rb") as fp:
            discord_file = discord.File(fp, "collage.jpg")
        await channel.send(file=discord_file)
        last_run.update(today)
        logger.info("Daily covers posted successfully")

    except Exception as e:
        logger.error(f"Error in daily_covers task: {e}")


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

    # Start scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(daily_covers, CronTrigger(hour=hour))
    scheduler.start()
    logger.info(f"Scheduler started, daily covers at {hour}:00")

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
                "`/evento` - Texto formatado do evento\n"
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
            await interaction.response.send_message(
                error_msg, ephemeral=True
            )
        else:
            await interaction.followup.send(error_msg, ephemeral=True)
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")


if __name__ == "__main__":
    token, channel_id, hour = load_configuration()
    bot.run(token)
