"""Docker-based installation mode for Artifactory.

This module handles Docker-based installation of Artifactory,
including pulling images, setting up volumes, and creating containers.
"""

import asyncio
import secrets
import shutil
import string
import subprocess  # nosec B404
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import docker
import typer
from docker.errors import DockerException, ImageNotFound
from pydantic import BaseModel, Field
from rich.console import Console
from rich.progress import Progress

from ..common import Platform, check_docker_installed, run_docker_command
from ..console import SapoConsole
from .common import OperationStatus
from .docker.volume import VolumeManager, VolumeType
from .templates import render_template_from_file
from .docker.container import DockerContainerManager

# Create a default console for module-level logging
console = Console()

# Minimum recommended free space in GB for Artifactory installation
MIN_RECOMMENDED_FREE_SPACE_GB = 20
# Warning threshold percentage
DISK_SPACE_WARNING_THRESHOLD = 15


class DockerConfig(BaseModel):
    """Docker deployment configuration.

    Attributes:
        version: Artifactory version
        port: HTTP port
        data_dir: Data directory
        use_derby: Whether to use Derby instead of PostgreSQL (not recommended)
        postgres_user: PostgreSQL username
        postgres_db: PostgreSQL database name
        output_dir: Output directory for generated files
        joinkey: Security join key for Artifactory
    """

    version: str
    port: int = Field(default=8082)
    data_dir: Path = Field(default=Path.home() / ".jfrog" / "artifactory")
    use_derby: bool = Field(default=False)  # Default to PostgreSQL
    postgres_user: str = Field(default="artifactory")
    postgres_db: str = Field(default="artifactory")
    output_dir: Path = Field(default=Path.home() / ".jfrog" / "artifactory" / "docker")
    joinkey: Optional[str] = Field(default=None)
    _passwords: Dict[str, str] = {}

    def generate_password(self, key: str) -> str:
        """Generate a secure random password and store it.

        Args:
            key: Identifier for the password

        Returns:
            str: The generated password
        """
        if key not in self._passwords:
            # Generate a strong password with mixed characters
            charset = (
                string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>/?"
            )
            # Ensure at least 16 characters for security
            self._passwords[key] = "".join(secrets.choice(charset) for _ in range(20))
        return self._passwords[key]

    def get_password(self, key: str) -> str:
        """Retrieve a previously generated password.

        Args:
            key: Identifier for the password

        Returns:
            str: The stored password
        """
        if key not in self._passwords:
            return self.generate_password(key)
        return self._passwords[key]

    def generate_joinkey(self) -> str:
        """Generate a secure join key for Artifactory.

        Returns:
            str: A secure join key
        """
        if not self.joinkey:
            # Generate a unique join key if not provided
            key = "".join(
                secrets.choice(string.ascii_letters + string.digits) for _ in range(24)
            )
            self.joinkey = key
        return self.joinkey


def safe_write_file(path: Path, content: str, non_interactive: bool = False) -> bool:
    """Safely write content to a file, handling conflicts with user prompts.

    Args:
        path: Path to write to
        content: Content to write
        non_interactive: Whether to skip confirmation prompts

        Returns:
        bool: True if file was written successfully, False otherwise
    """
    # Check for directory/file conflicts
    if path.exists():
        if path.is_dir():
            if non_interactive:
                console.print(
                    f"[bold red]Error:[/] Cannot write to {path} - it's a directory"
                )
                return False

            should_remove = typer.confirm(
                f"A directory exists at {path} but a file is needed. Remove directory?",
                default=False,
            )

            if should_remove:
                try:
                    shutil.rmtree(path)
                    console.print(f"[yellow]Removed directory {path}[/]")
                except Exception as e:
                    console.print(
                        f"[bold red]Error:[/] Failed to remove directory {path}: {e}"
                    )
                    return False
            else:
                console.print("[yellow]Skipping file creation.[/]")
                return False

        elif path.is_file():
            if non_interactive:
                # In non-interactive mode, just overwrite the file
                pass
            else:
                should_overwrite = typer.confirm(
                    f"File {path} already exists. Overwrite?", default=True
                )

                if not should_overwrite:
                    console.print("[yellow]Skipping file creation.[/]")
                    return False

    # Create parent directories if they don't exist
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write the file
    try:
        path.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        console.print(f"[bold red]Error:[/] Failed to write to {path}: {e}")
        return False


def generate_files(config: DockerConfig, non_interactive: bool = False) -> Path:
    """Generate required files for Docker installation.

    Args:
        config: Docker configuration parameters
        non_interactive: Whether to skip confirmation prompts

    Returns:
        Path: Output directory where files were generated

    Raises:
        typer.Exit: If file generation fails and can't continue
    """
    # Create installation directory
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create required directories according to official JFrog documentation
    data_dir = config.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    # Set up the standard Artifactory directory structure
    var_dir = data_dir
    etc_dir = var_dir / "etc"
    etc_dir.mkdir(exist_ok=True)

    # Create other expected directories
    data_path = var_dir / "data"
    data_path.mkdir(exist_ok=True)
    logs_path = var_dir / "logs"
    logs_path.mkdir(exist_ok=True)
    backup_path = var_dir / "backup"
    backup_path.mkdir(exist_ok=True)
    access_path = var_dir / "access"
    access_path.mkdir(exist_ok=True)

    # Create PostgreSQL directory if needed
    if not config.use_derby:
        pg_path = data_dir / "postgresql"
        pg_path.mkdir(exist_ok=True)

    console.print(f"[bold]Generating files in {output_dir}...[/]")

    # Generate joinkey if not provided
    joinkey = config.generate_joinkey()

    # Determine if using PostgreSQL or Derby
    use_postgres = not config.use_derby

    # Generate .env file
    env_content = render_template_from_file(
        "docker",
        "env.j2",
        {
            "artifactory_version": config.version,
            "data_dir": str(config.data_dir.absolute()),
            "external_port": config.port,
            "postgres_user": config.postgres_user,
            "postgres_password": config.generate_password("postgres"),
            "postgres_db": config.postgres_db,
            "use_postgres": use_postgres,
            "joinkey": joinkey,
        },
    )
    if not safe_write_file(output_dir / ".env", env_content, non_interactive):
        console.print("[bold red]Failed to create .env file[/]")
        if not non_interactive and not typer.confirm("Continue anyway?", default=False):
            raise typer.Exit(1)

    # Generate docker-compose.yml
    docker_compose_content = render_template_from_file(
        "docker",
        "docker-compose.yml.j2",
        {
            "docker_registry": "releases-docker.jfrog.io",
            "artifactory_version": config.version,
            "external_port": config.port,
            "data_dir": str(config.data_dir.absolute()),
            "postgres_user": config.postgres_user,
            "postgres_password": config.get_password("postgres"),
            "postgres_db": config.postgres_db,
            "db_type": "postgresql" if use_postgres else "derby",
            "use_postgres": use_postgres,
        },
    )
    if not safe_write_file(
        output_dir / "docker-compose.yml", docker_compose_content, non_interactive
    ):
        console.print("[bold red]Failed to create docker-compose.yml file[/]")
        if not non_interactive and not typer.confirm("Continue anyway?", default=False):
            raise typer.Exit(1)

    # Generate system.yaml
    import platform as platform_module

    system_yaml_content = render_template_from_file(
        "docker",
        "system.yaml.j2",
        {
            "use_postgres": use_postgres,
            "postgres_user": config.postgres_user,
            "postgres_password": config.get_password("postgres"),
            "postgres_db": config.postgres_db,
            "joinkey": joinkey,
            "platform": platform_module.system(),
        },
    )

    # Write system.yaml to etc directory (official location)
    system_yaml_success = safe_write_file(
        etc_dir / "system.yaml", system_yaml_content, non_interactive
    )
    if not system_yaml_success:
        console.print("[bold red]Failed to create system.yaml file in etc directory[/]")
        if not non_interactive and not typer.confirm("Continue anyway?", default=False):
            raise typer.Exit(1)

    # Also write to the output dir for reference
    if not safe_write_file(
        output_dir / "system.yaml", system_yaml_content, non_interactive
    ):
        console.print(
            "[yellow]Note: Failed to create reference copy of system.yaml in output directory[/]"
        )

    # Set permissions according to official JFrog documentation
    import platform

    console.print(
        "[yellow]Setting appropriate permissions for Artifactory directories...[/]"
    )

    # Set owner to 1030:1030 (Artifactory user inside the container)
    try:
        # This works on Linux/macOS, but we'll handle Windows separately
        if platform.system() != "Windows":
            # Instead of using sudo, provide clear instructions
            console.print(
                "[yellow]Important: For Docker bind mounts, you need to set proper permissions.[/]"
            )
            console.print(
                "[yellow]Please run the following commands with appropriate privileges:[/]"
            )
            console.print(f"[yellow]sudo chown -R 1030:1030 {var_dir}[/]")

            if platform.system() == "Darwin":  # macOS
                console.print(
                    "[yellow]On macOS, you also need to set additional permissions:[/]"
                )
                console.print(f"[yellow]sudo chmod -R 777 {var_dir}[/]")

            console.print(
                "[yellow]These commands ensure the Artifactory container can access the bind-mounted directories.[/]"
            )
        else:
            # Windows instructions
            console.print(
                "[yellow]On Windows, Docker handles permissions differently with bind mounts.[/]"
            )
            console.print(
                "[yellow]Ensure your Windows user has full control of the directory:[/]"
            )
            console.print(f"[yellow]{var_dir}[/]")
    except Exception as e:
        console.print(f"[yellow]Warning: Error during permission setup: {e}[/]")
        console.print("[yellow]You may need to manually set permissions.[/]")

    console.print("[green]Files generated successfully![/]")
    return output_dir


async def run_docker_compose(docker_compose_dir: Path, debug: bool = False) -> bool:
    """Run docker compose up command and monitor the process.

    Args:
        docker_compose_dir: Directory containing the docker-compose.yml file
        debug: Whether to run in debug mode (with more verbose output)

    Returns:
        bool: True if deployment was successful, False otherwise
    """
    console = Console()

    # Command to run
    cmd = ["docker", "compose", "up", "-d"]

    try:
        # Check if Docker is available
        run_docker_command(["docker", "--version"], check=True, capture_output=True)
    except (subprocess.SubprocessError, FileNotFoundError, ValueError):
        console.print(
            "[bold red]Error:[/] Docker not found. Please install Docker and try again."
        )
        return False

    # Start the Docker Compose process
    console.print(
        f"[bold blue]Starting Artifactory with Docker Compose in {docker_compose_dir}...[/]"
    )

    try:
        # Execute docker compose up with live output
        process = subprocess.Popen(  # nosec B603
            cmd,
            cwd=docker_compose_dir,
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
                    console.print(f"[red]{output.strip()}[/]")
                # Show all output in debug mode
                elif debug:
                    console.print(output.strip())

            if output == "" and process.poll() is not None:
                break

        return_code = process.poll()

        if return_code != 0:
            console.print(
                f"[bold red]Docker Compose failed with exit code {return_code}[/]"
            )

            # Display the last few output lines to help diagnose the issue
            if output_lines:
                console.print("[bold red]Docker Compose output:[/]")
                # Show the last 10 lines or all if less than 10
                for line in output_lines[-10:]:
                    console.print(f"  {line}")

                console.print(
                    "\n[bold]To see full Docker Compose output, run manually:[/]"
                )
                console.print(f"  cd {docker_compose_dir} && docker compose up")

            return False

        # Use the container manager to wait for health
        container_manager = DockerContainerManager(docker_compose_dir, console)

        # Wait for containers to be healthy
        if not await container_manager.wait_for_health(debug=debug):
            return False

        # Get the port number
        try:
            port_cmd = ["docker", "compose", "port", "artifactory", "8082"]
            port_result = run_docker_command(
                port_cmd, cwd=docker_compose_dir, capture_output=True, check=True
            )

            # Extract port from output like "0.0.0.0:8082"
            port = port_result.stdout.strip().split(":")[-1]
            console.print(
                f"[bold green]Artifactory is now running![/] Access at http://localhost:{port}"
            )

        except subprocess.SubprocessError:
            console.print(
                "[bold green]Artifactory is now running![/] Access using the configured port."
            )

        return True

    except subprocess.SubprocessError as e:
        console.print(f"[bold red]Error:[/] Failed to run Docker Compose: {e}")
        return False


def clean_docker_environment(docker_compose_dir: Path, debug: bool = False) -> bool:
    """Clean up Docker environment by stopping and removing containers.

    Args:
        docker_compose_dir: Directory containing the docker-compose.yml file
        debug: Whether to run in debug mode (with more verbose output)

    Returns:
        bool: True if cleanup was successful, False otherwise
    """
    console = Console()
    console.print("[yellow]Cleaning up existing Docker environment...[/]")

    # First try with docker compose
    try:
        # Check if docker-compose.yml exists in the given directory
        if not (docker_compose_dir / "docker-compose.yml").exists():
            console.print(
                "[yellow]No docker-compose.yml found in the directory, skipping compose cleanup.[/]"
            )
        else:
            # Try to stop and remove containers using docker compose
            process = run_docker_command(
                ["docker", "compose", "down", "--volumes", "--remove-orphans"],
                cwd=docker_compose_dir,
                capture_output=True,
                check=False,
            )

            if process.returncode == 0:
                console.print(
                    "[green]Successfully cleaned up Docker Compose environment.[/]"
                )
            else:
                if debug:
                    console.print(
                        f"[yellow]Docker Compose cleanup warning: {process.stderr}[/]"
                    )
    except Exception as e:
        console.print(
            f"[yellow]Warning: Could not clean up with Docker Compose: {e}[/]"
        )

    # Also try to remove containers directly by name as a fallback
    try:
        # Remove artifactory container if it exists
        run_docker_command(
            ["docker", "rm", "-f", "artifactory"], capture_output=True, check=False
        )

        # Remove postgres container if it exists
        run_docker_command(
            ["docker", "rm", "-f", "artifactory-postgres"],
            capture_output=True,
            check=False,
        )

        # Remove the network if it exists
        run_docker_command(
            ["docker", "network", "rm", "artifactory_network"],
            capture_output=True,
            check=False,
        )

        console.print("[green]Cleaned up artifactory containers.[/]")
        return True
    except Exception as e:
        if debug:
            console.print(f"[yellow]Container cleanup warning: {e}[/]")
        return False


async def _setup_docker_volumes(
    progress: Progress,
    overall_task: int,
    volume_manager: VolumeManager,
    use_named_volumes: bool,
    destination: Path,
    version: str,
    volume_driver: str,
    volume_sizes: Optional[Dict[str, Dict[str, str]]] = None,
    host_paths: Optional[Dict[str, Path]] = None,
    verbose: bool = False,
    debug: bool = False,
) -> Tuple[Dict[str, Dict[str, str]], OperationStatus]:
    """Set up Docker volumes for Artifactory.

    Args:
        progress: Progress object for reporting
        overall_task: Task ID in the progress
        volume_manager: The volume manager instance
        use_named_volumes: Whether to use named volumes
        destination: Destination directory
        version: Artifactory version
        volume_driver: Docker volume driver
        volume_sizes: Volume size specifications
        host_paths: Host path bindings
        verbose: Enable verbose output
        debug: Enable debug output

    Returns:
        Tuple of volumes dictionary and status
    """
    progress.update(
        overall_task,
        advance=20,
        description="[bold green]Setting up Docker volumes...",
    )

    try:
        volumes = {}

        if use_named_volumes:
            # Create named volumes with either host paths or regular volumes
            progress.print("[bold]Creating Docker named volumes...[/]")

            # Define default volume types
            volume_types = {
                "data": VolumeType.DATA,
                "logs": VolumeType.LOGS,
                "postgresql": VolumeType.POSTGRESQL,
                "etc": VolumeType.ETC,
            }

            # Only add backup volume if explicitly requested
            if (volume_sizes and "backup" in volume_sizes) or (
                host_paths and "backup" in host_paths
            ):
                volume_types["backup"] = VolumeType.BACKUP

            # Create each volume
            for vol_name, vol_type in volume_types.items():
                # Get driver options if any
                driver_opts = volume_sizes.get(vol_name, {}) if volume_sizes else {}

                # Get host path if specified
                host_path = host_paths.get(vol_name) if host_paths else None

                # Create volume
                display_name = f"Artifactory {vol_name.capitalize()} Volume ({version})"

                volume_id = volume_manager.create_volume(
                    vol_type,
                    name_suffix=version.replace(":", "-")
                    if version != "latest"
                    else None,
                    driver=volume_driver,
                    driver_opts=driver_opts,
                    host_path=host_path,
                    display_name=display_name,
                )

                # Add to volumes dict for container creation
                container_path = None
                if vol_name == "data":
                    container_path = "/var/opt/jfrog/artifactory/data"
                elif vol_name == "logs":
                    container_path = "/var/opt/jfrog/artifactory/logs"
                elif vol_name == "backup":
                    container_path = "/var/opt/jfrog/artifactory/backup"
                elif vol_name == "postgresql":
                    container_path = "/var/opt/jfrog/artifactory/postgresql"
                elif vol_name == "etc":
                    container_path = "/var/opt/jfrog/artifactory/etc"

                if container_path:
                    # Use Docker volume format
                    volumes[volume_id] = {"bind": container_path, "mode": "rw"}

                progress.print(f"Created {vol_name} volume: {volume_id}")

        else:
            # Use bind mounts to directories under destination
            progress.print("[bold]Setting up bind mounts...[/]")
            volume_dirs = {
                "data": destination / "data",
                "logs": destination / "logs",
                "etc": destination / "etc",
                "backup": destination / "backup",
                "postgresql": destination / "postgresql",
            }

            # Create directories and set up bind mounts
            for name, path in volume_dirs.items():
                path.mkdir(parents=True, exist_ok=True)
                volumes[str(path)] = {
                    "bind": f"/var/opt/jfrog/artifactory/{name}",
                    "mode": "rw",
                }
                progress.print(f"Created bind mount: {path}")

        return volumes, OperationStatus.SUCCESS

    except Exception as e:
        progress.print(f"[bold red]Failed to set up Docker volumes:[/] {e}")
        if debug:
            import traceback

            progress.print(traceback.format_exc())
        return {}, OperationStatus.ERROR


async def _setup_docker_containers(
    progress: Progress,
    overall_task: int,
    docker_client: docker.DockerClient,
    docker_image: str,
    volumes: Dict[str, Dict[str, str]],
    port: int,
    destination: Path,
    start: bool,
    non_interactive: bool = False,
    verbose: bool = False,
    debug: bool = False,
) -> OperationStatus:
    """Set up and start Docker containers for Artifactory.

    Args:
        progress: Progress object for reporting
        overall_task: Task ID in the progress
        docker_client: Docker client instance
        docker_image: Docker image to use
        volumes: Volume mappings
        port: Port to expose
        destination: Destination directory
        start: Whether to start containers
        non_interactive: Non-interactive mode
        verbose: Enable verbose output
        debug: Enable debug output

    Returns:
        Operation status
    """
    progress.update(
        overall_task,
        advance=30,
        description="[bold green]Creating Docker container...",
    )

    try:
        container_name = "artifactory"

        # Check if container already exists
        try:
            existing_container = docker_client.containers.get(container_name)
            if existing_container:
                progress.print(
                    f"[yellow]Container {container_name} already exists. Removing it.[/]"
                )
                existing_container.remove(force=True)
        except docker.errors.NotFound:
            # Container doesn't exist, which is fine
            pass

        # Set up environment variables
        environment = {
            "JF_SHARED_DATABASE_TYPE": "postgresql",
            "JF_SHARED_DATABASE_USERNAME": "artifactory",
            "JF_SHARED_DATABASE_PASSWORD": "password",
            "JF_SHARED_DATABASE_URL": "jdbc:postgresql://artifactory-postgres:5432/artifactory",
            "JF_ROUTER_ENTRYPOINTS_EXTERNALURL": f"http://localhost:{port}",
        }

        # Create container
        progress.print(f"Creating {container_name} container...")
        container = docker_client.containers.create(
            docker_image,
            name=container_name,
            environment=environment,
            ports={8082: port},
            volumes=volumes,
            # Use a dedicated network for Artifactory
            network="artifactory_network",
        )

        # Create a network if it doesn't exist
        try:
            networks = docker_client.networks.list(names=["artifactory_network"])
            if not networks:
                progress.print("Creating artifactory_network...")
                docker_client.networks.create("artifactory_network")
        except Exception as e:
            progress.print(f"[yellow]Warning creating network: {e}[/]")

        # Create PostgreSQL container
        progress.print("Creating PostgreSQL container...")
        pg_volumes = {}

        # If we have a postgresql volume defined, use it
        if "postgresql" in volumes:
            for vol_name, vol_spec in volumes.items():
                if "postgresql" in vol_name or "postgresql" in vol_spec.get("bind", ""):
                    pg_volumes[vol_name] = vol_spec
                    break

        # If no postgresql volume found, create a default one
        if not pg_volumes:
            pg_data_dir = destination / "postgresql"
            pg_data_dir.mkdir(parents=True, exist_ok=True)
            pg_volumes[str(pg_data_dir)] = {
                "bind": "/var/lib/postgresql/data",
                "mode": "rw",
            }

        # Create PostgreSQL container
        try:
            # Check if container already exists
            try:
                existing_pg = docker_client.containers.get("artifactory-postgres")
                if existing_pg:
                    progress.print(
                        "[yellow]PostgreSQL container already exists. Removing it.[/]"
                    )
                    existing_pg.remove(force=True)
            except docker.errors.NotFound:
                # Container doesn't exist, which is fine
                pass

            pg_environment = {
                "POSTGRES_DB": "artifactory",
                "POSTGRES_USER": "artifactory",
                "POSTGRES_PASSWORD": "password",
            }

            docker_client.containers.create(
                "postgres:13",
                name="artifactory-postgres",
                environment=pg_environment,
                volumes=pg_volumes,
                network="artifactory_network",
            )
        except Exception as e:
            progress.print(f"[yellow]Warning creating PostgreSQL container: {e}[/]")

        progress.update(
            overall_task,
            advance=30,
            description="[bold green]Starting containers...",
        )

        # Start PostgreSQL first
        progress.print("Starting PostgreSQL container...")
        try:
            pg_container = docker_client.containers.get("artifactory-postgres")
            pg_container.start()
        except Exception as e:
            progress.print(f"[bold red]Failed to start PostgreSQL container: {e}[/]")
            return OperationStatus.ERROR

        # Give PostgreSQL a moment to start
        progress.print("Waiting for PostgreSQL to initialize...")
        time.sleep(5)

        # Start Artifactory container
        if start:
            progress.print("Starting Artifactory container...")
            container.start()

            progress.update(
                overall_task,
                completed=100,
                description="[bold green]Installation complete!",
            )
            progress.print(
                f"\n[bold green]Artifactory is now running![/] Access it at: http://localhost:{port}"
            )
            progress.print(
                "[yellow]Note:[/] It may take a minute or two for Artifactory to fully start."
            )
            progress.print(
                "[yellow]Default credentials:[/] admin/password (change this immediately after login!)"
            )
        else:
            progress.update(
                overall_task,
                completed=100,
                description="[bold green]Installation complete (not started)!",
            )
            progress.print("\n[bold green]Artifactory installation is complete![/]")
            progress.print(
                "To start Artifactory, run: docker start artifactory-postgres && docker start artifactory"
            )
            progress.print(f"Once started, access it at: http://localhost:{port}")

        return OperationStatus.SUCCESS

    except Exception as e:
        progress.print(f"[bold red]Failed to create or start containers: {e}[/]")
        if debug:
            import traceback

            progress.print(traceback.format_exc())
        return OperationStatus.ERROR


async def install_docker(
    version: str = "latest",
    platform: Optional[Platform] = None,
    destination: Optional[Path] = None,
    port: int = 8081,
    start: bool = True,
    non_interactive: bool = False,
    verbose: bool = False,
    debug: bool = False,
    use_named_volumes: bool = False,
    volume_driver: str = "local",
    volume_sizes: Optional[Dict[str, Dict[str, str]]] = None,
    host_paths: Optional[Dict[str, Path]] = None,
) -> OperationStatus:
    """
    Install Artifactory using Docker.

    Args:
        version: Artifactory version to install
        platform: Platform to install
        destination: Destination directory for Artifactory data
        port: Port to run Artifactory on
        start: Start Artifactory after installation
        non_interactive: Non-interactive mode
        verbose: Verbose output
        debug: Enable debug output
        use_named_volumes: Use Docker named volumes instead of bind mounts
        volume_driver: Docker volume driver to use for named volumes
        volume_sizes: Dictionary of volume sizes by type (data, logs, etc.)
        host_paths: Dictionary of host paths by volume type (for bind mounting)

    Returns:
        OperationStatus: Status of the operation
    """
    console = SapoConsole()
    docker_image = f"releases-docker.jfrog.io/jfrog/artifactory-pro:{version}"

    # Ensure a destination directory exists or use default
    if destination is None:
        destination = Path.home() / ".jfrog" / "artifactory"

    # Create the destination directory if it doesn't exist
    if not destination.exists():
        destination.mkdir(parents=True, exist_ok=True)
        console.print(f"Created destination directory: {destination}")

    # Check if Docker is installed
    if not check_docker_installed():
        console.print(
            "[bold red]Docker is not installed.[/] Please install Docker first."
        )
        return OperationStatus.ERROR

    # Initialize Docker client
    try:
        docker_client = docker.from_env()
    except DockerException as e:
        console.print(f"[bold red]Failed to connect to Docker:[/] {e}")
        return OperationStatus.ERROR

    # Define volume paths
    with Progress() as progress:
        # Create the overall progress task
        overall_task = progress.add_task(
            "[bold green]Installing Artifactory...", total=100
        )

        # Pull the Docker image
        progress.update(
            overall_task, advance=10, description="[bold green]Pulling Docker image..."
        )
        try:
            if verbose:
                progress.print(f"Pulling image: {docker_image}")
            docker_client.images.pull(docker_image)
        except ImageNotFound:
            progress.print(f"[bold red]Docker image not found:[/] {docker_image}")
            return OperationStatus.ERROR
        except Exception as e:
            progress.print(f"[bold red]Failed to pull Docker image:[/] {e}")
            return OperationStatus.ERROR

        # Set up Docker volumes
        volumes, status = await _setup_docker_volumes(
            progress=progress,
            overall_task=overall_task,
            volume_manager=VolumeManager(console=console),
            use_named_volumes=use_named_volumes,
            destination=destination,
            version=version,
            volume_driver=volume_driver,
            volume_sizes=volume_sizes,
            host_paths=host_paths,
            verbose=verbose,
            debug=debug,
        )

        if status != OperationStatus.SUCCESS:
            return status

        # Create and start containers
        return await _setup_docker_containers(
            progress=progress,
            overall_task=overall_task,
            docker_client=docker_client,
            docker_image=docker_image,
            volumes=volumes,
            port=port,
            destination=destination,
            start=start,
            non_interactive=non_interactive,
            verbose=verbose,
            debug=debug,
        )


def install_docker_sync(
    version: str = "latest",
    platform: Optional[Platform] = None,
    destination: Optional[Path] = None,
    port: int = 8081,
    start: bool = True,
    non_interactive: bool = False,
    verbose: bool = False,
    debug: bool = False,
    use_named_volumes: bool = False,
    volume_driver: str = "local",
    volume_sizes: Optional[Dict[str, Dict[str, str]]] = None,
    host_paths: Optional[Dict[str, Path]] = None,
) -> OperationStatus:
    """
    Synchronous wrapper for install_docker.

    Args:
        version: Artifactory version to install
        platform: Platform to install
        destination: Destination directory for Artifactory data
        port: Port to run Artifactory on
        start: Start Artifactory after installation
        non_interactive: Non-interactive mode
        verbose: Verbose output
        debug: Enable debug output
        use_named_volumes: Use Docker named volumes instead of bind mounts
        volume_driver: Docker volume driver to use for named volumes
        volume_sizes: Dictionary of volume sizes by type
        host_paths: Dictionary of host paths by volume type

    Returns:
        OperationStatus: Status of the operation
    """
    try:
        result = asyncio.run(
            install_docker(
                version=version,
                platform=platform,
                destination=destination,
                port=port,
                start=start,
                non_interactive=non_interactive,
                verbose=verbose,
                debug=debug,
                use_named_volumes=use_named_volumes,
                volume_driver=volume_driver,
                volume_sizes=volume_sizes,
                host_paths=host_paths,
            )
        )
        # Convert OperationStatus to boolean for the test
        return result == OperationStatus.SUCCESS
    except typer.Exit:
        # Return False for any typer.Exit exceptions with non-zero exit codes
        return False
    except Exception:
        # Any other exception is considered a failure
        return False
