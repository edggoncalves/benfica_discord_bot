# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Discord bot that posts sports newspaper covers and Benfica match information. The bot scrapes Portuguese sports newspapers (A Bola, O Jogo, Record) and provides match scheduling features.

## Dependencies & Environment

**Dependency Management**: uv (modern Python package manager)
- Install dependencies: `uv sync`
- Install with dev tools: `uv sync --all-extras`
- Run bot: `uv run python bot.py`
- Alternative: Activate venv with `source .venv/bin/activate` then `python bot.py`

**Configuration**: Uses `.env` file for configuration (see `.env.example`):

```bash
DISCORD_TOKEN=your_bot_token_here
DISCORD_CHANNEL_ID=your_channel_id_here
SCHEDULE_HOUR=8
```

**Important**: `.env` is in `.gitignore` to protect secrets. Never commit this file. The bot will run an interactive setup wizard on first launch if no `.env` file is found.

## Architecture

### Core Components

**[bot.py](bot.py)** - Main Discord bot entry point
- Uses Discord slash commands (prefix: `/`)
- Syncs commands with Discord API on startup
- Configures APScheduler for daily automated posts at specified hour
- Sends startup message to configured channel when bot comes online
- Implements comprehensive error handling and logging
- All commands have type hints and docstrings
- Global error handler for slash commands with graceful failure recovery

**[configuration.py](configuration.py)** - Configuration management

- Manages `.env` file using python-dotenv
- Stores bot credentials (token, channel ID, schedule hour)
- Provides `setup_interactive()` wizard for first-time setup
- Functions: `exists()`, `get()`, `get_required()`
- Type hints for all functions

**[covers.py](covers.py)** - Newspaper cover scraping (async)

- Scrapes <https://24.sapo.pt/jornais/desporto> for newspaper covers (redirects to <https://sapo.pt/noticias/jornais/desporto>)
- Fully async implementation using `aiohttp` for HTTP requests with retry logic
- Parses HTML with BeautifulSoup, extracts `<img>` tags by `alt` attribute
- Creates image collage using PIL (3 newspapers side-by-side)
- Saves to `/tmp/collage.jpg` (Linux) or user temp directory (Windows)
- Comprehensive error handling and logging
- All configurable values extracted to constants (URL, NEWSPAPERS, MAX_RETRIES, REQUEST_TIMEOUT)
- **Note**: Website structure changed in Nov 2024; now uses `<img alt="a-bola">` instead of `<picture data-title="A Bola">`

**[next_match.py](next_match.py)** - Match scheduling

- Scrapes Benfica fixtures from ESPN using `requests` only (no Selenium required!)
- Extracts embedded JSON data from `window['__espnfitt__']` in ESPN page source
- Fast (<1 second) and works reliably on any VPS without memory issues
- Extracts next match date, adversary, location, competition, home/away status
- Stores match data in `match_data.json` (separate from configuration)
- Formats messages with timezone handling (Europe/Lisbon)
- Functions: `read_match_data()`, `write_match_data()`, `update_match_date()`
- `update_match_date()` returns bool for success/failure
- Comprehensive error handling for HTTP requests and JSON parsing
- Can be tested standalone: `uv run python next_match.py`

**[gen_browser.py](gen_browser.py)** - Selenium browser factory
- Creates headless Firefox WebDriver instances
- Manages geckodriver installation via webdriver-manager
- Auto-updates driver if older than `DRIVER_UPDATE_DAYS` (configurable constant)
- Proper error handling and logging
- Fixed bug: driver age check now works correctly on all paths

**[totw.py](totw.py)** - Team of the Week

- Screenshots SofaScore's Liga Portugal Betclic Team of the Week widget
- **Fully automated**: No manual updates needed!
  - Extracts current season ID from SofaScore using curl_cffi (yearly changes)
  - Extracts current matchday from Transfermarkt using curl_cffi (weekly changes)
  - Calculates SofaScore round ID using formula: `BASE_ROUND_ID + matchday`
  - Builds widget URL dynamically with both season and round
- **Performance optimized**: Uses Firefox only once (for screenshot, not data extraction)
- **Image processing**: Crops screenshot to show only team formation (50% top portion), removes branding
- Uses `curl_cffi` with Chrome impersonation to bypass bot detection (no 403 errors)
- Uses direct widget embed URL from <https://widgets.sofascore.com> (no dialogs!)
- Fallback mechanism: Uses hardcoded URL if extraction fails
- Session caching: Caches season ID and matchday to avoid repeated lookups
- **Note**: `BASE_ROUND_ID` (22524) may need adjustment if SofaScore changes their ID scheme
- Uses curl_cffi for HTTP requests, Selenium for screenshot, PIL for image cropping
- Returns cropped screenshot as Discord File (smaller file size, cleaner appearance)
- Proper browser cleanup with try/finally
- Called via thread executor in bot to avoid blocking async event loop

**[core/benfica_calendar.py](core/benfica_calendar.py)** - Benfica Calendar API client

- Primary source for match data from Benfica's official calendar API
- **Fully automated dynamic extraction**: No manual updates needed!
  - Extracts current season from checked season checkbox on calendar page
  - Extracts rank ID (team level) from checked radio button on calendar page
  - Extracts tournament IDs from checked checkboxes dynamically
  - Falls back to hardcoded constants if extraction fails
- Manages session cookies and request verification tokens
- Uses `curl_cffi` with Chrome impersonation to bypass bot protection
- Parses HTML response to extract structured match data
- Filters for upcoming matches only
- Functions: `get_next_match_from_api()` returns next match or None
- CURRENT_SEASON constant is now a fallback only (automatically extracted from page)
- Can be tested standalone: `uv run python -m core.benfica_calendar`
- Supports `--dry-run` flag to show detailed extraction info with Discord message previews
- Dry-run shows: API payload, raw response, parsed events, and previews of /quando_joga, /quanto_falta, and /criar_evento messages

### Logging

All modules use Python's `logging` module:
- **Structured JSON logging** for file output (easy to parse with jq/grep)
- Human-readable console output for development
- Log rotation (10MB files, 5 backups) to prevent disk space issues
- Each module has its own logger: `logger = logging.getLogger(__name__)`

### Health Check

The bot includes a health check mechanism for monitoring:
- Updates `bot_health.txt` every minute with current timestamp
- Monitor script at `scripts/check_bot_health.sh` checks file freshness
- Exits with code 0 (healthy), 1 (unhealthy), or 2 (error)
- Can be integrated with cron or systemd for automated monitoring

### Discord Commands

All commands use Discord's native slash command system (prefix: `/`):

- `/capas` - Posts newspaper covers immediately (prevents automatic post that day)
- `/quanto_falta` - Shows countdown to next match (requires match data)
- `/quando_joga` - Shows when next match is scheduled (requires match data)
- `/actualizar_data` - Updates match date from ESPN (fast, <1 second, no browser needed)
- `/equipa_semana` - Posts SofaScore team of the week screenshot (rate-limited to once per day)
- `/criar_evento` - Creates a Discord scheduled event for the next match (requires match data and Manage Events permission)

All commands have proper error handling and provide user feedback on failures.

**Performance optimization**: `/equipa_semana` runs Selenium in a thread executor to avoid blocking Discord's async event loop. `/actualizar_data` is now fast enough to run directly without threading.

### Scheduled Tasks

**Daily Covers Post** (APScheduler CronTrigger)

- Runs at hour specified in `.env` (SCHEDULE_HOUR)
- Posts newspaper covers to configured channel
- Uses `last_run` dict to prevent duplicate posts on same day
- Comprehensive error handling with logging
- Validates channel exists before posting
- Validates file exists before attempting to send

### Data Flow

1. Bot reads config from `.env` on startup (with validation)
2. Scheduler triggers `daily_covers()` at configured hour
3. `covers.sports_covers()` asynchronously scrapes, creates collage, returns file path
4. Bot validates file exists and channel is accessible
5. Bot posts collage to Discord channel
6. Errors are logged and handled gracefully

### Browser Automation

Selenium operations (where needed) use Firefox in headless mode:
- [gen_browser.py](gen_browser.py) provides centralized browser creation
- Currently only used by [totw.py](totw.py) for SofaScore screenshots
- [next_match.py](next_match.py) now uses requests-only approach (no browser needed)
- Proper cleanup in try/finally blocks prevents resource leaks
- Requires Firefox installed on system for TOTW feature

### Timezone Handling

- Bot operates in Europe/Lisbon timezone
- Uses `pendulum` library for timezone conversions
- Match times stored in `match_data.json` in local time

## Code Quality Standards

### Type Hints
- All functions have type hints for parameters and return values
- Union types use `Type | None` syntax (Python 3.10+)
- Complex types use `typing.Dict`, `typing.Any` where needed

### Error Handling
- All external operations (HTTP, Discord, file I/O) wrapped in try/except
- Specific exception types caught where possible
- Errors logged before re-raising or returning None
- User-friendly error messages sent to Discord

### Documentation
- All public functions have docstrings with Args/Returns/Raises sections
- Module-level docstrings explain purpose
- Comments explain "why" not "what"

### Code Style
- PEP 8 compliant (79 character line limit)
- Constants in UPPER_CASE at module level
- Private functions prefixed with underscore
- Consistent string formatting (f-strings)

## Development Notes

### Match Features

Match-related features (`/quanto_falta`, `/quando_joga`, `/actualizar_data`) are fully functional:

- Now use ESPN as data source (fast and reliable)
- No Selenium dependency for match scraping
- Work on any VPS without resource concerns
- Update match data with `/actualizar_data` command

### Resource Management

Fixed issues:
- Browser instances now properly closed in all code paths
- File handles use context managers
- Async HTTP sessions properly cleaned up

### Testing

To test locally:

1. Copy `.env.example` to `.env` OR run `uv run python bot.py` to launch setup wizard
2. Add your Discord bot token and channel ID
3. Run with `uv run python bot.py`
4. Test commands in Discord channel

### Security

- `.env` contains sensitive data and is in `.gitignore`
- Never commit tokens or credentials
- Use `.env.example` as template for others
- Bot provides interactive setup wizard for first-time configuration
