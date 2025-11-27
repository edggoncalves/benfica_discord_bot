"""Tests for commands.covers module."""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from commands.covers import capas_command


@pytest.mark.asyncio
async def test_capas_command_success():
    """Test successful capas command execution."""
    mock_interaction = MagicMock(spec=discord.Interaction)
    mock_interaction.followup = AsyncMock()
    mock_interaction.user = MagicMock()

    mock_files = [MagicMock(spec=discord.File) for _ in range(3)]

    with patch(
        "commands.covers.get_covers_as_discord_files", return_value=mock_files
    ):
        await capas_command(mock_interaction)

        mock_interaction.followup.send.assert_called_once()
        call_kwargs = mock_interaction.followup.send.call_args[1]
        assert "files" in call_kwargs
        assert len(call_kwargs["files"]) == 3


@pytest.mark.asyncio
async def test_capas_command_error_handling():
    """Test capas command handles errors gracefully."""
    mock_interaction = MagicMock(spec=discord.Interaction)
    mock_interaction.followup = AsyncMock()
    mock_interaction.user = MagicMock()

    with patch(
        "commands.covers.get_covers_as_discord_files",
        side_effect=Exception("Test error"),
    ):
        await capas_command(mock_interaction)

        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args[0]
        assert "❌" in call_args[0]  # Error message
