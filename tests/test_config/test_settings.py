"""Tests for config.settings module."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from config import settings


def test_env_path_points_to_root():
    """Test that env_path points to project root."""
    assert settings.env_path.name == ".env"
    # env_path should be in parent of config directory
    assert settings.env_path.parent.name != "config"


def test_get_with_default():
    """Test get() returns default when key not found."""
    with patch.dict("os.environ", {}, clear=True):
        result = settings.get("NONEXISTENT_KEY", "default_value")
        assert result == "default_value"


def test_get_required_raises_when_missing():
    """Test get_required() raises ValueError when key missing."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="Required environment variable"):
            settings.get_required("NONEXISTENT_KEY")


def test_get_required_returns_value():
    """Test get_required() returns value when key exists."""
    with patch.dict("os.environ", {"TEST_KEY": "test_value"}):
        result = settings.get_required("TEST_KEY")
        assert result == "test_value"


def test_exists_returns_false_when_no_env():
    """Test exists() returns False when .env doesn't exist."""
    with patch.object(settings, "env_path", Path("/nonexistent/.env")):
        assert settings.exists() is False


def test_exists_returns_true_when_env_exists():
    """Test exists() returns True when .env exists."""
    with tempfile.NamedTemporaryFile(suffix=".env") as tmp:
        with patch.object(settings, "env_path", Path(tmp.name)):
            assert settings.exists() is True


def test_get_bypass_user_ids_with_valid_ids():
    """Test get_bypass_user_ids() with valid comma-separated IDs."""
    with patch.dict("os.environ", {"BYPASS_USER_IDS": "123,456,789"}):
        result = settings.get_bypass_user_ids()
        assert result == {123, 456, 789}


def test_get_bypass_user_ids_with_empty_string():
    """Test get_bypass_user_ids() with empty string returns empty set."""
    with patch.dict("os.environ", {"BYPASS_USER_IDS": ""}):
        result = settings.get_bypass_user_ids()
        assert result == set()


def test_get_bypass_user_ids_with_whitespace():
    """Test get_bypass_user_ids() with whitespace-only string."""
    with patch.dict("os.environ", {"BYPASS_USER_IDS": "   "}):
        result = settings.get_bypass_user_ids()
        assert result == set()


def test_get_bypass_user_ids_not_set():
    """Test get_bypass_user_ids() when env var not set."""
    with patch.dict("os.environ", {}, clear=True):
        result = settings.get_bypass_user_ids()
        assert result == set()


def test_get_bypass_user_ids_with_spaces():
    """Test get_bypass_user_ids() handles spaces around IDs."""
    with patch.dict("os.environ", {"BYPASS_USER_IDS": " 123 , 456 , 789 "}):
        result = settings.get_bypass_user_ids()
        assert result == {123, 456, 789}


def test_get_bypass_user_ids_with_invalid_format():
    """Test get_bypass_user_ids() with invalid format returns empty set."""
    with patch.dict("os.environ", {"BYPASS_USER_IDS": "123,abc,789"}):
        result = settings.get_bypass_user_ids()
        assert result == set()


def test_get_bypass_user_ids_with_single_id():
    """Test get_bypass_user_ids() with single ID."""
    with patch.dict("os.environ", {"BYPASS_USER_IDS": "123456789"}):
        result = settings.get_bypass_user_ids()
        assert result == {123456789}
