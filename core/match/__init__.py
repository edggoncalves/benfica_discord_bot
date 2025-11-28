"""Match module - Handles match data fetching, storage, and formatting.

This module provides a clean API for managing Benfica match information:
- Fetching from multiple sources (Benfica API primary, ESPN fallback)
- Storing and retrieving match data
- Formatting messages for Discord
- Auto-refreshing stale data
"""

# Public API exports - maintain backward compatibility with old match.py
from core.match.formatter import (
    format_countdown_message as how_long_until,
)
from core.match.formatter import (
    format_match_schedule_message as when_is_it,
)
from core.match.refresh import (
    get_match_data_with_refresh,
)
from core.match.refresh import (
    update_match_data as update_match_date,
)
from core.match.repository import (
    load_match_data as read_match_data,
)
from core.match.repository import (
    match_data_to_pendulum,
)
from core.match.repository import (
    save_match_data as write_match_data,
)
from core.match.sources import (
    fetch_next_match as get_next_match,
)
from core.match.sources import (
    normalize_match_data as _normalize_match_data,
)

__all__ = [
    # Main functions (for backward compatibility)
    "how_long_until",
    "when_is_it",
    "update_match_date",
    "read_match_data",
    "write_match_data",
    "get_next_match",
    "match_data_to_pendulum",
    "get_match_data_with_refresh",
    # For tests (backward compatibility)
    "_normalize_match_data",
]
