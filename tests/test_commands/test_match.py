"""Tests for commands.match module."""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from commands.match import (
    actualizar_data_command,
    quando_joga_command,
    quanto_falta_command,
)


@pytest.mark.asyncio
async def test_quanto_falta_command_success():
    """Test successful quanto_falta command."""
    mock_interaction = MagicMock(spec=discord.Interaction)
    mock_interaction.followup = AsyncMock()

    with patch("core.match.how_long_until", return_value="Faltam 5 dias"):
        await quanto_falta_command(mock_interaction)

        mock_interaction.followup.send.assert_called_once_with("Faltam 5 dias")


@pytest.mark.asyncio
async def test_quanto_falta_command_file_not_found():
    """Test quanto_falta when match data file not found."""
    mock_interaction = MagicMock(spec=discord.Interaction)
    mock_interaction.followup = AsyncMock()

    with patch("core.match.how_long_until", side_effect=FileNotFoundError):
        await quanto_falta_command(mock_interaction)

        call_args = mock_interaction.followup.send.call_args[0]
        assert "não encontrados" in call_args[0]


@pytest.mark.asyncio
async def test_quando_joga_command_success():
    """Test successful quando_joga command."""
    mock_interaction = MagicMock(spec=discord.Interaction)
    mock_interaction.followup = AsyncMock()

    with patch("core.match.when_is_it", return_value="Benfica joga amanhã"):
        await quando_joga_command(mock_interaction)

        mock_interaction.followup.send.assert_called_once_with("Benfica joga amanhã")


@pytest.mark.asyncio
async def test_actualizar_data_command_success():
    """Test successful match data update."""
    mock_interaction = MagicMock(spec=discord.Interaction)
    mock_interaction.followup = AsyncMock()

    with patch("core.match.update_match_date", return_value=True):
        await actualizar_data_command(mock_interaction)

        call_args = mock_interaction.followup.send.call_args[0]
        assert "✅" in call_args[0]


@pytest.mark.asyncio
async def test_actualizar_data_command_failure():
    """Test match data update failure."""
    mock_interaction = MagicMock(spec=discord.Interaction)
    mock_interaction.followup = AsyncMock()

    with patch("core.match.update_match_date", return_value=False):
        await actualizar_data_command(mock_interaction)

        call_args = mock_interaction.followup.send.call_args[0]
        assert "❌" in call_args[0]
