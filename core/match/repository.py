"""Match data repository - File I/O operations."""

import json
import logging

import pendulum

from config.constants import TIMEZONE
from config.paths import MATCH_DATA_FILE

logger = logging.getLogger(__name__)


def save_match_data(info: dict) -> None:
    """Write match information to JSON file.

    Args:
        info: Dictionary containing match data with date, adversary,
              location, competition, and optional tv_channel keys.
    """
    data = {
        "year": info["date"].year,
        "month": info["date"].month,
        "day": info["date"].day,
        "hour": info["date"].hour,
        "minute": info["date"].minute,
        "adversary": info["adversary"],
        "location": info["location"],
        "competition": info["competition"],
    }
    # Add TV channel if available
    if "tv_channel" in info and info["tv_channel"]:
        data["tv_channel"] = info["tv_channel"]

    with open(MATCH_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
    logger.info("Match data saved")


def load_match_data() -> dict:
    """Read match information from JSON file.

    Returns:
        Dictionary with match data.

    Raises:
        FileNotFoundError: If match data file doesn't exist.
    """
    if not MATCH_DATA_FILE.exists():
        raise FileNotFoundError(
            "Match data not found. Run !actualizar_data first."
        )
    with open(MATCH_DATA_FILE) as f:
        return json.load(f)


def match_data_to_pendulum(match_data: dict) -> pendulum.DateTime:
    """Convert match data dict to timezone-aware pendulum datetime.

    Args:
        match_data: Dictionary with year, month, day, hour, minute keys.

    Returns:
        Timezone-aware pendulum datetime in Lisbon timezone.
    """
    return pendulum.datetime(
        year=match_data["year"],
        month=match_data["month"],
        day=match_data["day"],
        hour=match_data["hour"],
        minute=match_data["minute"],
        tz=TIMEZONE,
    )
