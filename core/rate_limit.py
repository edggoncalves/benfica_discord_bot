"""Rate limiting utilities for Discord commands."""

import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from functools import wraps
from typing import Any

import discord

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter for Discord commands.

    Uses a dictionary to track the last call time for each user/command
    combination. More efficient than file-based tracking and suitable for
    single-instance bots on VPS.
    """

    def __init__(self):
        """Initialize rate limiter with empty tracking dict."""
        self._last_calls: dict[str, datetime] = {}

    def is_allowed(self, key: str, min_interval: timedelta) -> bool:
        """Check if an action is allowed based on rate limit.

        Args:
            key: Unique key for the rate-limited action (e.g., "user_id:cmd").
            min_interval: Minimum time between allowed calls.

        Returns:
            True if action is allowed, False if rate limited.
        """
        now = datetime.now()
        last_call = self._last_calls.get(key)

        if last_call is None or (now - last_call) >= min_interval:
            self._last_calls[key] = now
            return True

        return False

    def get_remaining_time(self, key: str, min_interval: timedelta) -> int:
        """Get remaining seconds until rate limit resets.

        Args:
            key: Unique key for the rate-limited action.
            min_interval: Minimum time between allowed calls.

        Returns:
            Remaining seconds, or 0 if not rate limited.
        """
        last_call = self._last_calls.get(key)
        if last_call is None:
            return 0

        elapsed = datetime.now() - last_call
        remaining = min_interval - elapsed

        return max(0, int(remaining.total_seconds()))

    def reset(self, key: str) -> None:
        """Reset rate limit for a specific key.

        Args:
            key: Key to reset.
        """
        self._last_calls.pop(key, None)


# Global rate limiter instance
_rate_limiter = RateLimiter()


def rate_limit(
    *,
    per_user: bool = True,
    interval: timedelta = timedelta(hours=24),
    message: str = "This command is rate-limited. Try again later.",
):
    """Decorator for rate-limiting Discord commands.

    Args:
        per_user: If True, limit per user. If False, limit globally.
        interval: Minimum time between allowed calls.
        message: Message to send when rate limited.

    Example:
        @rate_limit(per_user=True, interval=timedelta(hours=24))
        async def my_command(interaction: discord.Interaction) -> None:
            # Command logic here
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(
            interaction: discord.Interaction, *args: Any, **kwargs: Any
        ) -> Any:
            # Generate rate limit key
            if per_user:
                key = f"{func.__name__}:{interaction.user.id}"
            else:
                key = func.__name__

            # Check rate limit
            if not _rate_limiter.is_allowed(key, interval):
                remaining = _rate_limiter.get_remaining_time(key, interval)
                logger.info(
                    f"Rate limit hit for {func.__name__} by "
                    f"{interaction.user} ({remaining}s remaining)"
                )
                await interaction.followup.send(
                    f"{message} ({remaining}s remaining)", ephemeral=True
                )
                return None

            # Execute command
            return await func(interaction, *args, **kwargs)

        return wrapper

    return decorator
