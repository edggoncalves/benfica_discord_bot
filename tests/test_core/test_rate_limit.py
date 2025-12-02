"""Tests for rate limiting functionality."""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from core.rate_limit import _format_remaining_time, _rate_limiter, rate_limit


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter between tests."""
    _rate_limiter._last_calls.clear()
    yield
    _rate_limiter._last_calls.clear()


class TestFormatRemainingTime:
    """Tests for the _format_remaining_time helper function."""

    def test_format_seconds(self):
        """Test formatting when less than 60 seconds."""
        assert _format_remaining_time(30) == "30s"
        assert _format_remaining_time(59) == "59s"
        assert _format_remaining_time(1) == "1s"

    def test_format_minutes(self):
        """Test formatting when 60-3599 seconds."""
        assert _format_remaining_time(60) == "1m"
        assert _format_remaining_time(120) == "2m"
        assert _format_remaining_time(1800) == "30m"
        assert _format_remaining_time(3599) == "59m"

    def test_format_hours(self):
        """Test formatting when >= 3600 seconds."""
        assert _format_remaining_time(3600) == "1h"
        assert _format_remaining_time(7200) == "2h"
        assert _format_remaining_time(86400) == "24h"
        assert _format_remaining_time(90000) == "25h"


class TestRateLimitKeyGeneration:
    """Tests for rate limit key generation."""

    @pytest.fixture
    def mock_interaction(self):
        """Create a mock Discord interaction."""
        interaction = Mock()
        interaction.user.id = 12345
        interaction.guild_id = 67890
        interaction.followup = AsyncMock()
        return interaction

    @pytest.mark.asyncio
    async def test_global_key(self, mock_interaction):
        """Test global rate limit key (no user, no guild)."""

        @rate_limit(
            per_user=False, per_guild=False, interval=timedelta(seconds=1)
        )
        async def test_cmd(interaction):
            return "executed"

        # First call should work
        with patch(
            "core.rate_limit.settings.get_bypass_user_ids", return_value=set()
        ):
            result = await test_cmd(mock_interaction)
            assert result == "executed"

    @pytest.mark.asyncio
    async def test_per_user_key(self, mock_interaction):
        """Test per-user rate limit key."""

        @rate_limit(
            per_user=True, per_guild=False, interval=timedelta(seconds=1)
        )
        async def test_cmd(interaction):
            return "executed"

        with patch(
            "core.rate_limit.settings.get_bypass_user_ids", return_value=set()
        ):
            result = await test_cmd(mock_interaction)
            assert result == "executed"

    @pytest.mark.asyncio
    async def test_per_guild_key(self, mock_interaction):
        """Test per-guild rate limit key."""

        @rate_limit(
            per_user=False, per_guild=True, interval=timedelta(seconds=1)
        )
        async def test_cmd(interaction):
            return "executed"

        with patch(
            "core.rate_limit.settings.get_bypass_user_ids", return_value=set()
        ):
            result = await test_cmd(mock_interaction)
            assert result == "executed"

    @pytest.mark.asyncio
    async def test_per_guild_and_user_key(self, mock_interaction):
        """Test per-guild and per-user rate limit key."""

        @rate_limit(
            per_user=True, per_guild=True, interval=timedelta(seconds=1)
        )
        async def test_cmd(interaction):
            return "executed"

        with patch(
            "core.rate_limit.settings.get_bypass_user_ids", return_value=set()
        ):
            result = await test_cmd(mock_interaction)
            assert result == "executed"

    @pytest.mark.asyncio
    async def test_dm_handling(self, mock_interaction):
        """Test DM handling when guild_id is None."""
        mock_interaction.guild_id = None

        @rate_limit(
            per_user=False, per_guild=True, interval=timedelta(seconds=1)
        )
        async def test_cmd(interaction):
            return "executed"

        with patch(
            "core.rate_limit.settings.get_bypass_user_ids", return_value=set()
        ):
            result = await test_cmd(mock_interaction)
            assert result == "executed"


class TestBypassUsers:
    """Tests for bypass user functionality."""

    @pytest.fixture
    def mock_interaction(self):
        """Create a mock Discord interaction."""
        interaction = Mock()
        interaction.user.id = 12345
        interaction.guild_id = 67890
        interaction.followup = AsyncMock()
        return interaction

    @pytest.mark.asyncio
    async def test_bypass_user_allowed(self, mock_interaction):
        """Test that bypass users can execute command immediately."""

        @rate_limit(
            per_user=False, per_guild=True, interval=timedelta(hours=24)
        )
        async def test_cmd(interaction):
            return "executed"

        # User is in bypass list
        with patch(
            "core.rate_limit.settings.get_bypass_user_ids",
            return_value={12345},
        ):
            # First call
            result1 = await test_cmd(mock_interaction)
            assert result1 == "executed"

            # Immediate second call should also work (bypassing rate limit)
            result2 = await test_cmd(mock_interaction)
            assert result2 == "executed"

    @pytest.mark.asyncio
    async def test_non_bypass_user_rate_limited(self, mock_interaction):
        """Test that non-bypass users are rate limited."""

        @rate_limit(
            per_user=False, per_guild=True, interval=timedelta(seconds=1)
        )
        async def test_cmd(interaction):
            return "executed"

        # User is NOT in bypass list
        with patch(
            "core.rate_limit.settings.get_bypass_user_ids", return_value=set()
        ):
            # First call should work
            result1 = await test_cmd(mock_interaction)
            assert result1 == "executed"

            # Immediate second call should be blocked
            result2 = await test_cmd(mock_interaction)
            assert result2 is None

            # followup.send should have been called with rate limit message
            mock_interaction.followup.send.assert_called_once()
            args = mock_interaction.followup.send.call_args
            assert "restantes" in args[0][0]

    @pytest.mark.asyncio
    async def test_empty_bypass_list(self, mock_interaction):
        """Test that empty bypass list works correctly."""

        @rate_limit(
            per_user=False, per_guild=True, interval=timedelta(seconds=1)
        )
        async def test_cmd(interaction):
            return "executed"

        with patch(
            "core.rate_limit.settings.get_bypass_user_ids", return_value=set()
        ):
            result = await test_cmd(mock_interaction)
            assert result == "executed"


class TestRateLimitingBehavior:
    """Tests for rate limiting behavior."""

    @pytest.fixture
    def mock_interaction(self):
        """Create a mock Discord interaction."""
        interaction = Mock()
        interaction.user.id = 12345
        interaction.guild_id = 67890
        interaction.followup = AsyncMock()
        return interaction

    @pytest.mark.asyncio
    async def test_first_call_allowed(self, mock_interaction):
        """Test that first call is always allowed."""

        @rate_limit(
            per_user=False, per_guild=True, interval=timedelta(hours=1)
        )
        async def test_cmd(interaction):
            return "executed"

        with patch(
            "core.rate_limit.settings.get_bypass_user_ids", return_value=set()
        ):
            result = await test_cmd(mock_interaction)
            assert result == "executed"

    @pytest.mark.asyncio
    async def test_second_immediate_call_blocked(self, mock_interaction):
        """Test that second immediate call is blocked."""

        @rate_limit(
            per_user=False, per_guild=True, interval=timedelta(seconds=1)
        )
        async def test_cmd(interaction):
            return "executed"

        with patch(
            "core.rate_limit.settings.get_bypass_user_ids", return_value=set()
        ):
            # First call
            result1 = await test_cmd(mock_interaction)
            assert result1 == "executed"

            # Second immediate call should be blocked
            result2 = await test_cmd(mock_interaction)
            assert result2 is None

    @pytest.mark.asyncio
    async def test_call_after_interval_allowed(self, mock_interaction):
        """Test that call after interval expires is allowed."""

        @rate_limit(
            per_user=False,
            per_guild=True,
            interval=timedelta(milliseconds=100),
        )
        async def test_cmd(interaction):
            return "executed"

        with patch(
            "core.rate_limit.settings.get_bypass_user_ids", return_value=set()
        ):
            # First call
            result1 = await test_cmd(mock_interaction)
            assert result1 == "executed"

            # Wait for interval to expire
            await asyncio.sleep(0.15)

            # Second call after interval should work
            result2 = await test_cmd(mock_interaction)
            assert result2 == "executed"

    @pytest.mark.asyncio
    async def test_different_guilds_independent_limits(self):
        """Test that different guilds have independent rate limits."""

        @rate_limit(
            per_user=False, per_guild=True, interval=timedelta(hours=1)
        )
        async def test_cmd(interaction):
            return "executed"

        # Create two interactions from different guilds
        interaction1 = Mock()
        interaction1.user.id = 12345
        interaction1.guild_id = 11111
        interaction1.followup = AsyncMock()

        interaction2 = Mock()
        interaction2.user.id = 12345
        interaction2.guild_id = 22222
        interaction2.followup = AsyncMock()

        with patch(
            "core.rate_limit.settings.get_bypass_user_ids", return_value=set()
        ):
            # Call from guild 1
            result1 = await test_cmd(interaction1)
            assert result1 == "executed"

            # Call from guild 2 should also work (different guild)
            result2 = await test_cmd(interaction2)
            assert result2 == "executed"

    @pytest.mark.asyncio
    async def test_different_users_independent_limits(self):
        """
        Test that different users have independent limits when per_user=True.
        """

        @rate_limit(
            per_user=True, per_guild=False, interval=timedelta(hours=1)
        )
        async def test_cmd(interaction):
            return "executed"

        # Create two interactions from different users
        interaction1 = Mock()
        interaction1.user.id = 11111
        interaction1.guild_id = 67890
        interaction1.followup = AsyncMock()

        interaction2 = Mock()
        interaction2.user.id = 22222
        interaction2.guild_id = 67890
        interaction2.followup = AsyncMock()

        with patch(
            "core.rate_limit.settings.get_bypass_user_ids", return_value=set()
        ):
            # Call from user 1
            result1 = await test_cmd(interaction1)
            assert result1 == "executed"

            # Call from user 2 should also work (different user)
            result2 = await test_cmd(interaction2)
            assert result2 == "executed"

    @pytest.mark.asyncio
    async def test_time_formatting_in_message(self, mock_interaction):
        """Test that time formatting is included in rate limit message."""

        @rate_limit(
            per_user=False,
            per_guild=True,
            interval=timedelta(hours=1),
            message="Command rate limited",
        )
        async def test_cmd(interaction):
            return "executed"

        with patch(
            "core.rate_limit.settings.get_bypass_user_ids", return_value=set()
        ):
            # First call
            await test_cmd(mock_interaction)

            # Second call should be blocked with formatted time
            await test_cmd(mock_interaction)

            # Check that followup.send was called with formatted time
            mock_interaction.followup.send.assert_called_once()
            args = mock_interaction.followup.send.call_args
            message = args[0][0]

            # Message should contain "restantes" and time format
            assert "restantes" in message
            assert "Command rate limited" in message
