"""Discord slash command for creating scheduled events."""

import asyncio
import logging

import discord
import pendulum

from config.constants import (
    ERROR_EVENT_CREATE,
    ERROR_GUILD_ONLY,
    ERROR_INVALID_QUANTITY,
    ERROR_NO_MATCHES_FOUND,
)
from core.benfica_calendar import get_upcoming_matches

logger = logging.getLogger(__name__)


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

        # Silently cap at 10
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
                # Build event name
                event_name = f"⚽ Benfica vs {match['adversary']}"

                # Parse match datetime with Lisbon timezone
                match_dt_aware = pendulum.parse(
                    f"{match['date']} {match['time']}",
                    tz="Europe/Lisbon",
                )

                # Build event description with TV channel
                tv_channel_line = ""
                if match.get("tv_channel"):
                    tv_channel_line = (
                        f"📺 **Canal TV:** {match['tv_channel']}\n"
                    )

                event_description = (
                    f"🏟️ **Local:** {match['location']}\n"
                    f"🏆 **Competição:** {match['competition']}\n"
                    f"{tv_channel_line}"
                )

                # Check if event already exists
                existing_event = None
                for e in interaction.guild.scheduled_events:
                    if e.name == event_name:
                        existing_event = e
                        break

                if existing_event:
                    # Compare details to see if update is needed
                    time_diff = abs(
                        (existing_event.start_time - match_dt_aware).total_seconds()  # noqa: E501
                    )
                    needs_update = (
                        existing_event.description != event_description
                        or existing_event.location != match["location"]
                        or time_diff > 60  # More than 1 minute difference
                    )

                    if needs_update:
                        # Update the event
                        end_time = match_dt_aware.add(hours=2)
                        await existing_event.edit(
                            description=event_description,
                            start_time=match_dt_aware,
                            end_time=end_time,
                            location=match["location"],
                        )
                        updated_count += 1
                        logger.info(
                            f"Updated event: {event_name} (ID: {existing_event.id})"  # noqa: E501
                        )
                    else:
                        unchanged_count += 1
                        logger.debug(f"Event unchanged: {event_name}")
                else:
                    # Create new event
                    # Event end time is 2 hours after start
                    end_time = match_dt_aware.add(hours=2)

                    event = await interaction.guild.create_scheduled_event(
                        name=event_name,
                        description=event_description,
                        start_time=match_dt_aware,
                        end_time=end_time,
                        entity_type=discord.EntityType.external,
                        location=match["location"],
                        privacy_level=discord.PrivacyLevel.guild_only,
                    )
                    created_count += 1
                    logger.info(f"Created event: {event.name} (ID: {event.id})")  # noqa: E501

            except Exception as e:
                logger.error(
                    f"Error processing event for {match.get('adversary', 'Unknown')}: {e}",  # noqa: E501
                    exc_info=True,
                )
                errors.append(
                    f"{match.get('adversary', 'Unknown')}: {str(e)}"
                )

        # Send summary message with all changes
        summary_lines = []
        if created_count > 0:
            summary_lines.append(f"✅ Criados: {created_count}")
        if updated_count > 0:
            summary_lines.append(f"🔄 Atualizados: {updated_count}")
        if unchanged_count > 0:
            summary_lines.append(f"✓ Sem alterações: {unchanged_count}")
        if errors:
            summary_lines.append(f"❌ Erros: {len(errors)}")

        summary = "📅 **Resumo:**\n" + "\n".join(summary_lines)
        await interaction.followup.send(summary)

    except Exception as e:
        logger.error(f"Error in criar_evento_command: {e}", exc_info=True)
        await interaction.followup.send(f"{ERROR_EVENT_CREATE}: {str(e)}")
