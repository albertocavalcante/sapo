"""Docker-based installation mode for Artifactory.

This module handles Docker-based installation of Artifactory OSS,
generating the necessary docker-compose.yml and system.yaml files.
"""

import asyncio
import string
import secrets
from pathlib import Path
from typing import Optional, Dict, Union
import typer
from rich.console import Console

from .config import DockerConfig, DatabaseType
from .files import DockerFileManager
from .container import DockerContainerManager
from ..common import OperationStatus

# Import volume management functionality
from .volume import VolumeManager, VolumeType

__all__ = [
    "install_docker",
    "install_docker_sync",
    "DockerConfig",
    "DatabaseType",
    "DockerFileManager",
    "DockerContainerManager",
    "VolumeManager",
    "VolumeType",
    "generate_files",
    "run_docker_compose",
    "generate_password",
]


# Compatibility functions for tests
def generate_files(config: DockerConfig) -> Path:
    """Generate Docker files for Artifactory installation.

    This is a compatibility function for tests.

    Args:
        config: Docker configuration

    Returns:
        Path: Path to the compose directory
    """
    console = Console()
    file_manager = DockerFileManager(config, console)
    file_manager.generate_all_files(non_interactive=True)
    return config.output_dir


async def run_docker_compose(compose_dir: Path, debug: bool = False) -> bool:
    """Run Docker Compose to start Artifactory.

    This is a compatibility function for tests.

    Args:
        compose_dir: Path to the compose directory
        debug: Whether to show detailed debug output

    Returns:
        bool: True if successful
    """
    console = Console()
    container_manager = DockerContainerManager(compose_dir, console)
    return await container_manager.start_containers(debug=debug)


async def install_docker(
    version: str,
    port: int = 8082,
    data_dir: Optional[Path] = None,
    non_interactive: bool = False,
    start: bool = False,
    use_derby: bool = False,
    joinkey: Optional[str] = None,
    debug: bool = False,
    use_named_volumes: bool = False,
    volume_driver: Optional[str] = None,
    volume_sizes: Optional[Dict[str, str]] = None,
) -> None:
    """Install Artifactory using Docker.

    Args:
        version: Artifactory version to install
        port: External port for Artifactory
        data_dir: Custom data directory
        non_interactive: Skip confirmation prompts
        start: Start Artifactory after installation
        use_derby: Whether to use Derby instead of PostgreSQL (not recommended)
        joinkey: Security join key (generated if not provided)
        debug: Whether to show detailed debug output
        use_named_volumes: Whether to use Docker named volumes
        volume_driver: Docker volume driver to use
        volume_sizes: Size configuration for Docker volumes

    Raises:
        typer.Exit: If the installation fails
    """
    console = Console()

    try:
        # Create the configuration with specified parameters
        config = DockerConfig(
            version=version,
            port=port,
            data_dir=data_dir or Path.home() / ".jfrog" / "artifactory",
            database_type=DatabaseType.DERBY if use_derby else DatabaseType.POSTGRESQL,
            joinkey=joinkey,
        )

        # Show installation information
        console.print("[bold]JFrog Artifactory OSS Docker Installation[/]")
        console.print(f"Version: {config.version}")
        console.print(f"Port: {config.port}")
        console.print(f"Data directory: {config.data_dir.absolute()}")
        console.print(
            f"Database: {'Derby (Not Recommended)' if config.use_derby else 'PostgreSQL (Recommended)'}"
        )

        if use_named_volumes:
            console.print("Storage: Docker named volumes")
            if volume_driver:
                console.print(f"Volume driver: {volume_driver}")
        else:
            console.print(f"Storage: Bind mounts to {config.data_dir.absolute()}")

        if config.use_derby:
            console.print(
                "[bold yellow]Warning:[/] Derby database is not recommended for Docker installations and may cause stability issues."
            )

        # Confirm installation unless in non-interactive mode
        if not non_interactive:
            confirmed = typer.confirm(
                "Do you want to proceed with the installation?", default=True
            )
            if not confirmed:
                console.print("[yellow]Installation cancelled by user.[/]")
                raise typer.Exit(0)  # Exit gracefully with code 0

        # Create volumes if using named volumes
        volume_names = {}
        if use_named_volumes:
            console.print("[bold]Setting up Docker volumes for Artifactory...[/]")

            # Set default volume sizes if not provided
            if not volume_sizes:
                volume_sizes = {}

            # Create volume manager
            volume_manager = VolumeManager(console=console)

            try:
                # Format version for volume name (e.g., 7.9.2 -> v7_9_2)
                version_suffix = f"v{version.replace('.', '_')}"

                # Create volume options dictionary with sizes
                volume_opts = {}

                # Only include backup volume if explicitly requested
                volume_types_to_create = [
                    VolumeType.DATA,
                    VolumeType.LOGS,
                    VolumeType.POSTGRESQL,
                ]

                # Add backup volume only if user specified backup size
                if "backup" in volume_sizes:
                    volume_types_to_create.append(VolumeType.BACKUP)

                for volume_type in volume_types_to_create:
                    # Set defaults by volume type
                    if volume_type == VolumeType.DATA and "data" not in volume_sizes:
                        volume_opts[volume_type] = {"size": "10G"}
                    elif volume_type == VolumeType.LOGS and "logs" not in volume_sizes:
                        volume_opts[volume_type] = {"size": "3G"}
                    elif (
                        volume_type == VolumeType.BACKUP
                        and "backup" not in volume_sizes
                    ):
                        volume_opts[volume_type] = {"size": "20G"}
                    elif (
                        volume_type == VolumeType.POSTGRESQL
                        and "postgresql" not in volume_sizes
                    ):
                        volume_opts[volume_type] = {"size": "15G"}

                    # Override with user-specified sizes
                    if volume_type.value in volume_sizes:
                        volume_opts[volume_type] = {
                            "size": volume_sizes[volume_type.value]
                        }

                # Add etc volume too
                volume_opts[VolumeType.DATA] = volume_opts.get(
                    VolumeType.DATA, {"size": "1G"}
                )

                # Create the volumes
                volumes = volume_manager.create_volume_set(
                    version_suffix, driver=volume_driver, size_opts=volume_opts
                )

                # Store volume names for compose file generation
                for volume_type, name in volumes.items():
                    volume_names[volume_type.value] = name

                # Also create an etc volume
                etc_volume_name = volume_manager.create_volume(
                    VolumeType.DATA,
                    f"etc_{version_suffix}",
                    driver=volume_driver,
                    driver_opts=volume_opts.get(VolumeType.DATA),
                )
                volume_names["etc"] = etc_volume_name

                console.print(
                    "[green]Successfully created Docker volumes for Artifactory![/]"
                )
                volume_manager.display_volumes()

            except Exception as e:
                console.print(f"[bold red]Error creating Docker volumes:[/] {e}")
                if not non_interactive:
                    if not typer.confirm(
                        "Continue without using named volumes?", default=False
                    ):
                        raise typer.Exit(1)
                    use_named_volumes = False
                else:
                    raise typer.Exit(1)

        # Create file manager and generate files
        file_manager = DockerFileManager(
            config,
            console,
            use_named_volumes=use_named_volumes,
            volume_names=volume_names,
        )

        file_results = file_manager.generate_all_files(non_interactive)

        # Check if all files were created successfully
        all_success = all(result.success for result in file_results.values())

        if all_success:
            console.print("\n[green]Docker files generated successfully![/]")
        else:
            console.print("\n[yellow]Some files were not generated successfully.[/]")

        console.print(f"Docker Compose directory: {config.output_dir}")

        # Show security information
        console.print("\n[yellow]Security Information:[/]")
        console.print(f"Join Key: {config.joinkey}")
        console.print("[bold yellow]Keep this information secure![/]")

        if config.use_postgres:
            # Show PostgreSQL password if using PostgreSQL
            console.print("\n[yellow]PostgreSQL Configuration:[/]")
            console.print(f"Username: {config.postgres_user}")
            console.print(f"Password: {config.get_password('postgres')}")
            console.print(f"Database: {config.postgres_db}")
            console.print("[yellow]Make sure to save this information securely![/]")

        # Start Artifactory if requested
        if start:
            console.print("\n[bold]Starting Artifactory with Docker Compose...[/]")

            # Create container manager
            container_manager = DockerContainerManager(config.output_dir, console)

            # Clean up any existing containers first
            if not non_interactive:
                should_cleanup = typer.confirm(
                    "Clean up any existing Docker containers before starting?",
                    default=True,
                )
                if should_cleanup:
                    container_manager.clean_environment(debug=debug)
            else:
                # In non-interactive mode, always clean up first
                container_manager.clean_environment(debug=debug)

            success = await container_manager.start_containers(debug=debug)

            if success:
                console.print("[green]Artifactory is starting up![/]")
                console.print("\n[bold]To access Artifactory:[/]")
                console.print(f"http://localhost:{config.port}/ui/")
                console.print("\nDefault admin credentials: admin/password")
                console.print(
                    "[bold red]Important:[/] Change the default password immediately after first login!"
                )
                console.print("\nIt may take a minute or two to fully start.")

                # If using named volumes, show helpful information
                if use_named_volumes:
                    console.print("\n[bold]Volume Information:[/]")
                    console.print(
                        "Your data is stored in Docker named volumes which can be managed with:"
                    )
                    console.print("- docker volume ls")
                    console.print("- sapo volume list")
                    console.print("\nTo back up these volumes:")
                    console.print("sapo volume backup --name <volume-name>")
            else:
                console.print("[red]Failed to start Artifactory.[/]")
                console.print("\n[bold]Troubleshooting:[/]")
                console.print("1. Verify Docker is running properly")
                console.print("2. Check if port conflicts exist")
                console.print("3. Ensure sufficient disk space and permissions")
                console.print(
                    "4. Clean up any previous installations: docker rm -f artifactory artifactory-postgres"
                )
                console.print("5. Examine Docker logs: docker logs artifactory")
                console.print(
                    "\n[bold]To start Artifactory manually with full output, run:[/]"
                )
                console.print(f"cd {config.output_dir} && docker compose up")

                # Offer to clean up failed containers
                if not non_interactive and typer.confirm(
                    "Would you like to clean up the failed containers?", default=True
                ):
                    container_manager.clean_environment(debug=debug)
                    console.print(
                        "[green]Cleanup complete. You can try again with a fresh installation.[/]"
                    )
        else:
            # Display instructions
            console.print("\n[bold]To start Artifactory, run:[/]")
            console.print(f"cd {config.output_dir} && docker compose up -d")
            console.print("\n[bold]To access Artifactory after starting:[/]")
            console.print(f"http://localhost:{config.port}/ui/")
            console.print("\nDefault admin credentials: admin/password")
            console.print(
                "[bold red]Important:[/] Change the default password immediately after first login!"
            )

    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/]")
        if debug:
            # Print stack trace in debug mode
            import traceback

            console.print("[bold red]Stack trace:[/]")
            console.print(traceback.format_exc())
        raise typer.Exit(1)


# Synchronous entry point for CLI
def install_docker_sync(
    version: str = "latest",
    platform: Optional[str] = None,
    destination: Optional[Path] = None,
    port: int = 8081,
    start: bool = True,
    non_interactive: bool = False,
    verbose: bool = False,
    debug: bool = False,
    use_named_volumes: bool = False,
    volume_driver: str = "local",
    volume_sizes: Optional[Dict[str, Union[str, Dict[str, str]]]] = None,
    host_paths: Optional[Dict[str, Path]] = None,
) -> OperationStatus:
    """Synchronous wrapper for the install_docker function.

    Args:
        version: Artifactory version to install
        platform: Platform to install on (linux, darwin, windows)
        destination: Installation directory
        port: Port to run Artifactory on
        start: Whether to start Artifactory after installation
        non_interactive: Whether to run in non-interactive mode
        verbose: Whether to show verbose output
        debug: Whether to show debug output
        use_named_volumes: Whether to use Docker named volumes
        volume_driver: Docker volume driver to use
        volume_sizes: Dictionary of volume sizes by volume type
        host_paths: Dictionary of host paths by volume type

    Returns:
        OperationStatus: Success or error status
    """
    try:
        # Use the local async Docker installation function from this module
        return asyncio.run(
            install_docker(
                version=version,
                port=port,
                data_dir=destination,
                non_interactive=non_interactive,
                start=start,
                debug=debug,
                use_named_volumes=use_named_volumes,
                volume_driver=volume_driver,
                volume_sizes=volume_sizes,
            )
        )
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return OperationStatus.WARNING
    except Exception as e:
        # Catch and report any exceptions
        from rich.console import Console

        console = Console()
        console.print(f"[bold red]Error during installation:[/] {e}")

        # Print traceback in debug mode
        if debug:
            import traceback

            console.print(traceback.format_exc())

        return OperationStatus.ERROR


_password_cache: Dict[str, str] = {}


def generate_password(key: str) -> str:
    """Generate a secure random password.

    Args:
        key: Identifier for the password

    Returns:
        str: The generated password
    """
    if key not in _password_cache:
        # Use Docker/YAML-safe character classes for password complexity
        letters = string.ascii_letters
        digits = string.digits
        # Use only Docker/YAML-safe special characters (avoid $, `, \, ", ')
        special_chars = "!@#%^&*()-_=+[]{}|;:,.<>/?"

        # Create a base password that has at least one of each required character type
        base_password = [
            secrets.choice(letters),  # At least one letter
            secrets.choice(digits),  # At least one digit
            secrets.choice(special_chars),  # At least one special char
        ]

        # Fill the rest with random selections from all characters
        all_chars = letters + digits + special_chars
        base_password.extend(
            secrets.choice(all_chars) for _ in range(32 - len(base_password))
        )

        # Shuffle the password to avoid predictable character placement
        secrets.SystemRandom().shuffle(base_password)
        _password_cache[key] = "".join(base_password)

    return _password_cache[key]
