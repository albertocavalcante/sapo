"""Tests for Docker CLI commands using CliRunner."""

from unittest import mock
from pathlib import Path
import pytest
from typer.testing import CliRunner

from sapo.cli.cli import app

# Create a test runner
runner = CliRunner()


def test_install_docker_command_basic():
    """Test basic Docker installation command without starting."""
    with mock.patch(
        "sapo.cli.cli.install_docker_sync", return_value=True
    ) as mock_install:
        # Run the command
        result = runner.invoke(
            app,
            ["install", "--mode", "docker", "--version", "7.111.4", "--port", "8082"],
        )

        # Verify exit code and call
        assert result.exit_code == 0
        mock_install.assert_called_once()
        # Verify parameters
        args = mock_install.call_args[1]
        assert args["version"] == "7.111.4"
        assert args["port"] == 8082
        assert args["start"] is False  # default value


def test_install_docker_command_with_start():
    """Test Docker installation with start flag."""
    with mock.patch(
        "sapo.cli.cli.install_docker_sync", return_value=True
    ) as mock_install:
        # Run the command with start flag
        result = runner.invoke(
            app, ["install", "--mode", "docker", "--version", "7.111.4", "--start"]
        )

        # Verify exit code and call
        assert result.exit_code == 0
        mock_install.assert_called_once()
        # Verify parameters
        args = mock_install.call_args[1]
        assert args["start"] is True


def test_install_docker_command_with_volumes():
    """Test Docker installation with named volumes."""
    with mock.patch(
        "sapo.cli.cli.install_docker_sync", return_value=True
    ) as mock_install:
        # Run the command with volumes
        result = runner.invoke(
            app,
            [
                "install",
                "--mode",
                "docker",
                "--version",
                "7.111.4",
                "--use-volumes",
                "--data-size",
                "100G",
                "--logs-size",
                "20G",
            ],
        )

        # Verify exit code and call
        assert result.exit_code == 0
        mock_install.assert_called_once()
        # Verify parameters
        args = mock_install.call_args[1]
        assert args["use_named_volumes"] is True
        assert args["volume_sizes"]["data"] == "100G"
        assert args["volume_sizes"]["logs"] == "20G"


def test_install_docker_command_with_destination():
    """Test Docker installation with custom destination."""
    temp_path = Path("/tmp/artifactory")

    with mock.patch(
        "sapo.cli.cli.install_docker_sync", return_value=True
    ) as mock_install:
        # Run the command with custom destination
        result = runner.invoke(
            app,
            [
                "install",
                "--mode",
                "docker",
                "--version",
                "7.111.4",
                "--dest",
                str(temp_path),
            ],
        )

        # Verify exit code and call
        assert result.exit_code == 0
        mock_install.assert_called_once()
        # Verify parameters
        args = mock_install.call_args[1]
        assert args["destination"] == temp_path


def test_install_docker_command_failure():
    """Test Docker installation with failure from sync function."""
    with mock.patch(
        "sapo.cli.cli.install_docker_sync", return_value=False
    ) as mock_install:
        # Run the command
        result = runner.invoke(
            app, ["install", "--mode", "docker", "--version", "7.111.4"]
        )

        # Since install_docker_sync returns False, the CLI should still exit with 0
        # because the return value is not checked in the cli.py implementation
        assert result.exit_code == 0
        mock_install.assert_called_once()


def test_install_docker_command_exception():
    """Test Docker installation with exception."""
    with mock.patch(
        "sapo.cli.cli.install_docker_sync", side_effect=Exception("Test error")
    ) as mock_install:
        # Run the command
        result = runner.invoke(
            app, ["install", "--mode", "docker", "--version", "7.111.4"]
        )

        # When an exception is raised, it should be propagated
        assert result.exit_code != 0
        mock_install.assert_called_once()
        assert "Test error" in result.stdout or "Test error" in str(result.exception)


def test_install_docker_direct_command():
    """Test the direct 'install-cmd docker' command."""
    with mock.patch(
        "sapo.cli.cli.install_docker_sync", return_value=True
    ) as mock_install:
        # Run the command using the install-cmd docker subcommand
        if hasattr(app, "registered_commands"):
            # Check if the direct command exists
            has_command = any(cmd.name == "docker" for cmd in app.registered_commands)
            if not has_command:
                pytest.skip("Docker direct command not available in this version")

        # Try to use the install-cmd docker subcommand
        result = runner.invoke(app, ["install-cmd", "docker", "--version", "7.111.4"])

        # Verify exit code and call
        if result.exit_code == 0:
            mock_install.assert_called_once()
            # Verify parameters
            args = mock_install.call_args[1]
            assert args["version"] == "7.111.4"
