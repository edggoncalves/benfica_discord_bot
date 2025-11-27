"""Discord slash command for creating scheduled events."""

import asyncio
import logging

import discord

from config.constants import (
    ERROR_EVENT_CREATE,
    ERROR_GUILD_ONLY,
    ERROR_MATCH_DATA_NOT_FOUND,
    ERROR_NO_UPCOMING_MATCH,
    EVENT_ALREADY_EXISTS,
    EVENT_CREATED,
    SUCCESS_MATCH_DATA_REFRESHED,
)
from core import match

logger = logging.getLogger(__name__)


async def criar_evento_command(interaction: discord.Interaction) -> None:
    """Handle /criar_evento slash command.

    Args:
        interaction: Discord interaction from slash command.
    """
    try:
        # Check if we have a guild (server) context
        if interaction.guild is None:
            await interaction.followup.send(ERROR_GUILD_ONLY)
            return

        # Get match data, with auto-refresh if needed
        loop = asyncio.get_event_loop()
        match_data, was_refreshed = await loop.run_in_executor(
            None, match.get_match_data_with_refresh
        )

        if match_data is None:
            # No match data available or all matches are in the past
            await interaction.followup.send(
                ERROR_MATCH_DATA_NOT_FOUND
                if not was_refreshed
                else ERROR_NO_UPCOMING_MATCH
            )
            return

        # Inform user if data was auto-refreshed
        if was_refreshed:
            await interaction.followup.send(SUCCESS_MATCH_DATA_REFRESHED)

        # Parse match datetime with Lisbon timezone
        match_dt_aware = match.match_data_to_pendulum(match_data)

        # Build event details
        event_name = f"⚽ Benfica vs {match_data['adversary']}"

        # Build event description with TV channel
        tv_channel_line = ""
        if "tv_channel" in match_data and match_data["tv_channel"]:
            tv_channel_line = f"📺 **Canal TV:** {match_data['tv_channel']}\n"

        event_description = (
            f"🏟️ **Local:** {match_data['location']}\n"
            f"🏆 **Competição:** {match_data['competition']}\n"
            f"{tv_channel_line}"
        )

        # Check if event already exists
        existing_events = interaction.guild.scheduled_events
        for existing_event in existing_events:
            if existing_event.name == event_name:
                # Discord timestamp: <t:unix:F> = full date and time
                timestamp = int(existing_event.start_time.timestamp())
                await interaction.followup.send(
                    EVENT_ALREADY_EXISTS.format(
                        name=event_name, timestamp=timestamp
                    )
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

        # Build success message with TV channel info
        success_msg = EVENT_CREATED.format(
            name=event_name, timestamp=timestamp
        )
        # Add TV channel to success message if available
        if "tv_channel" in match_data and match_data["tv_channel"]:
            success_msg += f"\n📺 {match_data['tv_channel']}"

        await interaction.followup.send(success_msg)
        logger.info(f"Created event: {event.name} (ID: {event.id})")

    except Exception as e:
        logger.error(f"Error creating event: {e}", exc_info=True)
        await interaction.followup.send(f"{ERROR_EVENT_CREATE}: {str(e)}")
