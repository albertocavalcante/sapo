"""Docker container management for Artifactory."""

import subprocess
import asyncio
from pathlib import Path
from typing import Optional
from enum import Enum

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner


class ContainerStatus(str, Enum):
    """Container status types."""

    RUNNING = "running"
    STOPPED = "stopped"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class DockerContainerManager:
    """Manages Docker containers for Artifactory."""

    def __init__(self, compose_dir: Path, console: Optional[Console] = None):
        self.compose_dir = compose_dir
        self.console = console or Console()

    def is_docker_available(self) -> bool:
        """Check if Docker is available on the system.

        Returns:
            bool: True if Docker is available
        """
        try:
            subprocess.run(
                ["docker", "--version"], check=True, capture_output=True, text=True
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            self.console.print(
                "[bold red]Error:[/] Docker not found. Please install Docker and try again."
            )
            return False

    def clean_environment(self, debug: bool = False) -> bool:
        """Clean up Docker environment by stopping and removing containers.

        Args:
            debug: Whether to show debug output

        Returns:
            bool: True if cleanup was successful
        """
        self.console.print("[yellow]Cleaning up existing Docker environment...[/]")

        # First try with docker compose
        try:
            # Check if docker-compose.yml exists in the given directory
            if not (self.compose_dir / "docker-compose.yml").exists():
                self.console.print(
                    "[yellow]No docker-compose.yml found, skipping compose cleanup.[/]"
                )
            else:
                # Try to stop and remove containers using docker compose
                process = subprocess.run(
                    ["docker", "compose", "down", "--volumes", "--remove-orphans"],
                    cwd=self.compose_dir,
                    capture_output=True,
                    text=True,
                )

                if process.returncode == 0:
                    self.console.print(
                        "[green]Successfully cleaned up Docker Compose environment.[/]"
                    )
                else:
                    if debug:
                        self.console.print(
                            f"[yellow]Docker Compose cleanup warning: {process.stderr}[/]"
                        )
        except Exception as e:
            self.console.print(
                f"[yellow]Warning: Could not clean up with Docker Compose: {e}[/]"
            )

        # Also try to remove containers directly by name as a fallback
        try:
            # Remove artifactory container if it exists
            subprocess.run(
                ["docker", "rm", "-f", "artifactory"], capture_output=True, text=True
            )

            # Remove postgres container if it exists
            subprocess.run(
                ["docker", "rm", "-f", "artifactory-postgres"],
                capture_output=True,
                text=True,
            )

            # Remove the network if it exists
            subprocess.run(
                ["docker", "network", "rm", "artifactory_network"],
                capture_output=True,
                text=True,
            )

            self.console.print("[green]Cleaned up artifactory containers.[/]")
            return True
        except Exception as e:
            if debug:
                self.console.print(f"[yellow]Container cleanup warning: {e}[/]")
            return False

    async def start_containers(self, debug: bool = False) -> bool:
        """Start Docker containers.

        Args:
            debug: Whether to show debug output

        Returns:
            bool: True if containers started successfully
        """
        if not self.is_docker_available():
            return False

        self.console.print(
            f"[bold blue]Starting Artifactory with Docker Compose in {self.compose_dir}...[/]"
        )

        try:
            # Execute docker compose up
            cmd = ["docker", "compose", "up", "-d"]
            process = subprocess.Popen(
                cmd,
                cwd=self.compose_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            # Collect all output for error reporting
            output_lines = []

            # Stream the output
            while True:
                output = process.stdout.readline()
                if output:
                    output_lines.append(output.strip())
                    # Always show critical errors
                    if "error" in output.lower() or "fail" in output.lower():
                        self.console.print(f"[red]{output.strip()}[/]")
                    # Show all output in debug mode
                    elif debug:
                        self.console.print(output.strip())

                if output == "" and process.poll() is not None:
                    break

            return_code = process.poll()

            if return_code != 0:
                self.console.print(
                    f"[bold red]Docker Compose failed with exit code {return_code}[/]"
                )

                # Display the last few output lines to help diagnose the issue
                if output_lines:
                    self.console.print("[bold red]Docker Compose output:[/]")
                    # Show the last 10 lines or all if less than 10
                    for line in output_lines[-10:]:
                        self.console.print(f"  {line}")

                    self.console.print(
                        "\n[bold]To see full Docker Compose output, run manually:[/]"
                    )
                    self.console.print(f"  cd {self.compose_dir} && docker compose up")

                return False

            # Wait for Artifactory to be ready
            self.console.print("[bold yellow]Waiting for Artifactory to start...[/]")

            with Live(
                Panel(
                    Spinner("dots", text="Starting Artifactory services..."),
                    title="Deployment Status",
                ),
                refresh_per_second=4,
            ) as live:
                # Wait for services to be ready
                attempts = 0
                max_attempts = 60  # 5 minutes (5s * 60)

                while attempts < max_attempts:
                    try:
                        # Check if Artifactory container is running and healthy
                        status = subprocess.run(
                            ["docker", "compose", "ps", "-q", "artifactory"],
                            cwd=self.compose_dir,
                            capture_output=True,
                            text=True,
                            check=True,
                        )

                        if status.stdout.strip():
                            health = subprocess.run(
                                [
                                    "docker",
                                    "inspect",
                                    "--format",
                                    "{{.State.Health.Status}}",
                                    status.stdout.strip(),
                                ],
                                capture_output=True,
                                text=True,
                            )

                            if health.stdout.strip() == "healthy":
                                live.update(
                                    Panel(
                                        "[bold green]Artifactory is now running![/]",
                                        title="Deployment Status",
                                    )
                                )
                                break

                        # Update status message
                        attempts += 1
                        message = f"Starting Artifactory services... ({attempts}/{max_attempts})"
                        live.update(
                            Panel(
                                Spinner("dots", text=message), title="Deployment Status"
                            )
                        )

                        # Wait before next check
                        await asyncio.sleep(5)

                    except subprocess.SubprocessError as e:
                        if debug:
                            self.console.print(
                                f"[red]Error checking service status: {e}[/]"
                            )
                        live.update(
                            Panel(
                                f"[bold red]Error checking service status: {e}[/]",
                                title="Deployment Status",
                            )
                        )
                        return False

                if attempts >= max_attempts:
                    live.update(
                        Panel(
                            "[bold red]Timeout waiting for Artifactory to start[/]",
                            title="Deployment Status",
                        )
                    )
                    return False

            # Get the port number
            try:
                port_cmd = ["docker", "compose", "port", "artifactory", "8082"]
                port_result = subprocess.run(
                    port_cmd,
                    cwd=self.compose_dir,
                    capture_output=True,
                    text=True,
                    check=True,
                )

                # Extract port from output like "0.0.0.0:8082"
                port = port_result.stdout.strip().split(":")[-1]
                self.console.print(
                    f"[bold green]Artifactory is now running![/] Access at http://localhost:{port}"
                )

            except subprocess.SubprocessError:
                self.console.print(
                    "[bold green]Artifactory is now running![/] Access using the configured port."
                )

            return True

        except subprocess.SubprocessError as e:
            self.console.print(f"[bold red]Error:[/] Failed to run Docker Compose: {e}")
            return False

    def get_container_status(self, container_name: str) -> ContainerStatus:
        """Get the status of a container.

        Args:
            container_name: Name of the container

        Returns:
            ContainerStatus: Status of the container
        """
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Status}}", container_name],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return ContainerStatus.UNKNOWN

            status = result.stdout.strip()

            if status == "running":
                # Check health status for running containers
                health = subprocess.run(
                    [
                        "docker",
                        "inspect",
                        "--format",
                        "{{.State.Health.Status}}",
                        container_name,
                    ],
                    capture_output=True,
                    text=True,
                )

                if health.returncode == 0 and health.stdout.strip() == "unhealthy":
                    return ContainerStatus.UNHEALTHY

                return ContainerStatus.RUNNING
            elif status == "exited":
                return ContainerStatus.STOPPED
            else:
                return ContainerStatus.UNKNOWN

        except Exception:
            return ContainerStatus.UNKNOWN
