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
)
logger = logging.getLogger(__name__)

# Configure bot with minimal required intents
# Note: message_content is a privileged intent that must be enabled
# in Discord Developer Portal under Bot -> Privileged Gateway Intents
intents = discord.Intents.default()
intents.message_content = True  # Required to read command messages
description = "Um bot para obter capas de jornais."
bot = commands.Bot(
    command_prefix="!", description=description, intents=intents
)

last_run = dict()

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


async def send_collage(ctx: commands.Context, file_path: str) -> None:
    """Send newspaper collage file to Discord.

    Args:
        ctx: Discord command context.
        file_path: Path to collage image file.
    """
    try:
        path = Path(file_path)
        if not path.exists():
            await ctx.send("Erro: Ficheiro de capas não encontrado.")
            return

        with open(path, "rb") as fp:
            discord_file = discord.File(fp, filename="collage.jpg")
        await ctx.send(file=discord_file)
    except OSError as e:
        logger.error(f"File operation error: {e}")
        await ctx.send("Erro ao ler o ficheiro de capas.")
    except discord.DiscordException as e:
        logger.error(f"Discord error sending file: {e}")
        await ctx.send("Erro ao enviar capas.")


@bot.command()
async def capas(ctx: commands.Context) -> None:
    """Post newspaper covers on demand."""
    try:
        file_path = await covers.sports_covers()
        last_run[datetime.now().month] = datetime.now().day
        await send_collage(ctx, file_path)
    except Exception as e:
        logger.error(f"Error in capas command: {e}")
        await ctx.send("Erro ao obter capas dos jornais.")


@bot.command()
async def quanto_falta(ctx: commands.Context) -> None:
    """Show time remaining until next match."""
    try:
        message = next_match.how_long_until()
        await ctx.send(message)
    except FileNotFoundError:
        await ctx.send(
            "Dados do jogo não encontrados. "
            "Usa `!actualizar_data` primeiro."
        )
    except Exception as e:
        logger.error(f"Error in quanto_falta command: {e}")
        await ctx.send("Erro ao calcular tempo até ao jogo.")


@bot.command()
async def quando_joga(ctx: commands.Context) -> None:
    """Show when next match is scheduled."""
    try:
        message = next_match.when_is_it()
        await ctx.send(message)
    except FileNotFoundError:
        await ctx.send(
            "Dados do jogo não encontrados. "
            "Usa `!actualizar_data` primeiro."
        )
    except Exception as e:
        logger.error(f"Error in quando_joga command: {e}")
        await ctx.send("Erro ao obter data do jogo.")


@bot.command()
async def actualizar_data(ctx: commands.Context) -> None:
    """Update next match date from website."""
    try:
        # Run blocking Selenium operation in thread executor
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None, next_match.update_match_date
        )
        if success:
            await ctx.send(
                "Data do jogo actualizada. "
                "Testa com `!quando_joga` ou `!quanto_falta`"
            )
        else:
            await ctx.send("Erro ao actualizar data do jogo.")
    except Exception as e:
        logger.error(f"Error updating match date: {e}")
        await ctx.send("Erro ao actualizar data do jogo.")


@bot.command()
async def evento(ctx: commands.Context) -> None:
    """Generate formatted event text for next match."""
    try:
        event_text = next_match.generate_event()
        await ctx.send(event_text)
    except Exception as e:
        logger.error(f"Error generating event: {e}")
        await ctx.send("Erro ao gerar evento.")


@bot.command()
async def equipa_semana(ctx: commands.Context) -> None:
    """Post team of the week screenshot."""
    try:
        # Run blocking Selenium operation in thread executor
        loop = asyncio.get_event_loop()
        discord_file = await loop.run_in_executor(None, totw.fetch_team_week)
        await ctx.send(file=discord_file)
    except Exception as e:
        logger.error(f"Error fetching team of the week: {e}")
        await ctx.send("Erro ao obter equipa da semana.")


@bot.command()
async def criar_evento(ctx: commands.Context) -> None:
    """Create a Discord scheduled event for the next match."""
    try:
        # Check if we have a guild (server) context
        if ctx.guild is None:
            await ctx.send("Este comando só funciona em servidores.")
            return

        # Read match data
        try:
            match_data = next_match.read_match_data()
        except FileNotFoundError:
            await ctx.send(
                "Dados do jogo não encontrados. "
                "Usa `!actualizar_data` primeiro."
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

        # Create the scheduled event
        # Event end time is 2 hours after start (typical match duration)
        end_time = match_dt_aware.add(hours=2)

        event = await ctx.guild.create_scheduled_event(
            name=event_name,
            description=event_description,
            start_time=match_dt_aware,
            end_time=end_time,
            entity_type=discord.EntityType.external,
            location=match_data["location"],
            privacy_level=discord.PrivacyLevel.guild_only,
        )

        await ctx.send(
            f"✅ Evento criado com sucesso!\n"
            f"📅 {event_name}\n"
            f"🕐 {match_dt_aware.strftime('%d/%m/%Y às %H:%M')}"
        )
        logger.info(f"Created event: {event.name} (ID: {event.id})")

    except Exception as e:
        logger.error(f"Error creating event: {e}", exc_info=True)
        await ctx.send(f"Erro ao criar evento: {str(e)}")


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
                "`!capas` - Capas dos jornais\n"
                "`!equipa_semana` - Equipa da semana\n"
                "`!actualizar_data` - Atualizar dados do jogo\n"
                "`!quanto_falta` - Tempo até ao próximo jogo\n"
                "`!quando_joga` - Quando joga o Benfica\n"
                "`!evento` - Texto formatado do evento"
            )
            await channel.send(startup_msg)
            logger.info("Startup message sent to channel")
        else:
            logger.warning(
                f"Could not find channel {channel_id} for startup message"
            )
    except Exception as e:
        logger.error(f"Error sending startup message: {e}")


@bot.event
async def on_command_error(
    ctx: commands.Context, error: commands.CommandError
) -> None:
    """Global error handler for bot commands."""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Erro: Argumentos em falta.")
    else:
        logger.error(f"Command error: {error}")
        await ctx.send("Ocorreu um erro ao executar o comando.")


if __name__ == "__main__":
    token, channel_id, hour = load_configuration()
    bot.run(token)
