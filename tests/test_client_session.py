"""Tests for ClientSession creation with proxy support."""

import os
from unittest.mock import patch
from sapo.cli.http import create_client_session


def test_create_client_session_with_trust_env():
    """Test that create_client_session creates a ClientSession with trust_env=True."""
    with patch("sapo.cli.http.aiohttp.ClientSession") as mock_session:
        # Call the function
        create_client_session()

        # Verify trust_env=True was used
        mock_session.assert_called_once_with(trust_env=True)


def test_create_client_session_respects_http_proxy():
    """Test that HTTP_PROXY environment variable is respected."""
    with patch.dict(
        os.environ, {"HTTP_PROXY": "http://proxy.example.com:8080"}, clear=True
    ):
        with patch("sapo.cli.http.aiohttp.ClientSession") as mock_session:
            # Call the function
            create_client_session(debug=True)

            # Verify trust_env=True was used
            mock_session.assert_called_once_with(trust_env=True)


def test_create_client_session_respects_https_proxy():
    """Test that HTTPS_PROXY environment variable is respected."""
    with patch.dict(
        os.environ, {"HTTPS_PROXY": "https://proxy.example.com:8443"}, clear=True
    ):
        with patch("sapo.cli.http.aiohttp.ClientSession") as mock_session:
            # Call the function
            create_client_session(debug=True)

            # Verify trust_env=True was used
            mock_session.assert_called_once_with(trust_env=True)


def test_create_client_session_respects_no_proxy():
    """Test that NO_PROXY environment variable is respected."""
    env = {
        "HTTP_PROXY": "http://proxy.example.com:8080",
        "NO_PROXY": "localhost,127.0.0.1,.example.com",
    }
    with patch.dict(os.environ, env, clear=True):
        with patch("sapo.cli.http.aiohttp.ClientSession") as mock_session:
            # Call the function
            create_client_session(debug=True)

            # Verify trust_env=True was used
            mock_session.assert_called_once_with(trust_env=True)
