"""Configuration validation utilities."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def validate_discord_token(token: str) -> bool:
    """Validate Discord bot token format.

    Args:
        token: Discord bot token to validate.

    Returns:
        True if token format is valid, False otherwise.
    """
    # Discord tokens are base64 encoded, typically 59+ chars
    # Should not start with placeholder text
    return (
        len(token) > 50
        and not token.startswith("your_")
        and not token.startswith("YOUR_")
    )


def validate_channel_id(channel_id: str) -> bool:
    """Validate Discord channel ID format.

    Args:
        channel_id: Discord channel ID to validate.

    Returns:
        True if channel ID format is valid, False otherwise.
    """
    # Discord channel IDs are snowflakes (64-bit integers)
    # Typically 17-20 digits
    return channel_id.isdigit() and len(channel_id) >= 17


def validate_schedule_hour(hour: str) -> bool:
    """Validate schedule hour is 0-23.

    Args:
        hour: Hour value to validate.

    Returns:
        True if hour is valid (0-23), False otherwise.
    """
    if not hour.isdigit():
        return False

    hour_int = int(hour)
    return 0 <= hour_int <= 23


def validate_rate_limit_hours(hours: str) -> bool:
    """Validate rate limit hours is a positive integer.

    Args:
        hours: Hours value to validate.

    Returns:
        True if hours is valid (positive integer), False otherwise.
    """
    if not hours.isdigit():
        return False

    hours_int = int(hours)
    return hours_int > 0


def validate_config(config: dict[str, Any]) -> list[str]:
    """Validate all configuration values.

    Args:
        config: Dictionary of configuration key-value pairs.

    Returns:
        List of validation error messages (empty if all valid).

    Example:
        >>> config = {
        ...     "DISCORD_TOKEN": "valid_token_here",
        ...     "DISCORD_CHANNEL_ID": "123456789012345678",
        ...     "SCHEDULE_HOUR": "8"
        ... }
        >>> errors = validate_config(config)
        >>> if errors:
        ...     print("Config errors:", errors)
    """
    errors = []

    # Validate Discord token
    token = config.get("DISCORD_TOKEN", "")
    if not validate_discord_token(token):
        errors.append(
            "Invalid DISCORD_TOKEN format (must be >50 chars "
            "and not be a placeholder)"
        )

    # Validate channel ID
    channel_id = config.get("DISCORD_CHANNEL_ID", "")
    if not validate_channel_id(channel_id):
        errors.append(
            "Invalid DISCORD_CHANNEL_ID format "
            "(must be numeric and >= 17 digits)"
        )

    # Validate schedule hour
    hour = config.get("SCHEDULE_HOUR", "8")
    if not validate_schedule_hour(hour):
        errors.append("SCHEDULE_HOUR must be a number between 0 and 23")

    if errors:
        logger.error(f"Configuration validation failed: {errors}")
    else:
        logger.info("Configuration validation passed")

    return errors
