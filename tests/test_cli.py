"""Tests for the CLI commands."""

from unittest.mock import patch
from typer.testing import CliRunner
from sapo.cli.cli import app
from sapo.cli.artifactory import ArtifactoryConfig


runner = CliRunner()


@patch("sapo.cli.cli.install_artifactory")
def test_install_command(mock_install):
    """Test the install command."""
    result = runner.invoke(app, ["install", "--version", "7.99.0"])
    assert result.exit_code == 0
    mock_install.assert_called_once()
    # Check that the version was passed correctly
    assert mock_install.call_args[1]["version"] == "7.99.0"


@patch("sapo.cli.cli.list_versions")
def test_releases_command(mock_list_versions):
    """Test the releases command."""
    result = runner.invoke(app, ["releases", "--limit", "5"])
    assert result.exit_code == 0
    mock_list_versions.assert_called_once_with(limit=5)


@patch("sapo.cli.cli.show_info")
def test_info_command(mock_show_info):
    """Test the info command."""
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    mock_show_info.assert_called_once()

    # Verify the config passed to show_info
    config_arg = mock_show_info.call_args[0][0]
    assert isinstance(config_arg, ArtifactoryConfig)
    assert config_arg.version == "7.111.9"  # Updated default value


@patch("sapo.cli.cli.asyncio.run")
@patch("sapo.cli.cli.display_release_notes")
def test_release_notes_command(mock_display_notes, mock_asyncio_run):
    """Test the release notes command."""

    # Create a coroutine to return
    async def mock_coro():
        return None

    # Set up the mock to return a real coroutine function
    mock_display_notes.return_value = mock_coro()

    result = runner.invoke(app, ["release-notes", "--version", "7.99.0"])
    assert result.exit_code == 0

    # Verify display_release_notes was called with correct args
    mock_display_notes.assert_called_once_with("7.99.0", False)

    # Verify asyncio.run was called (with any coroutine)
    mock_asyncio_run.assert_called_once()
