"""Decorators for Discord command handlers."""

import asyncio
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

import discord

logger = logging.getLogger(__name__)


def async_command(
    *,
    error_message: str,
    run_in_executor: bool = False,
):
    """Decorator for async Discord command handlers.

    Handles common patterns:
    - Running blocking functions in executor
    - Error handling and logging
    - Sending error responses

    Args:
        error_message: Error message to send if command fails.
        run_in_executor: Whether to run the wrapped function in executor.

    Example:
        @async_command(error_message="Failed to fetch data")
        async def my_command(interaction: discord.Interaction) -> None:
            result = await some_async_operation()
            await interaction.followup.send(result)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(
            interaction: discord.Interaction, *args: Any, **kwargs: Any
        ) -> None:
            try:
                if run_in_executor:
                    # Run blocking function in executor
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None, lambda: func(interaction, *args, **kwargs)
                    )
                else:
                    # Run as normal async function
                    await func(interaction, *args, **kwargs)

            except FileNotFoundError as e:
                logger.error(f"File not found in {func.__name__}: {e}")
                await interaction.followup.send(error_message)
            except Exception as e:
                logger.error(
                    f"Error in {func.__name__}: {e}", exc_info=True
                )
                await interaction.followup.send(error_message)

        return wrapper

    return decorator


def sync_command(
    error_message: str, file_not_found_message: str | None = None
):
    """Decorator for Discord commands that wrap synchronous functions.

    Handles:
    - Running synchronous function in executor
    - Error handling and logging
    - Sending responses via followup

    Args:
        error_message: Error message to send if command fails.
        file_not_found_message: Optional custom message for FileNotFoundError.
            If None, uses error_message.

    Example:
        @sync_command(
            error_message="Failed",
            file_not_found_message="File not found"
        )
        async def update_command(interaction: discord.Interaction) -> None:
            result = blocking_function()
            await interaction.followup.send(result)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(
            interaction: discord.Interaction, *args: Any, **kwargs: Any
        ) -> None:
            try:
                # Run the async function normally (which will call sync
                # functions inside it)
                await func(interaction, *args, **kwargs)

            except FileNotFoundError as e:
                logger.error(
                    f"File not found in {func.__name__}: {e}"
                )
                msg = (
                    file_not_found_message
                    if file_not_found_message
                    else error_message
                )
                await interaction.followup.send(msg)
            except Exception as e:
                logger.error(
                    f"Error in {func.__name__}: {e}", exc_info=True
                )
                await interaction.followup.send(error_message)

        return wrapper

    return decorator
