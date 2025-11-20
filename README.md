# Benfica Discord Bot

A Discord bot that posts Portuguese sports newspaper covers and Benfica match information.

## Features

- 📰 Daily automated posting of newspaper covers (A Bola, O Jogo, Record)
- ⚽ Match scheduling and countdown features (currently disabled)
- 📊 Team of the week screenshots from SofaScore
- 🔄 Automatic newspaper cover collage creation
- ⏰ Configurable scheduling with timezone support

## Quick Start

### Prerequisites

- Python 3.11+
- Firefox (for Selenium web scraping)
- Discord bot token with permissions integer `2415943744`
  - Required permissions: Send Messages, Embed Links, Attach Files, Read Message History, Manage Events

### Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

### Discord Bot Setup

1. **Create Discord Application**
   - Go to <https://discord.com/developers/applications>
   - Create a new application
   - Go to "Bot" section and create a bot
   - Under "Privileged Gateway Intents", enable **Message Content Intent**
   - Copy the bot token

2. **Invite Bot to Server**
   - Go to OAuth2 → URL Generator
   - Select scope: `bot`
   - Select permissions integer: `2415943744` (or use the checkboxes for: Send Messages, Embed Links, Attach Files, Read Message History, Manage Events)
   - Copy and visit the generated URL to invite the bot

### Configuration

The bot will automatically run a setup wizard on first launch. Alternatively, you can manually create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
DISCORD_TOKEN=your_bot_token_here
DISCORD_CHANNEL_ID=your_channel_id_here
SCHEDULE_HOUR=8
```

⚠️ **Important**: `.env` is in `.gitignore` - never commit secrets!

### Running

```bash
# Run the bot
uv run python bot.py

# Or activate virtual environment
source .venv/bin/activate  # Linux/Mac
python bot.py
```

## Discord Commands

- `!capas` - Post newspaper covers immediately
- `!equipa_semana` - Post team of the week screenshot
- `!actualizar_data` - Update next match date from website
- `!quanto_falta` - Show countdown to next match
- `!quando_joga` - Show when next match is scheduled
- `!evento` - Generate formatted match event text
- `!criar_evento` - Create a Discord scheduled event for the next match

**Note**: Match-related commands (`!quanto_falta`, `!quando_joga`, `!evento`, `!criar_evento`) require running `!actualizar_data` first to fetch match information.

## Development

### Install Dev Dependencies

```bash
uv sync --all-extras
```

### Code Quality Tools

```bash
# Linting
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .

# Type checking
uv run mypy .

# Run tests (when available)
uv run pytest
```

### Project Structure

```text
.
├── bot.py              # Main bot entry point
├── configuration.py    # Config file management
├── covers.py          # Newspaper scraping (async)
├── next_match.py      # Match scheduling
├── gen_browser.py     # Selenium browser factory
├── totw.py           # Team of the week screenshots
├── classes/
│   └── cookies.py     # Calendar API client (experimental)
├── .env               # Configuration (gitignored)
└── match_data.json    # Match data cache (gitignored)
```

## Recent Improvements

This project was recently polished with:

### Code Quality

- ✅ 100% type hint coverage
- ✅ 100% docstring coverage
- ✅ Comprehensive error handling
- ✅ Proper logging throughout
- ✅ PEP 8 compliant
- ✅ Modern Python 3.9+ syntax

### Bug Fixes

- ✅ Fixed resource leaks (browser instances)
- ✅ Fixed driver age check logic
- ✅ Removed unused code
- ✅ Fixed None handling

### Architecture

- ✅ Async HTTP with aiohttp
- ✅ Constants extracted from code
- ✅ Code duplication eliminated
- ✅ Security best practices

### Migration to uv

- ✅ Migrated from Poetry to uv
- ✅ Standard PEP 621 pyproject.toml
- ✅ 10-100x faster dependency management

## Documentation

- `CLAUDE.md` - Detailed architecture and development guide
- `IMPROVEMENTS.md` - Complete changelog of improvements
- `MIGRATION_TO_UV.md` - Poetry to uv migration guide

## License

See LICENSE file.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run `uv run ruff check --fix .` before committing
4. Submit a pull request

## Troubleshooting

### Bot won't start

- Check `.env` exists and has valid token
- Ensure Firefox is installed (for Selenium)
- Run `uv sync` to install dependencies

### PrivilegedIntentsRequired error

- Go to Discord Developer Portal → Your Application → Bot
- Under "Privileged Gateway Intents", enable **Message Content Intent**
- Restart the bot

### Commands not working

- Verify bot has correct Discord permissions (use integer `2147862592` when inviting)
- Ensure Message Content Intent is enabled in Developer Portal
- Check `.env` channel ID is correct
- Review logs for error messages

### Newspaper covers not posting

- Check internet connection
- Verify <https://24.sapo.pt/jornais/desporto> is accessible
- Check logs for HTTP errors
