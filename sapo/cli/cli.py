"""Command definitions for the Sapo CLI.

This module contains all command definitions for the Sapo CLI application,
using the Typer framework to define the command structure and options.
"""

import asyncio
import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .artifactory import (
    ArtifactoryConfig,
    Platform,
    install_artifactory,
    list_versions,
    show_info,
)
from .console import SapoConsole
from .install_mode import InstallMode
from .install_mode.common import OperationStatus
from .install_mode.docker import install_docker_sync
from .install_mode.docker.volume import VolumeManager, VolumeType
from .release_notes import display_release_notes

console = Console()
sapo_console = SapoConsole()

app = typer.Typer(
    help="Download and install JFrog Artifactory OSS",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Create a volume subcommand group
volume_app = typer.Typer(help="Manage Docker volumes for Artifactory")
app.add_typer(volume_app, name="volume")

# Install subcommand group removed - using unified install command


@app.command()
def install(
    version: str = typer.Option(
        "7.111.9", "--version", "-v", help="Artifactory version to install"
    ),
    mode: InstallMode = typer.Option(
        None, "--mode", "-m", help="Installation mode (docker, local, helm)"
    ),
    platform: Platform = typer.Option(
        Platform.DARWIN,
        "--platform",
        "-p",
        help="Platform to download (for local mode)",
    ),
    destination: Optional[Path] = typer.Option(
        None,
        "--destination",
        "--dest",
        "-d",
        help="Destination directory (defaults to $HOME/dev/tools for local, $HOME/.jfrog/artifactory for docker)",
    ),
    port: int = typer.Option(
        8082, "--port", help="External port for Docker or Helm installation"
    ),
    keep_archive: bool = typer.Option(
        False,
        "--keep",
        "-k",
        help="Keep the downloaded archive after extraction (local mode only)",
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Non-interactive mode, skip confirmation prompts"
    ),
    start: bool = typer.Option(
        False, "--start", help="Start Artifactory after installation (Docker mode only)"
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Show verbose logs"),
    debug: bool = typer.Option(
        False, "--debug", help="Show detailed debug information including Docker output"
    ),
    # Volume management options for Docker mode
    use_named_volumes: bool = typer.Option(
        False,
        "--use-volumes",
        help="Use named Docker volumes instead of bind mounts (Docker mode only)",
    ),
    volume_driver: Optional[str] = typer.Option(
        None,
        "--volume-driver",
        help="Docker volume driver to use for volumes (Docker mode only)",
    ),
    data_volume_size: Optional[str] = typer.Option(
        None, "--data-size", help="Size for data volume, e.g. '10G' (Docker mode only)"
    ),
    logs_volume_size: Optional[str] = typer.Option(
        None, "--logs-size", help="Size for logs volume, e.g. '3G' (Docker mode only)"
    ),
    backup_volume_size: Optional[str] = typer.Option(
        None,
        "--backup-size",
        help="Size for backup volume, e.g. '20G' (Docker mode only)",
    ),
    db_volume_size: Optional[str] = typer.Option(
        None,
        "--db-size",
        help="Size for database volume, e.g. '15G' (Docker mode only)",
    ),
    etc_volume_size: Optional[str] = typer.Option(
        None,
        "--etc-size",
        help="Size for etc volume, e.g. '1G' (Docker mode only)",
    ),
    data_host_path: Optional[Path] = typer.Option(
        None,
        "--data-path",
        help="Host path to bind for data volume (Docker mode only)",
    ),
    logs_host_path: Optional[Path] = typer.Option(
        None,
        "--logs-path",
        help="Host path to bind for logs volume (Docker mode only)",
    ),
    backup_host_path: Optional[Path] = typer.Option(
        None,
        "--backup-path",
        help="Host path to bind for backup volume (Docker mode only)",
    ),
    db_host_path: Optional[Path] = typer.Option(
        None,
        "--db-path",
        help="Host path to bind for database volume (Docker mode only)",
    ),
    etc_host_path: Optional[Path] = typer.Option(
        None,
        "--etc-path",
        help="Host path to bind for etc volume (Docker mode only)",
    ),
) -> None:
    """Download and install JFrog Artifactory OSS.

    Installs Artifactory using the specified installation mode (local, docker, or helm).
    For local installation, it downloads the specified version, verifies its checksum,
    and extracts it to the destination directory.
    For Docker installation, it generates docker-compose files and configuration.
    """
    # Docker mode installation
    if mode == InstallMode.DOCKER:
        # For Docker mode, default start to True if not explicitly set to False
        if not start:
            start = True

        # Handle volume options for Docker mode
        if use_named_volumes:
            console.print("[bold]Using named Docker volumes for Artifactory[/]")

            # Collect volume sizes if specified
            volume_sizes = {}
            if data_volume_size:
                volume_sizes["data"] = data_volume_size
            if logs_volume_size:
                volume_sizes["logs"] = logs_volume_size
            if backup_volume_size:
                volume_sizes["backup"] = backup_volume_size
            if db_volume_size:
                volume_sizes["postgresql"] = db_volume_size
            if etc_volume_size:
                volume_sizes["etc"] = etc_volume_size

            # Collect host paths for volumes if specified
            host_paths = {}
            if data_host_path:
                host_paths["data"] = data_host_path
            if logs_host_path:
                host_paths["logs"] = logs_host_path
            if backup_host_path:
                host_paths["backup"] = backup_host_path
            if db_host_path:
                host_paths["postgresql"] = db_host_path
            if etc_host_path:
                host_paths["etc"] = etc_host_path

            # Check if we're using host paths
            using_host_paths = any(
                [
                    data_host_path,
                    logs_host_path,
                    backup_host_path,
                    db_host_path,
                    etc_host_path,
                ]
            )

            # Give warning if mixing named volumes with host paths
            if using_host_paths:
                console.print(
                    "[bold yellow]Notice:[/] Using host paths with named volumes"
                )
                console.print(
                    "This will create named volumes bound to specific directories on your host"
                )

            # Now pass these to install_docker_sync directly
            install_docker_sync(
                version=version,
                platform=platform,
                destination=destination,
                port=port,
                start=start,
                non_interactive=yes,
                verbose=verbose,
                debug=debug,
                use_named_volumes=True,
                volume_driver=volume_driver,
                volume_sizes=volume_sizes,
                host_paths=host_paths if using_host_paths else None,
            )
        else:
            # Standard installation without named volumes
            install_docker_sync(
                version=version,
                platform=platform,
                destination=destination,
                port=port,
                start=start,
                non_interactive=yes,
                verbose=verbose,
                debug=debug,
            )
    # Default to local installation if no mode specified
    else:
        install_artifactory(
            version=version,
            platform=platform,
            destination=destination,
            keep_archive=keep_archive,
            non_interactive=yes,
            verbose=verbose,
        )


@app.command()
def releases(
    limit: int = typer.Option(
        10, "--limit", "-l", help="Number of versions to show (default: 10)"
    ),
) -> None:
    """List available Artifactory releases with size and timestamp information.

    Fetches and displays a list of available Artifactory versions,
    including file sizes and release dates.
    """
    list_versions(limit=limit)


@app.command()
def info(
    version: str = typer.Option(
        "7.111.9", "--version", "-v", help="Artifactory version to check"
    ),
) -> None:
    """Show information about the script and available URLs.

    Displays configuration information, download URLs, and other details
    about the specified Artifactory version.
    """
    config = ArtifactoryConfig(version=version)
    show_info(config)


@app.command(name="release-notes")
def release_notes(
    version: str = typer.Option(
        ..., "--version", "-v", help="Artifactory version to get release notes for"
    ),
    debug: bool = typer.Option(False, "--debug", help="Enable debug output"),
) -> None:
    """Get release notes for a specific Artifactory version.

    Fetches and displays release notes for the specified Artifactory version,
    including fixed issues and other changes.
    """
    asyncio.run(display_release_notes(version, debug))


# Volume management commands


@volume_app.command(name="list")
def volume_list() -> None:
    """List all Docker volumes used by Artifactory."""
    volume_manager = VolumeManager(console=console)
    volume_manager.display_volumes()


@volume_app.command(name="create")
def volume_create(
    name: str = typer.Option(..., "--name", "-n", help="Base name for the volume set"),
    driver: Optional[str] = typer.Option(
        None, "--driver", "-d", help="Docker volume driver to use"
    ),
    data_size: Optional[str] = typer.Option(
        "10G", "--data-size", help="Size for data volume"
    ),
    logs_size: Optional[str] = typer.Option(
        "3G", "--logs-size", help="Size for logs volume"
    ),
    backup_size: Optional[str] = typer.Option(
        "20G", "--backup-size", help="Size for backup volume"
    ),
    db_size: Optional[str] = typer.Option(
        "15G", "--db-size", help="Size for database volume"
    ),
) -> None:
    """Create a new set of Docker volumes for Artifactory.

    Creates a complete set of volumes (data, logs, backup, postgresql)
    with specified driver and sizes.
    """
    volume_manager = VolumeManager(console=console)

    # Collect volume sizes
    volume_sizes = {
        VolumeType.DATA: {"size": data_size},
        VolumeType.LOGS: {"size": logs_size},
        VolumeType.BACKUP: {"size": backup_size},
        VolumeType.POSTGRESQL: {"size": db_size},
    }

    try:
        # Create volumes
        volumes = volume_manager.create_volume_set(
            name, driver=driver, size_opts=volume_sizes
        )

        # Display created volumes
        console.print("[green]Successfully created Docker volumes:[/]")
        volume_manager.display_volumes()

        # Show docker-compose snippet
        console.print("\n[bold]Add this to your docker-compose.yml under 'volumes:'[/]")

        compose_volumes = volume_manager.generate_compose_volumes(volumes)
        import yaml

        console.print(yaml.dump(compose_volumes, default_flow_style=False))

    except Exception as e:
        console.print(f"[bold red]Error creating volumes:[/] {e}")
        raise typer.Exit(1)


@volume_app.command(name="delete")
def volume_delete(
    name: str = typer.Option(..., "--name", "-n", help="Name of volume to delete"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force deletion (dangerous)"
    ),
) -> None:
    """Delete a Docker volume used by Artifactory.

    Warning: This will permanently delete all data in the volume.
    """
    volume_manager = VolumeManager(console=console)

    # Confirm deletion
    if not force:
        confirm = typer.confirm(
            f"Are you sure you want to delete volume {name}? This action cannot be undone.",
            default=False,
        )
        if not confirm:
            console.print("[yellow]Operation cancelled.[/]")
            return

    # Delete volume
    success = volume_manager.delete_volume(name, force=force)

    if success:
        console.print(f"[green]Successfully deleted volume {name}[/]")
    else:
        console.print(f"[bold red]Failed to delete volume {name}[/]")
        raise typer.Exit(1)


@volume_app.command(name="backup")
def volume_backup(
    volume_name: str = typer.Option(
        ..., "--name", "-n", help="Name of volume to backup"
    ),
    output_dir: Path = typer.Option(
        Path.home() / ".jfrog" / "backups",
        "--output",
        "-o",
        help="Directory to save backup",
    ),
) -> None:
    """Backup an Artifactory Docker volume to a tar file."""
    volume_manager = VolumeManager(console=console)

    # Backup volume
    status, backup_file = volume_manager.backup_volume(volume_name, output_dir)

    if status == OperationStatus.SUCCESS and backup_file:
        console.print(
            f"[green]Successfully backed up volume {volume_name} to {backup_file}[/]"
        )
    else:
        console.print(f"[bold red]Failed to backup volume {volume_name}[/]")
        raise typer.Exit(1)


@volume_app.command(name="restore")
def volume_restore(
    backup_file: Path = typer.Option(
        ..., "--file", "-f", help="Backup file to restore from"
    ),
    volume_name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Name of volume to restore to (will create new if not provided)",
    ),
    volume_type: Optional[VolumeType] = typer.Option(
        None,
        "--type",
        "-t",
        help="Type of volume (required if volume_name not provided)",
    ),
) -> None:
    """Restore an Artifactory Docker volume from a backup file."""
    volume_manager = VolumeManager(console=console)

    # Check if backup file exists
    if not backup_file.exists():
        console.print(f"[bold red]Error:[/] Backup file not found: {backup_file}")
        raise typer.Exit(1)

    # Confirm restore will overwrite existing data
    if volume_name:
        confirm = typer.confirm(
            f"Restoring to volume {volume_name} will overwrite all existing data. Continue?",
            default=False,
        )
        if not confirm:
            console.print("[yellow]Operation cancelled.[/]")
            return

    # Restore volume
    status, restored_volume = volume_manager.restore_volume(
        backup_file, volume_name, volume_type
    )

    if status == OperationStatus.SUCCESS and restored_volume:
        console.print(f"[green]Successfully restored to volume {restored_volume}[/]")
    else:
        console.print("[bold red]Failed to restore volume[/]")
        raise typer.Exit(1)


@volume_app.command(name="migrate")
def volume_migrate(
    source: str = typer.Option(..., "--source", "-s", help="Source volume name"),
    target: str = typer.Option(..., "--target", "-t", help="Target volume name"),
    temp_dir: Path = typer.Option(
        Path.home() / ".jfrog" / "temp",
        "--temp",
        help="Temporary directory for migration",
    ),
) -> None:
    """Migrate data from one Artifactory volume to another."""
    volume_manager = VolumeManager(console=console)

    # Confirm migration
    confirm = typer.confirm(
        f"Migrating to volume {target} will overwrite all existing data. Continue?",
        default=False,
    )
    if not confirm:
        console.print("[yellow]Operation cancelled.[/]")
        return

    # Run migration
    success = asyncio.run(volume_manager.migrate_data(source, target, temp_dir))

    if success:
        console.print(f"[green]Successfully migrated data from {source} to {target}[/]")
    else:
        console.print("[bold red]Failed to migrate data[/]")
        raise typer.Exit(1)


@volume_app.command()
def list() -> None:
    """List Docker volumes for Artifactory."""
    console = Console()
    volume_manager = VolumeManager(console=console)
    volume_manager.display_volumes()


@volume_app.command()
def backup(
    name: str = typer.Option(..., "--name", "-n", help="Name of the volume to backup"),
    output_dir: Path = typer.Option(
        Path.cwd() / "backups", "--output", "-o", help="Directory to save backup"
    ),
    compress: bool = typer.Option(
        True, "--compress/--no-compress", help="Compress backup with gzip"
    ),
) -> None:
    """Backup Docker volume for Artifactory."""
    console = Console()
    volume_manager = VolumeManager(console=console)
    status, _ = volume_manager.backup_volume(name, output_dir, compress=compress)
    if status != OperationStatus.SUCCESS:
        raise typer.Exit(1)


@volume_app.command()
def restore(
    file: Path = typer.Option(..., "--file", "-f", help="Backup file to restore from"),
    name: str = typer.Option(
        None,
        "--name",
        "-n",
        help="Name of volume to restore to (optional, will create new if not specified)",
    ),
    type: VolumeType = typer.Option(
        None, "--type", "-t", help="Type of volume to create if name not specified"
    ),
    host_path: Path = typer.Option(
        None, "--host-path", help="Optional host path to bind the new volume to"
    ),
) -> None:
    """Restore Docker volume for Artifactory."""
    console = Console()
    volume_manager = VolumeManager(console=console)
    status, _ = volume_manager.restore_volume(file, name, type, host_path)
    if status != OperationStatus.SUCCESS:
        raise typer.Exit(1)


@volume_app.command()
def create(
    type: VolumeType = typer.Option(
        ..., "--type", "-t", help="Type of volume to create"
    ),
    name_suffix: str = typer.Option(
        None, "--suffix", "-s", help="Suffix for volume name"
    ),
    driver: str = typer.Option("local", "--driver", "-d", help="Docker volume driver"),
    host_path: Path = typer.Option(
        None, "--host-path", "-p", help="Host path to bind volume to"
    ),
    size: str = typer.Option(None, "--size", help="Size for volume (e.g. '10G')"),
    display_name: str = typer.Option(
        None, "--display-name", help="Human-readable name for the volume"
    ),
) -> None:
    """Create Docker volume for Artifactory."""
    console = Console()
    volume_manager = VolumeManager(console=console)

    driver_opts = {"size": size} if size else None

    try:
        volume_name = volume_manager.create_volume(
            type,
            name_suffix,
            driver=driver,
            driver_opts=driver_opts,
            host_path=host_path,
            display_name=display_name,
        )
        console.print(f"[green]Created volume:[/] {volume_name}")
    except Exception as e:
        console.print(f"[bold red]Failed to create volume:[/] {e}")
        raise typer.Exit(1)


@volume_app.command()
def migrate(
    source: str = typer.Option(..., "--source", "-s", help="Source volume name"),
    target: str = typer.Option(..., "--target", "-t", help="Target volume name"),
    temp_dir: Path = typer.Option(
        Path.cwd() / "temp", "--temp-dir", help="Temporary directory for migration"
    ),
) -> None:
    """Migrate data between Docker volumes."""
    console = Console()
    volume_manager = VolumeManager(console=console)

    success = asyncio.run(volume_manager.migrate_data(source, target, temp_dir))
    if not success:
        console.print("[bold red]Migration failed[/]")
        raise typer.Exit(1)


@volume_app.command()
def import_path(
    source_path: Path = typer.Option(
        ..., "--source", "-s", help="Source directory path"
    ),
    volume_type: VolumeType = typer.Option(
        ..., "--type", "-t", help="Type of volume to create"
    ),
    name_suffix: str = typer.Option(None, "--suffix", help="Suffix for volume name"),
    driver: str = typer.Option("local", "--driver", "-d", help="Docker volume driver"),
) -> None:
    """Import data from a host path into a Docker volume."""
    console = Console()
    volume_manager = VolumeManager(console=console)

    # Create the target volume
    try:
        target_volume = volume_manager.create_volume(
            volume_type,
            name_suffix
            or f"imported_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            driver=driver,
            display_name=f"Imported {volume_type.value} from {source_path.name}",
        )

        # Migrate data from path to volume
        success = asyncio.run(
            volume_manager.migrate_from_bind_mount(
                source_path, target_volume, volume_type
            )
        )

        if not success:
            console.print("[bold red]Import failed[/]")
            volume_manager.delete_volume(target_volume, force=True)
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[bold red]Failed to import data:[/] {e}")
        raise typer.Exit(1)


@volume_app.command()
def analyze(
    name: str = typer.Option(..., "--name", "-n", help="Name of the volume to analyze"),
) -> None:
    """Analyze data usage in a Docker volume."""
    console = Console()
    volume_manager = VolumeManager(console=console)

    result = volume_manager.analyze_data_usage(name)
    if "error" in result:
        console.print(f"[bold red]Analysis failed:[/] {result['error']}")
        raise typer.Exit(1)
