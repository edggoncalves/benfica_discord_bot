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
