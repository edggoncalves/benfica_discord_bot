"""Centralized file path configuration.

All file paths used by the bot are defined here for easy maintenance
and testing.
"""

from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Data files (stored in project root)
MATCH_DATA_FILE = PROJECT_ROOT / "match_data.json"
LAST_RUN_FILE = PROJECT_ROOT / "last_run.json"

# Temporary files (system temp directory)
TEMP_DIR = Path("/tmp") if Path("/tmp").exists() else Path.home() / "tmp"
TOTW_SCREENSHOT_PATH = TEMP_DIR / "totw_screenshot.png"

# Log files (stored in project root)
LOG_FILE = PROJECT_ROOT / "bot.log"
