"""Tests for checksum verification."""

from unittest.mock import patch

import pytest
import requests

from sapo.cli.checksum import calculate_sha256, verify_checksum


@pytest.fixture
def test_file(tmp_path):
    """Create a test file with known content."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("test content")
    return file_path


def test_calculate_sha256(test_file):
    """Test SHA256 calculation."""
    # Known SHA256 hash for "test content"
    expected_hash = "6ae8a75555209fd6c44157c0aed8016e763ff435a19cf186f76863140143ff72"
    assert calculate_sha256(test_file) == expected_hash


def test_verify_checksum_success(test_file):
    """Test successful checksum verification."""
    # Mock the expected checksum response
    with patch("requests.get") as mock_get:
        mock_response = mock_get.return_value
        mock_response.ok = True
        mock_response.text = calculate_sha256(test_file)

        assert verify_checksum(test_file, "http://example.com/checksum.sha256")
        mock_get.assert_called_once_with("http://example.com/checksum.sha256")


def test_verify_checksum_mismatch(test_file):
    """Test checksum verification with mismatch."""
    with patch("requests.get") as mock_get:
        mock_response = mock_get.return_value
        mock_response.ok = True
        mock_response.text = "different_checksum"

        assert not verify_checksum(test_file, "http://example.com/checksum.sha256")
        mock_get.assert_called_once_with("http://example.com/checksum.sha256")


def test_verify_checksum_download_failure(test_file):
    """Test checksum verification with download failure."""
    with patch("requests.get") as mock_get:
        mock_response = mock_get.return_value
        mock_response.ok = False

        assert not verify_checksum(test_file, "http://example.com/checksum.sha256")
        mock_get.assert_called_once_with("http://example.com/checksum.sha256")


def test_verify_checksum_request_error(test_file):
    """Test checksum verification with request error."""
    with patch("requests.get", side_effect=requests.RequestException("Network error")):
        assert not verify_checksum(test_file, "http://example.com/checksum.sha256")
