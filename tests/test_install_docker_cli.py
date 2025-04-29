"""Tests for the Docker installation command using CliRunner."""

from pathlib import Path
from unittest import mock
import pytest
from typer.testing import CliRunner

from sapo.cli.cli import app

# Create a test runner
runner = CliRunner()


@pytest.mark.asyncio
async def test_install_docker_direct_command():
    """Test the 'install-cmd docker' command using CliRunner."""
    # Create a mock for the async install_docker function
    with mock.patch(
        "sapo.cli.install_mode.docker.install_docker", new=mock.AsyncMock()
    ) as mock_install:
        # Run the command
        result = runner.invoke(
            app, ["install-cmd", "docker", "--version", "7.111.4", "--port", "8090"]
        )

        # Verify the function was called with the correct parameters
        mock_install.assert_called_once()
        args = mock_install.call_args[1]
        assert args["version"] == "7.111.4"
        assert args["port"] == 8090

        # Check exit code
        assert result.exit_code == 0


@pytest.mark.asyncio
async def test_install_docker_command_with_named_volumes():
    """Test Docker installation with named volumes using CliRunner."""
    # Create a mock for the async install_docker function
    with mock.patch(
        "sapo.cli.install_mode.docker.install_docker", new=mock.AsyncMock()
    ) as mock_install:
        # Run the command with volumes
        result = runner.invoke(
            app,
            [
                "install-cmd",
                "docker",
                "--version",
                "7.111.4",
                "--use-volumes",
                "--data-size",
                "100G",
                "--logs-size",
                "20G",
                "--volume-driver",
                "local",
            ],
        )

        # Verify the function was called correctly
        mock_install.assert_called_once()
        args = mock_install.call_args[1]
        assert args["version"] == "7.111.4"
        assert args["use_named_volumes"] is True
        assert args["volume_driver"] == "local"
        assert args["data_size"] == "100G"
        assert args["logs_size"] == "20G"

        # Check exit code
        assert result.exit_code == 0


@pytest.mark.asyncio
async def test_install_docker_command_with_host_paths():
    """Test Docker installation with host paths using CliRunner."""
    # Create a temporary path
    temp_path = Path("/tmp/artifactory/data")

    # Create a mock for the async install_docker function
    with mock.patch(
        "sapo.cli.install_mode.docker.install_docker", new=mock.AsyncMock()
    ) as mock_install:
        # Run the command with host paths
        result = runner.invoke(
            app,
            [
                "install-cmd",
                "docker",
                "--version",
                "7.111.4",
                "--data-path",
                str(temp_path),
            ],
        )

        # Verify the function was called correctly
        mock_install.assert_called_once()
        args = mock_install.call_args[1]
        assert args["version"] == "7.111.4"
        assert args["data_path"] == temp_path

        # Check exit code
        assert result.exit_code == 0


@pytest.mark.asyncio
async def test_install_docker_command_non_interactive():
    """Test Docker installation in non-interactive mode using CliRunner."""
    # Create a mock for the async install_docker function
    with mock.patch(
        "sapo.cli.install_mode.docker.install_docker", new=mock.AsyncMock()
    ) as mock_install:
        # Run the command in non-interactive mode
        result = runner.invoke(
            app, ["install-cmd", "docker", "--version", "7.111.4", "--non-interactive"]
        )

        # Verify the function was called correctly
        mock_install.assert_called_once()
        args = mock_install.call_args[1]
        assert args["version"] == "7.111.4"
        assert args["non_interactive"] is True

        # Check exit code
        assert result.exit_code == 0


@pytest.mark.asyncio
async def test_install_docker_command_debug():
    """Test Docker installation with debug mode using CliRunner."""
    # Create a mock for the async install_docker function
    with mock.patch(
        "sapo.cli.install_mode.docker.install_docker", new=mock.AsyncMock()
    ) as mock_install:
        # Run the command with debug flag
        result = runner.invoke(
            app, ["install-cmd", "docker", "--version", "7.111.4", "--debug"]
        )

        # Verify the function was called correctly
        mock_install.assert_called_once()
        args = mock_install.call_args[1]
        assert args["version"] == "7.111.4"
        assert args["debug"] is True

        # Check exit code
        assert result.exit_code == 0


@pytest.mark.asyncio
async def test_install_docker_command_exception_handling():
    """Test exception handling during Docker installation using CliRunner."""
    # Create a mock that raises an exception
    mock_install = mock.AsyncMock(side_effect=Exception("Test error"))

    # Patch the install_docker function
    with mock.patch("sapo.cli.install_mode.docker.install_docker", new=mock_install):
        # Run the command
        result = runner.invoke(app, ["install-cmd", "docker", "--version", "7.111.4"])

        # Verify the exception was handled
        assert result.exit_code != 0
        assert "Test error" in result.stdout or "Test error" in str(result.exception)

        # Verify the function was called
        mock_install.assert_called_once()
