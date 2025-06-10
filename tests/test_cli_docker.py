"""Tests for Docker CLI commands using CliRunner."""

from unittest import mock
from pathlib import Path
import pytest
from typer.testing import CliRunner

from sapo.cli.cli import app

# Create a test runner
runner = CliRunner()


def test_install_docker_command_basic():
    """Test basic Docker installation command."""
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
        assert args["start"] is True  # Updated to match new Docker default


def test_install_docker_command_with_start():
    """Test Docker installation with explicit start flag."""
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
                "5G",
            ],
        )

        # Verify exit code and call
        assert result.exit_code == 0
        mock_install.assert_called_once()
        # Verify parameters
        args = mock_install.call_args[1]
        assert args["use_named_volumes"] is True
        assert args["volume_sizes"]["data"] == "100G"
        assert args["volume_sizes"]["logs"] == "5G"


@pytest.mark.parametrize(
    "flag,expected_path",
    [
        ("--destination", Path("/tmp/artifactory")),
        ("--dest", Path("/tmp/artifactory")),
        ("-d", Path("/tmp/artifactory")),
    ],
)
def test_install_docker_destination_aliases(flag, expected_path):
    """Test Docker installation with different destination flag aliases."""
    with mock.patch(
        "sapo.cli.cli.install_docker_sync", return_value=True
    ) as mock_install:
        # Run the command with custom destination using new --destination flag
        result = runner.invoke(
            app,
            [
                "install",
                "--mode",
                "docker",
                "--version",
                "7.111.4",
                flag,
                str(expected_path),
            ],
        )

        # Verify exit code and call
        assert result.exit_code == 0
        mock_install.assert_called_once()
        # Verify parameters
        args = mock_install.call_args[1]
        assert args["destination"] == expected_path


def test_install_docker_command_with_host_paths():
    """Test Docker installation with host paths for volume mounting."""
    data_path = Path("/tmp/artifactory/data")
    logs_path = Path("/tmp/artifactory/logs")
    db_path = Path("/tmp/artifactory/db")

    with mock.patch(
        "sapo.cli.cli.install_docker_sync", return_value=True
    ) as mock_install:
        # Run the command with host paths
        result = runner.invoke(
            app,
            [
                "install",
                "--mode",
                "docker",
                "--version",
                "7.111.4",
                "--use-volumes",
                "--data-path",
                str(data_path),
                "--logs-path",
                str(logs_path),
                "--db-path",
                str(db_path),
            ],
        )

        # Verify exit code and call
        assert result.exit_code == 0
        mock_install.assert_called_once()
        # Verify parameters
        args = mock_install.call_args[1]
        assert args["use_named_volumes"] is True
        assert args["host_paths"]["data"] == data_path
        assert args["host_paths"]["logs"] == logs_path
        assert args["host_paths"]["postgresql"] == db_path


def test_install_docker_command_non_interactive():
    """Test Docker installation in non-interactive mode."""
    with mock.patch(
        "sapo.cli.cli.install_docker_sync", return_value=True
    ) as mock_install:
        # Run the command in non-interactive mode
        result = runner.invoke(
            app,
            [
                "install",
                "--mode",
                "docker",
                "--version",
                "7.111.4",
                "--yes",  # non-interactive flag
                "--port",
                "8090",
            ],
        )

        # Verify exit code and call
        assert result.exit_code == 0
        mock_install.assert_called_once()
        # Verify parameters
        args = mock_install.call_args[1]
        assert args["version"] == "7.111.4"
        assert args["non_interactive"] is True
        assert args["port"] == 8090


def test_install_docker_command_debug_mode():
    """Test Docker installation with debug mode enabled."""
    with mock.patch(
        "sapo.cli.cli.install_docker_sync", return_value=True
    ) as mock_install:
        # Run the command with debug flag
        result = runner.invoke(
            app,
            [
                "install",
                "--mode",
                "docker",
                "--version",
                "7.111.4",
                "--debug",
                "--port",
                "8091",
            ],
        )

        # Verify exit code and call
        assert result.exit_code == 0
        mock_install.assert_called_once()
        # Verify parameters
        args = mock_install.call_args[1]
        assert args["debug"] is True
        assert args["port"] == 8091


def test_install_docker_command_with_volume_driver():
    """Test Docker installation with custom volume driver."""
    with mock.patch(
        "sapo.cli.cli.install_docker_sync", return_value=True
    ) as mock_install:
        # Run the command with custom volume driver
        result = runner.invoke(
            app,
            [
                "install",
                "--mode",
                "docker",
                "--version",
                "7.111.4",
                "--use-volumes",
                "--volume-driver",
                "local",
                "--data-size",
                "100G",
            ],
        )

        # Verify exit code and call
        assert result.exit_code == 0
        mock_install.assert_called_once()
        # Verify parameters
        args = mock_install.call_args[1]
        assert args["use_named_volumes"] is True
        assert args["volume_driver"] == "local"
        assert args["volume_sizes"]["data"] == "100G"


def test_install_docker_command_with_backup_volume():
    """Test Docker installation with backup volume explicitly requested."""
    with mock.patch(
        "sapo.cli.cli.install_docker_sync", return_value=True
    ) as mock_install:
        # Run the command with backup volume
        result = runner.invoke(
            app,
            [
                "install",
                "--mode",
                "docker",
                "--version",
                "7.111.4",
                "--use-volumes",
                "--backup-size",
                "50G",
            ],
        )

        # Verify exit code and call
        assert result.exit_code == 0
        mock_install.assert_called_once()
        # Verify parameters
        args = mock_install.call_args[1]
        assert args["use_named_volumes"] is True
        assert args["volume_sizes"]["backup"] == "50G"


def test_install_docker_command_without_backup_volume():
    """Test Docker installation without backup volume (default behavior)."""
    with mock.patch(
        "sapo.cli.cli.install_docker_sync", return_value=True
    ) as mock_install:
        # Run the command without backup volume
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
                "10G",
            ],
        )

        # Verify exit code and call
        assert result.exit_code == 0
        mock_install.assert_called_once()
        # Verify parameters
        args = mock_install.call_args[1]
        assert args["use_named_volumes"] is True
        assert args["volume_sizes"]["data"] == "10G"
        # Backup should not be in volume_sizes when not requested
        assert "backup" not in args["volume_sizes"]


@pytest.mark.parametrize(
    "data_size,logs_size,db_size",
    [
        ("10G", "3G", "5G"),
        ("200G", "20G", "15G"),
        ("1T", "50G", "30G"),
    ],
)
def test_install_docker_command_volume_sizes(data_size, logs_size, db_size):
    """Test Docker installation with various volume size combinations."""
    with mock.patch(
        "sapo.cli.cli.install_docker_sync", return_value=True
    ) as mock_install:
        # Run the command with all volume sizes
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
                data_size,
                "--logs-size",
                logs_size,
                "--db-size",
                db_size,
            ],
        )

        # Verify exit code and call
        assert result.exit_code == 0
        mock_install.assert_called_once()
        # Verify parameters
        args = mock_install.call_args[1]
        assert args["use_named_volumes"] is True
        assert args["volume_sizes"]["data"] == data_size
        assert args["volume_sizes"]["logs"] == logs_size
        assert args["volume_sizes"]["postgresql"] == db_size


def test_install_docker_command_failure():
    """Test Docker installation failure handling."""
    with mock.patch(
        "sapo.cli.cli.install_docker_sync", return_value=False
    ) as mock_install:
        # Run the command
        result = runner.invoke(
            app, ["install", "--mode", "docker", "--version", "7.111.4"]
        )

        # CLI doesn't check return value, so it exits with 0 even if function returns False
        assert result.exit_code == 0
        mock_install.assert_called_once()


def test_install_docker_command_exception():
    """Test Docker installation exception handling."""
    with mock.patch(
        "sapo.cli.cli.install_docker_sync", side_effect=Exception("Mock error")
    ) as mock_install:
        # Run the command
        result = runner.invoke(
            app, ["install", "--mode", "docker", "--version", "7.111.4"]
        )

        # When an exception is raised, it should be propagated
        assert result.exit_code == 1
        mock_install.assert_called_once()
        assert "Mock error" in result.stdout or "Mock error" in str(result.exception)


def test_install_docker_command_complex_scenario():
    """Test Docker installation with complex configuration."""
    with mock.patch(
        "sapo.cli.cli.install_docker_sync", return_value=True
    ) as mock_install:
        # Run the command with multiple options combined
        result = runner.invoke(
            app,
            [
                "install",
                "--mode",
                "docker",
                "--version",
                "7.111.4",
                "--port",
                "9090",
                "--destination",
                "/custom/path",
                "--use-volumes",
                "--data-size",
                "500G",
                "--logs-size",
                "50G",
                "--db-size",
                "30G",
                "--volume-driver",
                "local",
                "--start",
                "--yes",
                "--debug",
            ],
        )

        # Verify exit code and call
        assert result.exit_code == 0
        mock_install.assert_called_once()
        # Verify parameters
        args = mock_install.call_args[1]
        assert args["version"] == "7.111.4"
        assert args["port"] == 9090
        assert args["destination"] == Path("/custom/path")
        assert args["use_named_volumes"] is True
        assert args["volume_sizes"]["data"] == "500G"
        assert args["volume_sizes"]["logs"] == "50G"
        assert args["volume_sizes"]["postgresql"] == "30G"
        assert args["volume_driver"] == "local"
        assert args["start"] is True
        assert args["non_interactive"] is True
        assert args["debug"] is True
