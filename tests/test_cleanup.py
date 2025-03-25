"""Tests for cleanup and signal handling."""

import signal
from unittest.mock import patch

import pytest

from sapo.cli.cleanup import (
    cleanup,
    register_temp_file,
    setup_signal_handlers,
    signal_handler,
)


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file for testing."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("test")
    return file_path


def test_register_temp_file(temp_file):
    """Test registering a temporary file."""
    register_temp_file(temp_file)
    # Note: We can't directly test the private _temp_files set
    # but we can verify the cleanup function works with it


def test_cleanup_success(temp_file):
    """Test successful cleanup of temporary files."""
    register_temp_file(temp_file)
    cleanup()
    assert not temp_file.exists()


def test_cleanup_failure(temp_file):
    """Test cleanup handling of file deletion failures."""
    register_temp_file(temp_file)

    # Mock os.unlink to raise an exception
    with patch("pathlib.Path.unlink", side_effect=OSError("Permission denied")):
        cleanup()
        # File should still exist
        assert temp_file.exists()


def test_signal_handler():
    """Test signal handler setup and execution."""
    # Mock sys.exit
    with patch("sys.exit") as mock_exit:
        # Mock cleanup
        with patch("sapo.cli.cleanup.cleanup") as mock_cleanup:
            # Call signal handler
            signal_handler(signal.SIGINT, None)

            # Verify cleanup was called
            mock_cleanup.assert_called_once()
            # Verify sys.exit was called with code 1
            mock_exit.assert_called_once_with(1)


def test_setup_signal_handlers():
    """Test setting up signal handlers."""
    with patch("signal.signal") as mock_signal:
        setup_signal_handlers()

        # Verify signal handlers were registered for SIGINT and SIGTERM
        assert mock_signal.call_count == 2
        calls = mock_signal.call_args_list

        # Check SIGINT handler
        assert calls[0][0][0] == signal.SIGINT
        assert calls[0][0][1] == signal_handler

        # Check SIGTERM handler
        assert calls[1][0][0] == signal.SIGTERM
        assert calls[1][0][1] == signal_handler
