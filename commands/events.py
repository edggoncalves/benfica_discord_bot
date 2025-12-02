"""Discord slash command for creating scheduled events."""

import asyncio
import logging

import discord

from config.constants import (
    ERROR_EVENT_CREATE,
    ERROR_GUILD_ONLY,
    ERROR_INVALID_QUANTITY,
    ERROR_NO_MATCHES_FOUND,
)
from core.benfica_calendar import get_upcoming_matches
from core.utils.date_parser import parse_dd_mm_yyyy_time

logger = logging.getLogger(__name__)


def _build_event_name(adversary: str) -> str:
    """Build event name for a match.

    Args:
        adversary: Name of opposing team.

    Returns:
        Formatted event name.
    """
    return f"⚽ Benfica vs {adversary}"


def _build_event_description(match: dict) -> str:
    """Build event description from match data.

    Args:
        match: Match data dictionary.

    Returns:
        Formatted event description.
    """
    tv_channel_line = ""
    if match.get("tv_channel"):
        tv_channel_line = f"📺 **Canal TV:** {match['tv_channel']}\n"

    return (
        f"🏟️ **Local:** {match['location']}\n"
        f"🏆 **Competição:** {match['competition']}\n"
        f"{tv_channel_line}"
    )


def _find_existing_event(
    guild: discord.Guild, event_name: str
) -> discord.ScheduledEvent | None:
    """Find existing event by name.

    Args:
        guild: Discord guild to search.
        event_name: Name of event to find.

    Returns:
        Existing event or None if not found.
    """
    for event in guild.scheduled_events:
        if event.name == event_name:
            return event
    return None


def _needs_event_update(
    existing_event: discord.ScheduledEvent,
    event_description: str,
    match_dt_aware,
    location: str,
) -> bool:
    """Check if existing event needs update.

    Args:
        existing_event: Existing Discord event.
        event_description: New description.
        match_dt_aware: New match datetime.
        location: New location.

    Returns:
        True if update needed, False otherwise.
    """
    existing_timestamp = existing_event.start_time.timestamp()
    match_timestamp = match_dt_aware.timestamp()
    time_diff = abs(existing_timestamp - match_timestamp)

    return (
        existing_event.description != event_description
        or existing_event.location != location
        or time_diff > 60  # More than 1 minute difference
    )


async def _update_existing_event(
    existing_event: discord.ScheduledEvent,
    event_description: str,
    match_dt_aware,
    location: str,
    event_name: str,
) -> None:
    """Update existing event with new details.

    Args:
        existing_event: Event to update.
        event_description: New description.
        match_dt_aware: New match datetime.
        location: New location.
        event_name: Event name for logging.
    """
    end_time = match_dt_aware.add(hours=2)
    await existing_event.edit(
        description=event_description,
        start_time=match_dt_aware,
        end_time=end_time,
        location=location,
    )
    logger.info(f"Updated event: {event_name} (ID: {existing_event.id})")


async def _create_new_event(
    guild: discord.Guild,
    event_name: str,
    event_description: str,
    match_dt_aware,
    location: str,
) -> None:
    """Create new Discord scheduled event.

    Args:
        guild: Discord guild.
        event_name: Name for new event.
        event_description: Event description.
        match_dt_aware: Match datetime.
        location: Event location.
    """
    end_time = match_dt_aware.add(hours=2)
    event = await guild.create_scheduled_event(
        name=event_name,
        description=event_description,
        start_time=match_dt_aware,
        end_time=end_time,
        entity_type=discord.EntityType.external,
        location=location,
        privacy_level=discord.PrivacyLevel.guild_only,
    )
    logger.info(f"Created event: {event.name} (ID: {event.id})")


def _build_summary_message(
    created_count: int, updated_count: int, errors: list, unchanged_count: int
) -> str:
    """Build summary message for event creation results.

    Args:
        created_count: Number of events created.
        updated_count: Number of events updated.
        errors: List of error messages.
        unchanged_count: Number of unchanged events.

    Returns:
        Formatted summary message.
    """
    summary_lines = []
    if created_count > 0:
        summary_lines.append(f"✅ Criados: {created_count}")
    if updated_count > 0:
        summary_lines.append(f"🔄 Atualizados: {updated_count}")
    if errors:
        summary_lines.append(f"❌ Erros: {len(errors)}")

    # Only show "no changes" if nothing was created, updated, or errored
    if (
        created_count == 0
        and updated_count == 0
        and len(errors) == 0
        and unchanged_count > 0
    ):
        summary_lines.append("✓ Sem alterações")

    return "📅 **Resumo:**\n" + "\n".join(summary_lines)


async def criar_evento_command(
    interaction: discord.Interaction, quantidade: int = 1
) -> None:
    """Create Discord events for upcoming matches.

    Args:
        interaction: Discord interaction from slash command.
        quantidade: Number of events to create (default 1, max 10).
    """
    try:
        # Check if we have a guild (server) context
        if interaction.guild is None:
            await interaction.followup.send(ERROR_GUILD_ONLY)
            return

        # Validate and cap quantidade - minimum 1, maximum 10 (silently cap)
        if quantidade < 1:
            await interaction.followup.send(ERROR_INVALID_QUANTITY)
            return

        quantidade = min(quantidade, 10)

        # Fetch upcoming matches from calendar API
        loop = asyncio.get_event_loop()
        matches = await loop.run_in_executor(
            None, get_upcoming_matches, quantidade
        )

        if not matches:
            await interaction.followup.send(ERROR_NO_MATCHES_FOUND)
            return

        # Track results
        created_count = 0
        updated_count = 0
        unchanged_count = 0
        errors = []

        for match in matches:
            try:
                event_name = _build_event_name(match["adversary"])
                event_description = _build_event_description(match)

                # Parse match datetime with Lisbon timezone
                match_dt_aware = parse_dd_mm_yyyy_time(
                    match["date"], match["time"], timezone="Europe/Lisbon"
                )

                existing_event = _find_existing_event(
                    interaction.guild, event_name
                )

                if existing_event:
                    if _needs_event_update(
                        existing_event,
                        event_description,
                        match_dt_aware,
                        match["location"],
                    ):
                        await _update_existing_event(
                            existing_event,
                            event_description,
                            match_dt_aware,
                            match["location"],
                            event_name,
                        )
                        updated_count += 1
                    else:
                        unchanged_count += 1
                        logger.debug(f"Event unchanged: {event_name}")
                else:
                    await _create_new_event(
                        interaction.guild,
                        event_name,
                        event_description,
                        match_dt_aware,
                        match["location"],
                    )
                    created_count += 1

            except Exception as e:
                adversary = match.get("adversary", "Unknown")
                logger.error(
                    f"Error processing event for {adversary}: {e}",
                    exc_info=True,
                )
                errors.append(f"{adversary}: {str(e)}")

        summary = _build_summary_message(
            created_count, updated_count, errors, unchanged_count
        )
        await interaction.followup.send(summary)

    except Exception as e:
        logger.error(f"Error in criar_evento_command: {e}", exc_info=True)
        await interaction.followup.send(f"{ERROR_EVENT_CREATE}: {str(e)}")
