"""Tests for core.browser module."""

import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from selenium.common.exceptions import WebDriverException

from core.browser import DRIVER_UPDATE_DAYS, _get_driver_path, gen_browser


def test_get_driver_path_no_stored_path(tmp_path):
    """Test getting driver path when no stored path exists."""
    mock_driver_path = str(tmp_path / "geckodriver")

    with patch.dict(os.environ, {"SELENIUM_DRIVER_PATH": ""}, clear=False):
        with patch("core.browser.exists", return_value=False):
            with patch("core.browser.GeckoDriverManager") as mock_manager:
                mock_manager.return_value.install.return_value = (
                    mock_driver_path
                )

                result = _get_driver_path()

                assert result == mock_driver_path
                mock_manager.return_value.install.assert_called_once()


def test_get_driver_path_stored_path_recent(tmp_path):
    """Test using stored driver path when it's recent enough."""
    mock_driver_path = str(tmp_path / "geckodriver")

    # Create a fake driver file
    Path(mock_driver_path).touch()

    # Mock file creation time to be 2 days ago
    two_days_ago = datetime.now() - timedelta(days=2)
    with patch.dict(os.environ, {"SELENIUM_DRIVER_PATH": mock_driver_path}):
        with patch("core.browser.exists", return_value=True):
            with patch(
                "core.browser.getctime",
                return_value=two_days_ago.timestamp(),
            ):
                with patch("core.browser.GeckoDriverManager") as mock_manager:
                    result = _get_driver_path()

                    assert result == mock_driver_path
                    # Should NOT install new driver
                    mock_manager.return_value.install.assert_not_called()


def test_get_driver_path_stored_path_old(tmp_path):
    """Test updating driver when stored path is too old."""
    old_driver_path = str(tmp_path / "old_geckodriver")
    new_driver_path = str(tmp_path / "new_geckodriver")

    # Create fake driver files
    Path(old_driver_path).touch()

    # Mock file creation time to be 10 days ago (> 5 day threshold)
    ten_days_ago = datetime.now() - timedelta(days=10)
    with patch.dict(os.environ, {"SELENIUM_DRIVER_PATH": old_driver_path}):
        with patch("core.browser.exists", return_value=True):
            with patch(
                "core.browser.getctime",
                return_value=ten_days_ago.timestamp(),
            ):
                with patch("core.browser.GeckoDriverManager") as mock_manager:
                    mock_manager.return_value.install.return_value = (
                        new_driver_path
                    )

                    result = _get_driver_path()

                    assert result == new_driver_path
                    # Should install new driver
                    mock_manager.return_value.install.assert_called_once()


def test_gen_browser_success():
    """Test successful browser generation."""
    mock_driver_path = "/fake/path/geckodriver"
    mock_browser = MagicMock()

    with patch("core.browser._get_driver_path", return_value=mock_driver_path):
        with patch("core.browser.Firefox", return_value=mock_browser):
            with patch("core.browser.which", return_value="/usr/bin/firefox"):
                result = gen_browser()

                assert result == mock_browser
                # Verify timeouts were set
                mock_browser.set_page_load_timeout.assert_called_once_with(120)
                mock_browser.set_script_timeout.assert_called_once_with(120)


def test_gen_browser_failure():
    """Test browser generation failure."""
    mock_driver_path = "/fake/path/geckodriver"

    with patch("core.browser._get_driver_path", return_value=mock_driver_path):
        with patch(
            "core.browser.Firefox",
            side_effect=WebDriverException("Browser failed"),
        ):
            with patch("core.browser.which", return_value="/usr/bin/firefox"):
                with pytest.raises(WebDriverException):
                    gen_browser()


def test_gen_browser_sets_headless_options():
    """Test that browser is configured with headless options."""
    mock_driver_path = "/fake/path/geckodriver"
    mock_browser = MagicMock()

    with patch("core.browser._get_driver_path", return_value=mock_driver_path):
        with patch(
            "core.browser.Firefox", return_value=mock_browser
        ) as mock_firefox:
            with patch("core.browser.which", return_value="/usr/bin/firefox"):
                gen_browser()

                # Verify Firefox was called with options
                assert mock_firefox.called
                call_kwargs = mock_firefox.call_args[1]
                opts = call_kwargs["options"]

                # Verify headless mode is enabled
                assert opts.headless is True


def test_driver_update_days_constant():
    """Test that DRIVER_UPDATE_DAYS constant is set correctly."""
    assert DRIVER_UPDATE_DAYS == 5
