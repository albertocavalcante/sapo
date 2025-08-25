"""Tests for Docker container management."""

import subprocess
import tempfile
from pathlib import Path
from unittest import mock

import pytest
from rich.console import Console

from sapo.cli.install_mode.docker.container import (
    ContainerStatus,
    DockerContainerManager,
)


@pytest.fixture
def temp_compose_dir():
    """Create a temporary directory for testing compose files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        compose_dir = Path(tmpdir)
        (compose_dir / "docker-compose.yml").write_text("version: '3'\nservices: {}")
        yield compose_dir


@pytest.fixture
def mock_console():
    """Create a mock console for testing."""
    console = mock.MagicMock(spec=Console)
    console.print = mock.MagicMock()
    return console


class TestDockerContainerManager:
    """Tests for DockerContainerManager."""

    def test_initialization(self, temp_compose_dir, mock_console):
        """Test initialization of the container manager."""
        manager = DockerContainerManager(temp_compose_dir, mock_console)

        assert manager.compose_dir == temp_compose_dir
        assert manager.console == mock_console

    @mock.patch("sapo.cli.install_mode.docker.container.run_docker_command")
    def test_is_docker_available(self, mock_run, temp_compose_dir, mock_console):
        """Test checking if Docker is available."""
        # Setup mock
        mock_run.return_value = subprocess.CompletedProcess(
            args=["docker", "--version"],
            returncode=0,
            stdout="Docker version 20.10.23",
            stderr="",
        )

        # Create manager
        manager = DockerContainerManager(temp_compose_dir, mock_console)

        # Check if Docker is available
        result = manager.is_docker_available()

        # Verify result
        assert result is True
        mock_run.assert_called_once_with(
            ["docker", "--version"], check=True, capture_output=True
        )

        # Now test when Docker is not available
        mock_run.side_effect = subprocess.SubprocessError("Command failed")
        result = manager.is_docker_available()
        assert result is False

        # Verify console message
        mock_console.print.assert_called_with(
            "[bold red]Error:[/] Docker not found. Please install Docker and try again."
        )

    @mock.patch("sapo.cli.install_mode.docker.container.run_docker_command")
    def test_clean_environment(self, mock_run, temp_compose_dir, mock_console):
        """Test cleaning up Docker environment."""
        # Setup mocks
        mock_run.return_value = subprocess.CompletedProcess(
            args=["docker", "compose", "down"], returncode=0, stdout="", stderr=""
        )

        # Create manager
        manager = DockerContainerManager(temp_compose_dir, mock_console)

        # Clean environment
        result = manager.clean_environment()

        # Verify result
        assert result is True
        assert mock_run.call_count >= 3  # compose down + rm commands (network optional)

        # Check docker compose down was called - just check the command structure
        docker_compose_call = mock_run.call_args_list[0]
        called_cmd = docker_compose_call[0][0]  # First positional argument
        assert called_cmd[0] == "docker"
        assert called_cmd[1] == "compose"
        assert called_cmd[2] == "down"
        assert "--volumes" in called_cmd
        assert "--remove-orphans" in called_cmd
        assert docker_compose_call[1]["cwd"] == temp_compose_dir

        # Verify console message
        mock_console.print.assert_any_call(
            "[green]Successfully cleaned up Docker Compose environment.[/]"
        )
        mock_console.print.assert_any_call(
            "[green]Cleaned up artifactory containers.[/]"
        )

    @mock.patch("shutil.which", return_value="/usr/bin/docker")
    @mock.patch("sapo.cli.install_mode.docker.container.subprocess.run")
    def test_clean_environment_with_errors(
        self, mock_run, mock_which, temp_compose_dir, mock_console
    ):
        """Test cleaning up Docker environment with errors."""
        # Setup mocks for compose failure
        mock_run.side_effect = [
            # docker compose down fails
            subprocess.CompletedProcess(
                args=["docker", "compose", "down"],
                returncode=1,
                stdout="",
                stderr="Error",
            ),
            # rm commands succeed
            subprocess.CompletedProcess(
                args=["docker", "rm", "-f", "artifactory"],
                returncode=0,
                stdout="",
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=["docker", "rm", "-f", "artifactory-postgres"],
                returncode=0,
                stdout="",
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=["docker", "network", "rm", "artifactory_network"],
                returncode=0,
                stdout="",
                stderr="",
            ),
        ]

        # Create manager
        manager = DockerContainerManager(temp_compose_dir, mock_console)

        # Clean environment with debug
        result = manager.clean_environment(debug=True)

        # Verify result
        assert result is True  # Still succeeds because direct rm commands work

        # Verify warning was printed
        mock_console.print.assert_any_call(
            "[yellow]Docker Compose cleanup warning: Error[/]"
        )

    @pytest.mark.asyncio
    @mock.patch("shutil.which", return_value="/usr/bin/docker")
    @mock.patch("sapo.cli.install_mode.docker.container.subprocess.run")
    @mock.patch("sapo.cli.install_mode.docker.container.subprocess.Popen")
    @mock.patch(
        "sapo.cli.install_mode.docker.container.DockerContainerManager.is_docker_available"
    )
    async def test_start_containers(
        self,
        mock_is_docker,
        mock_popen,
        mock_run,
        mock_which,
        temp_compose_dir,
        mock_console,
    ):
        """Test starting Docker containers."""
        # Setup mocks
        mock_is_docker.return_value = True

        # Mock subprocess.run for port command
        mock_run.return_value = subprocess.CompletedProcess(
            args=["docker", "compose", "port"],
            returncode=0,
            stdout="0.0.0.0:8082\n",
            stderr="",
        )

        # Mock process for docker compose up
        mock_process = mock.MagicMock()
        mock_process.stdout.readline.side_effect = ["Starting containers...", ""]
        mock_process.poll.return_value = 0
        mock_popen.return_value = mock_process

        # Create manager
        manager = DockerContainerManager(temp_compose_dir, mock_console)

        # Mock the wait_for_health and print_container_status methods
        manager.wait_for_health = mock.AsyncMock(return_value=True)
        manager.print_container_status = mock.MagicMock()

        # Start containers
        result = await manager.start_containers()

        # Verify result
        assert result is True

        # Check docker compose up was called
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        assert cmd[:3] == ["docker", "compose", "up"]

        # Verify wait_for_health was called
        manager.wait_for_health.assert_called_once()

        # Verify success message
        mock_console.print.assert_any_call(
            f"[bold blue]Starting Artifactory with Docker Compose in {temp_compose_dir}...[/]"
        )

    @pytest.mark.asyncio
    @mock.patch("shutil.which", return_value="/usr/bin/docker")
    @mock.patch("sapo.cli.install_mode.docker.container.subprocess.run")
    @mock.patch("sapo.cli.install_mode.docker.container.subprocess.Popen")
    @mock.patch(
        "sapo.cli.install_mode.docker.container.DockerContainerManager.is_docker_available"
    )
    async def test_start_containers_failure(
        self,
        mock_is_docker,
        mock_popen,
        mock_run,
        mock_which,
        temp_compose_dir,
        mock_console,
    ):
        """Test starting Docker containers with failure."""
        # Setup mocks
        mock_is_docker.return_value = True

        # Even on failure path we patch run to avoid unexpected calls
        mock_run.return_value = subprocess.CompletedProcess(
            args=["docker"], returncode=0, stdout="", stderr=""
        )

        # Mock process for docker compose up with failure
        mock_process = mock.MagicMock()
        mock_process.stdout.readline.side_effect = ["Error: failed to start", ""]
        mock_process.poll.return_value = 1
        mock_popen.return_value = mock_process

        # Create manager
        manager = DockerContainerManager(temp_compose_dir, mock_console)

        # Start containers
        result = await manager.start_containers(debug=True)

        # Verify result
        assert result is False

        # Verify failure message
        mock_console.print.assert_any_call(
            "[bold red]Docker Compose failed with exit code 1[/]"
        )
        mock_console.print.assert_any_call("[red]Error: failed to start[/]")

    @mock.patch("shutil.which", return_value="/usr/bin/docker")
    @mock.patch("sapo.cli.install_mode.docker.container.subprocess.run")
    def test_get_container_status(
        self, mock_run, mock_which, temp_compose_dir, mock_console
    ):
        """Test getting container status."""
        # Setup mocks for different status cases
        mock_run.side_effect = [
            # Running case
            subprocess.CompletedProcess(
                args=["docker", "inspect"],
                returncode=0,
                stdout='[{"State": {"Status": "running", "Health": {"Status": "healthy"}}}]',
                stderr="",
            ),
            # Stopped case
            subprocess.CompletedProcess(
                args=["docker", "inspect"],
                returncode=0,
                stdout='[{"State": {"Status": "exited"}}]',
                stderr="",
            ),
            # Unhealthy case
            subprocess.CompletedProcess(
                args=["docker", "inspect"],
                returncode=0,
                stdout='[{"State": {"Status": "running", "Health": {"Status": "unhealthy"}}}]',
                stderr="",
            ),
            # Not found case
            subprocess.CalledProcessError(
                returncode=1,
                cmd=["docker", "inspect"],
                output="",
                stderr="Error: No such container",
            ),
        ]

        # Create manager
        manager = DockerContainerManager(temp_compose_dir, mock_console)

        # Test all status types
        assert manager.get_container_status("container1") == ContainerStatus.HEALTHY
        assert manager.get_container_status("container2") == ContainerStatus.STOPPED
        assert manager.get_container_status("container3") == ContainerStatus.UNHEALTHY
        assert manager.get_container_status("container4") == ContainerStatus.UNKNOWN

    @pytest.mark.asyncio
    @mock.patch("sapo.cli.install_mode.docker.container.asyncio.sleep")
    async def test_wait_for_health(self, mock_sleep, temp_compose_dir, mock_console):
        """Test waiting for container health."""
        # Create manager with a mocked get_container_status
        manager = DockerContainerManager(temp_compose_dir, mock_console)

        # Create a sequence of statuses to return
        status_sequence = [
            (ContainerStatus.UNKNOWN, ContainerStatus.UNKNOWN),  # Initial status
            (ContainerStatus.RUNNING, ContainerStatus.RUNNING),  # First check
            (ContainerStatus.RUNNING, ContainerStatus.RUNNING),  # Second check
            (ContainerStatus.HEALTHY, ContainerStatus.RUNNING),  # Third check
        ]

        # Mock the get_container_status method
        original_get_status = manager.get_container_status

        status_iter = iter(status_sequence)

        def mock_get_status(container_name):
            try:
                current_statuses = next(status_iter)
                return current_statuses[0 if container_name == "artifactory" else 1]
            except StopIteration:
                # After we run out of sequence items, return HEALTHY
                return ContainerStatus.HEALTHY

        # Apply the mock
        manager.get_container_status = mock_get_status

        try:
            # Wait for health
            result = await manager.wait_for_health(interval=1)

            # Verify result
            assert result is True

            # Verify sleep was called at least 3 times (minimum attempts)
            assert mock_sleep.call_count >= 3

            # Restore original method
            manager.get_container_status = original_get_status
        finally:
            # Ensure we restore the original method even if test fails
            manager.get_container_status = original_get_status
