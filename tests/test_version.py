"""Tests for version listing and management."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from sapo.cli.platform import Platform
from sapo.cli.version import (
    display_versions_table,
    get_available_versions,
    get_package_info,
    parse_version_from_html,
)


def test_parse_version_from_html():
    """Test parsing version from HTML."""
    # Valid version
    assert parse_version_from_html('<a href="7.98.17/">7.98.17/</a>') == "7.98.17"

    # Invalid versions
    assert parse_version_from_html('<a href="../">../</a>') is None
    assert parse_version_from_html('<a href="alpha/">alpha/</a>') is None
    assert parse_version_from_html("not a link") is None


def test_get_package_info_success():
    """Test getting package info with successful response."""
    mock_response = requests.Response()
    mock_response.status_code = 200
    mock_response.headers = {
        "content-length": "1024",
        "last-modified": "Wed, 01 Jan 2024 00:00:00 GMT",
    }

    with patch("requests.head", return_value=mock_response):
        size, timestamp, status = get_package_info("http://example.com/package")

        assert size == "1.00 KB"
        assert timestamp == "2024-01-01 00:00:00"
        assert status == "[green]Available[/]"


def test_get_package_info_not_found():
    """Test getting package info with 404 response."""
    mock_response = requests.Response()
    mock_response.status_code = 404

    with patch("requests.head", return_value=mock_response):
        size, timestamp, status = get_package_info("http://example.com/package")

        assert size == "N/A"
        assert timestamp == "N/A"
        assert status == "[red]Not Available (404)[/]"


def test_get_package_info_error():
    """Test getting package info with request error."""
    with patch("requests.head", side_effect=requests.RequestException("Network error")):
        size, timestamp, status = get_package_info("http://example.com/package")

        assert size == "N/A"
        assert timestamp == "N/A"
        assert status == "[red]Error: Network error[/]"


def test_get_available_versions():
    """Test getting available versions."""
    mock_response = MagicMock()
    mock_response.text = """
        <html>
        <body>
        <a href="7.98.17/">7.98.17/</a>
        <a href="7.98.16/">7.98.16/</a>
        <a href="7.98.15/">7.98.15/</a>
        <a href="../">../</a>
        <a href="alpha/">alpha/</a>
        </body>
        </html>
    """

    with patch("requests.get", return_value=mock_response):
        versions = get_available_versions("http://example.com")

        assert len(versions) == 3
        # Versions should be in descending order (latest first)
        assert versions == ["7.98.17", "7.98.16", "7.98.15"]


def test_get_available_versions_error():
    """Test getting available versions with error."""
    with patch("requests.get", side_effect=requests.RequestException("Network error")):
        with pytest.raises(requests.RequestException):
            get_available_versions("http://example.com")


def test_display_versions_table():
    """Test displaying versions table."""
    versions = ["7.98.17", "7.98.16", "7.98.15"]
    base_url = "http://example.com"
    platform = Platform.DARWIN
    package_pattern = "jfrog-artifactory-oss-{version}-darwin.tar.gz"

    # Mock get_package_info to return consistent results
    def mock_get_package_info(url):
        return "1.00 KB", "2024-01-01 00:00:00", "[green]Available[/]"

    with patch("sapo.cli.version.get_package_info", side_effect=mock_get_package_info):
        # This test mainly verifies that the function doesn't raise any exceptions
        display_versions_table(base_url, versions, platform, package_pattern)
