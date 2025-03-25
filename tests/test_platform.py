"""Tests for platform detection and configuration."""

from unittest.mock import patch

import pytest

from sapo.cli.platform import Platform, get_current_platform


def test_platform_enum():
    """Test Platform enum values."""
    assert Platform.DARWIN.value == "darwin"
    assert Platform.LINUX.value == "linux"
    assert Platform.WINDOWS.value == "windows"


@pytest.mark.parametrize(
    "system,expected_platform",
    [
        ("darwin", Platform.DARWIN),
        ("linux", Platform.LINUX),
        ("windows", Platform.WINDOWS),
    ],
)
def test_get_current_platform(system, expected_platform):
    """Test platform detection for different operating systems."""
    with patch("platform.system", return_value=system):
        assert get_current_platform() == expected_platform


def test_get_current_platform_unsupported():
    """Test platform detection for unsupported operating system."""
    with patch("platform.system", return_value="unsupported"):
        with pytest.raises(
            ValueError, match="Unsupported operating system: unsupported"
        ):
            get_current_platform()
