"""Tests for download utilities."""

import os
from unittest.mock import MagicMock, patch

import requests
from sapo.cli.download import download_file, ProgressTracker


def test_progress_tracker():
    """Test progress tracking functionality."""
    with ProgressTracker("Test", 100) as tracker:
        tracker.update(50)
        assert tracker.progress.tasks[0].completed == 50


def test_progress_tracker_zero_total():
    """Test progress tracking with zero total."""
    with ProgressTracker("Test", 0) as tracker:
        tracker.update(0)
        assert tracker.progress.tasks[0].completed == 0


@patch("requests.get")
def test_download_file_success(mock_get, tmp_path):
    """Test successful file download."""
    # Mock response
    mock_response = MagicMock()
    mock_response.headers = {"content-length": "1000"}
    mock_response.iter_content.return_value = [b"x" * 1000]
    mock_get.return_value.__enter__.return_value = mock_response

    # Test download
    dest_path = tmp_path / "test.txt"
    assert download_file("http://example.com/test.txt", dest_path)
    assert dest_path.exists()
    assert dest_path.stat().st_size == 1000


@patch("requests.get")
def test_download_file_no_content_length(mock_get, tmp_path):
    """Test download without content length header."""
    # Mock response
    mock_response = MagicMock()
    mock_response.headers = {}
    mock_response.iter_content.return_value = [b"x" * 1000]
    mock_get.return_value.__enter__.return_value = mock_response

    # Test download
    dest_path = tmp_path / "test.txt"
    assert download_file("http://example.com/test.txt", dest_path)
    assert dest_path.exists()


@patch("requests.get")
def test_download_file_network_error(mock_get, tmp_path):
    """Test download with network error."""
    mock_get.side_effect = requests.ConnectionError()

    dest_path = tmp_path / "test.txt"
    assert not download_file("http://example.com/test.txt", dest_path)
    assert not dest_path.exists()


@patch("requests.get")
def test_download_file_timeout(mock_get, tmp_path):
    """Test download timeout."""
    mock_get.side_effect = requests.Timeout()

    dest_path = tmp_path / "test.txt"
    assert not download_file("http://example.com/test.txt", dest_path)
    assert not dest_path.exists()


@patch("requests.get")
def test_download_file_ssl_error(mock_get, tmp_path):
    """Test download with SSL error."""
    mock_get.side_effect = requests.exceptions.SSLError()

    dest_path = tmp_path / "test.txt"
    assert not download_file("http://example.com/test.txt", dest_path)
    assert not dest_path.exists()


def test_download_file_dest_permission_error(tmp_path):
    """Test download with destination permission error."""
    # Create a read-only directory
    dest_dir = tmp_path / "readonly"
    dest_dir.mkdir()
    os.chmod(dest_dir, 0o444)  # Read-only

    dest_path = dest_dir / "test.txt"
    assert not download_file("http://example.com/test.txt", dest_path)

    # Change permissions to check existence
    os.chmod(dest_dir, 0o755)
    try:
        assert not dest_path.exists()
    finally:
        os.chmod(dest_dir, 0o444)  # Set back to read-only
