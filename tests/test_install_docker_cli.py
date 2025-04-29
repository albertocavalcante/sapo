"""Tests for the Docker installation command using CliRunner."""

from pathlib import Path
from unittest import mock
import pytest
from typer.testing import CliRunner

from sapo.cli.cli import app

# Create a test runner
runner = CliRunner()


@pytest.mark.skipif(
    not hasattr(app, "registered_commands")
    or not any(cmd.name == "docker" for cmd in getattr(app, "registered_commands", [])),
    reason="Docker direct command not available in this version",
)
def test_install_docker_direct_command():
    """Test the 'install-cmd docker' command using CliRunner."""
    # Create a mock for the install_docker_sync function
    with mock.patch(
        "sapo.cli.cli.install_docker_sync", return_value=True
    ) as mock_install:
        # Run the command
        result = runner.invoke(
            app, ["install-cmd", "docker", "--version", "7.111.4", "--port", "8090"]
        )

        # Verify exit code
        assert result.exit_code == 0

        # Verify the function was called with the correct parameters
        mock_install.assert_called_once()
        args = mock_install.call_args[1]
        assert args["version"] == "7.111.4"
        assert args["port"] == 8090


@pytest.mark.skipif(
    not hasattr(app, "registered_commands")
    or not any(cmd.name == "docker" for cmd in getattr(app, "registered_commands", [])),
    reason="Docker direct command not available in this version",
)
def test_install_docker_command_with_named_volumes():
    """Test Docker installation with named volumes using CliRunner."""
    # Create a mock for the install_docker_sync function
    with mock.patch(
        "sapo.cli.cli.install_docker_sync", return_value=True
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

        # Verify exit code
        assert result.exit_code == 0

        # Verify the function was called correctly
        mock_install.assert_called_once()
        args = mock_install.call_args[1]
        assert args["version"] == "7.111.4"
        assert args["use_named_volumes"] is True
        assert args["volume_driver"] == "local"
        assert "volume_sizes" in args
        assert "data" in args["volume_sizes"]
        assert args["volume_sizes"]["data"] == "100G"
        assert "logs" in args["volume_sizes"]
        assert args["volume_sizes"]["logs"] == "20G"


@pytest.mark.skipif(
    not hasattr(app, "registered_commands")
    or not any(cmd.name == "docker" for cmd in getattr(app, "registered_commands", [])),
    reason="Docker direct command not available in this version",
)
def test_install_docker_command_with_host_paths():
    """Test Docker installation with host paths using CliRunner."""
    # Create a temporary path
    temp_path = Path("/tmp/artifactory/data")

    # Create a mock for the install_docker_sync function
    with mock.patch(
        "sapo.cli.cli.install_docker_sync", return_value=True
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

        # Verify exit code
        assert result.exit_code == 0

        # Verify the function was called correctly
        mock_install.assert_called_once()
        args = mock_install.call_args[1]
        assert args["version"] == "7.111.4"
        assert "host_paths" in args
        assert "data" in args["host_paths"]
        assert args["host_paths"]["data"] == temp_path


@pytest.mark.skipif(
    not hasattr(app, "registered_commands")
    or not any(cmd.name == "docker" for cmd in getattr(app, "registered_commands", [])),
    reason="Docker direct command not available in this version",
)
def test_install_docker_command_non_interactive():
    """Test Docker installation in non-interactive mode using CliRunner."""
    # Create a mock for the install_docker_sync function
    with mock.patch(
        "sapo.cli.cli.install_docker_sync", return_value=True
    ) as mock_install:
        # Run the command in non-interactive mode
        result = runner.invoke(
            app, ["install-cmd", "docker", "--version", "7.111.4", "--non-interactive"]
        )

        # Verify exit code
        assert result.exit_code == 0

        # Verify the function was called correctly
        mock_install.assert_called_once()
        args = mock_install.call_args[1]
        assert args["version"] == "7.111.4"
        assert args["non_interactive"] is True


@pytest.mark.skipif(
    not hasattr(app, "registered_commands")
    or not any(cmd.name == "docker" for cmd in getattr(app, "registered_commands", [])),
    reason="Docker direct command not available in this version",
)
def test_install_docker_command_debug():
    """Test Docker installation with debug mode using CliRunner."""
    # Create a mock for the install_docker_sync function
    with mock.patch(
        "sapo.cli.cli.install_docker_sync", return_value=True
    ) as mock_install:
        # Run the command with debug flag
        result = runner.invoke(
            app, ["install-cmd", "docker", "--version", "7.111.4", "--debug"]
        )

        # Verify exit code
        assert result.exit_code == 0

        # Verify the function was called correctly
        mock_install.assert_called_once()
        args = mock_install.call_args[1]
        assert args["version"] == "7.111.4"
        assert args["debug"] is True


@pytest.mark.skipif(
    not hasattr(app, "registered_commands")
    or not any(cmd.name == "docker" for cmd in getattr(app, "registered_commands", [])),
    reason="Docker direct command not available in this version",
)
def test_install_docker_command_exception_handling():
    """Test exception handling during Docker installation using CliRunner."""
    # Create a mock that raises an exception
    with mock.patch(
        "sapo.cli.cli.install_docker_sync", side_effect=Exception("Test error")
    ) as mock_install:
        # Run the command
        result = runner.invoke(app, ["install-cmd", "docker", "--version", "7.111.4"])

        # Verify the exception was handled
        assert result.exit_code != 0
        assert "Test error" in result.stdout or "Test error" in str(result.exception)

        # Verify the function was called
        mock_install.assert_called_once()
