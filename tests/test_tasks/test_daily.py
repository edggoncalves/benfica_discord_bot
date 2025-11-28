"""Tests for tasks.daily module."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from tasks import daily


@pytest.fixture
def temp_last_run_file(tmp_path, monkeypatch):
    """Create a temporary last_run.json file for testing."""
    test_file = tmp_path / "last_run.json"
    monkeypatch.setattr(daily, "LAST_RUN_FILE", test_file)
    yield test_file
    # Cleanup
    if test_file.exists():
        test_file.unlink()


def test_get_today_date():
    """Test _get_today_date returns correct date string."""
    with patch("tasks.daily.datetime") as mock_datetime:
        # Mock a specific date
        mock_now = MagicMock()
        mock_now.strftime.return_value = "2025-11-24"
        mock_datetime.now.return_value = mock_now

        result = daily._get_today_date()

        assert result == "2025-11-24"
        assert isinstance(result, str)


def test_get_last_run_date_file_not_exists(temp_last_run_file):
    """Test _get_last_run_date returns None when file doesn't exist."""
    result = daily._get_last_run_date(123456789)
    assert result is None


def test_get_last_run_date_success(temp_last_run_file):
    """Test _get_last_run_date returns date for channel."""
    # Write test data
    temp_last_run_file.write_text(
        json.dumps({"123456789": "2025-11-24", "987654321": "2025-11-23"})
    )

    result = daily._get_last_run_date(123456789)
    assert result == "2025-11-24"

    result = daily._get_last_run_date(987654321)
    assert result == "2025-11-23"


def test_get_last_run_date_channel_not_found(temp_last_run_file):
    """Test _get_last_run_date returns None for unknown channel."""
    temp_last_run_file.write_text(json.dumps({"123456789": "2025-11-24"}))

    result = daily._get_last_run_date(999999999)
    assert result is None


def test_get_last_run_date_invalid_json(temp_last_run_file):
    """Test _get_last_run_date handles invalid JSON gracefully."""
    temp_last_run_file.write_text("invalid json{")

    result = daily._get_last_run_date(123456789)
    assert result is None


def test_save_last_run_date_new_file(temp_last_run_file):
    """Test _save_last_run_date creates new file."""
    daily._save_last_run_date(123456789, "2025-11-24")

    assert temp_last_run_file.exists()
    data = json.loads(temp_last_run_file.read_text())
    assert data == {"123456789": "2025-11-24"}


def test_save_last_run_date_update_existing(temp_last_run_file):
    """Test _save_last_run_date updates existing channel."""
    # Write initial data
    temp_last_run_file.write_text(json.dumps({"123456789": "2025-11-23"}))

    # Update
    daily._save_last_run_date(123456789, "2025-11-24")

    data = json.loads(temp_last_run_file.read_text())
    assert data == {"123456789": "2025-11-24"}


def test_save_last_run_date_multiple_channels(temp_last_run_file):
    """Test _save_last_run_date preserves other channels."""
    # Write initial data with multiple channels
    temp_last_run_file.write_text(
        json.dumps({"123456789": "2025-11-23", "987654321": "2025-11-22"})
    )

    # Update one channel
    daily._save_last_run_date(123456789, "2025-11-24")

    data = json.loads(temp_last_run_file.read_text())
    assert data == {"123456789": "2025-11-24", "987654321": "2025-11-22"}


def test_save_last_run_date_add_new_channel(temp_last_run_file):
    """Test _save_last_run_date adds new channel without affecting others."""
    # Write initial data
    temp_last_run_file.write_text(json.dumps({"123456789": "2025-11-24"}))

    # Add new channel
    daily._save_last_run_date(987654321, "2025-11-25")

    data = json.loads(temp_last_run_file.read_text())
    assert data == {"123456789": "2025-11-24", "987654321": "2025-11-25"}


@pytest.mark.asyncio
async def test_daily_covers_success(temp_last_run_file):
    """Test daily_covers posts covers successfully."""
    mock_bot = MagicMock()
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.name = "test-channel"
    mock_bot.get_channel.return_value = mock_channel

    mock_files = [MagicMock(spec=discord.File) for _ in range(3)]

    with patch("tasks.daily._get_today_date", return_value="2025-11-24"):
        with patch(
            "tasks.daily.get_covers_as_discord_files", return_value=mock_files
        ):
            await daily.daily_covers(mock_bot, 123456789)

            # Verify channel was fetched
            mock_bot.get_channel.assert_called_once_with(123456789)

            # Verify covers were sent
            mock_channel.send.assert_called_once()
            call_kwargs = mock_channel.send.call_args[1]
            assert "files" in call_kwargs
            assert call_kwargs["files"] == mock_files

            # Verify last_run was saved
            data = json.loads(temp_last_run_file.read_text())
            assert data == {"123456789": "2025-11-24"}


@pytest.mark.asyncio
async def test_daily_covers_already_run_today(temp_last_run_file):
    """Test daily_covers skips if already run today."""
    # Set channel as already run today
    temp_last_run_file.write_text(json.dumps({"123456789": "2025-11-24"}))

    mock_bot = MagicMock()
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_bot.get_channel.return_value = mock_channel

    with patch("tasks.daily._get_today_date", return_value="2025-11-24"):
        with patch(
            "tasks.daily.get_covers_as_discord_files"
        ) as mock_get_covers:
            await daily.daily_covers(mock_bot, 123456789)

            # Verify covers were NOT fetched
            mock_get_covers.assert_not_called()

            # Verify nothing was sent
            mock_channel.send.assert_not_called()


@pytest.mark.asyncio
async def test_daily_covers_multiple_channels_independent(temp_last_run_file):
    """Test daily_covers tracks channels independently."""
    # Channel 1 already ran today
    temp_last_run_file.write_text(json.dumps({"111111111": "2025-11-24"}))

    mock_bot = MagicMock()
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.name = "test-channel"
    mock_bot.get_channel.return_value = mock_channel

    mock_files = [MagicMock(spec=discord.File) for _ in range(3)]

    with patch("tasks.daily._get_today_date", return_value="2025-11-24"):
        with patch(
            "tasks.daily.get_covers_as_discord_files", return_value=mock_files
        ):
            # Channel 2 should still run
            await daily.daily_covers(mock_bot, 222222222)

            # Verify covers were sent
            mock_channel.send.assert_called_once()

            # Verify both channels are tracked
            data = json.loads(temp_last_run_file.read_text())
            assert data == {
                "111111111": "2025-11-24",
                "222222222": "2025-11-24",
            }


@pytest.mark.asyncio
async def test_daily_covers_channel_not_found(temp_last_run_file):
    """Test daily_covers handles missing channel gracefully."""
    mock_bot = MagicMock()
    mock_bot.get_channel.return_value = None

    with patch("tasks.daily._get_today_date", return_value="2025-11-24"):
        with patch(
            "tasks.daily.get_covers_as_discord_files"
        ) as mock_get_covers:
            await daily.daily_covers(mock_bot, 123456789)

            # Verify channel was attempted to be fetched
            mock_bot.get_channel.assert_called_once_with(123456789)

            # Verify covers were NOT fetched
            mock_get_covers.assert_not_called()

            # Verify last_run was NOT saved
            assert not temp_last_run_file.exists()


@pytest.mark.asyncio
async def test_daily_covers_get_covers_error(temp_last_run_file):
    """Test daily_covers handles get_covers error gracefully."""
    mock_bot = MagicMock()
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.name = "test-channel"
    mock_bot.get_channel.return_value = mock_channel

    with patch("tasks.daily._get_today_date", return_value="2025-11-24"):
        with patch(
            "tasks.daily.get_covers_as_discord_files",
            side_effect=ValueError("Test error"),
        ):
            # Should not raise exception
            await daily.daily_covers(mock_bot, 123456789)

            # Verify nothing was sent
            mock_channel.send.assert_not_called()

            # Verify last_run was NOT saved
            assert not temp_last_run_file.exists()


@pytest.mark.asyncio
async def test_daily_covers_send_error(temp_last_run_file):
    """Test daily_covers handles send error gracefully."""
    mock_bot = MagicMock()
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.name = "test-channel"
    mock_channel.send.side_effect = discord.HTTPException(
        MagicMock(), "Send failed"
    )
    mock_bot.get_channel.return_value = mock_channel

    mock_files = [MagicMock(spec=discord.File) for _ in range(3)]

    with patch("tasks.daily._get_today_date", return_value="2025-11-24"):
        with patch(
            "tasks.daily.get_covers_as_discord_files", return_value=mock_files
        ):
            # Should not raise exception
            await daily.daily_covers(mock_bot, 123456789)

            # Verify send was attempted
            mock_channel.send.assert_called_once()

            # Verify last_run was NOT saved (since send failed)
            assert not temp_last_run_file.exists()


@pytest.mark.asyncio
async def test_daily_covers_runs_again_next_day(temp_last_run_file):
    """Test daily_covers can run again on a different day."""
    mock_bot = MagicMock()
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.name = "test-channel"
    mock_bot.get_channel.return_value = mock_channel

    mock_files = [MagicMock(spec=discord.File) for _ in range(3)]

    # Run on first day
    with patch("tasks.daily._get_today_date", return_value="2025-11-24"):
        with patch(
            "tasks.daily.get_covers_as_discord_files", return_value=mock_files
        ):
            await daily.daily_covers(mock_bot, 123456789)

        data = json.loads(temp_last_run_file.read_text())
        assert data == {"123456789": "2025-11-24"}
        mock_channel.send.assert_called_once()

    # Try to run again on same day (should skip)
    mock_channel.send.reset_mock()
    with patch("tasks.daily._get_today_date", return_value="2025-11-24"):
        with patch(
            "tasks.daily.get_covers_as_discord_files", return_value=mock_files
        ):
            await daily.daily_covers(mock_bot, 123456789)

        mock_channel.send.assert_not_called()

    # Run on next day (should work)
    mock_channel.send.reset_mock()
    with patch("tasks.daily._get_today_date", return_value="2025-11-25"):
        with patch(
            "tasks.daily.get_covers_as_discord_files", return_value=mock_files
        ):
            await daily.daily_covers(mock_bot, 123456789)

        data = json.loads(temp_last_run_file.read_text())
        assert data == {"123456789": "2025-11-25"}
        mock_channel.send.assert_called_once()
