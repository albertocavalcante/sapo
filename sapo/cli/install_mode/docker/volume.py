"""Docker volume management for Artifactory installations.

This module provides functionality to create, manage, backup, and migrate
Artifactory data between Docker volumes.
"""

import subprocess
import datetime
import os
import json
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Union

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..common import OperationStatus


class VolumeType(str, Enum):
    """Types of volumes used by Artifactory."""

    DATA = "data"
    LOGS = "logs"
    BACKUP = "backup"
    POSTGRESQL = "postgresql"
    ETC = "etc"  # Added etc as a proper volume type
    ALL = "all"


class VolumeManager:
    """Manages Docker volumes for Artifactory."""

    def __init__(
        self,
        console: Optional[Console] = None,
        volume_prefix: str = "artifactory",
    ):
        """Initialize volume manager.

        Args:
            console: Console for output
            volume_prefix: Prefix for volume names
        """
        self.console = console or Console()
        self.volume_prefix = volume_prefix
        self.default_labels = {
            "com.jfrog.artifactory.managed-by": "sapo",
            "com.jfrog.artifactory.created-at": datetime.datetime.now().isoformat(),
        }

    def _run_command(
        self, cmd: List[str], check: bool = True, capture_output: bool = True
    ) -> subprocess.CompletedProcess:
        """Run a command and return the result.

        Args:
            cmd: Command to run
            check: Whether to check return code
            capture_output: Whether to capture output

        Returns:
            subprocess.CompletedProcess: Command result

        Raises:
            subprocess.CalledProcessError: If command fails and check is True
        """
        try:
            return subprocess.run(
                cmd, check=check, capture_output=capture_output, text=True
            )
        except subprocess.CalledProcessError as e:
            self.console.print(f"[bold red]Command failed:[/] {' '.join(cmd)}")
            self.console.print(f"[red]Error:[/] {e}")
            raise

    def is_docker_available(self) -> bool:
        """Check if Docker is available.

        Returns:
            bool: True if Docker is available
        """
        try:
            self._run_command(["docker", "--version"])
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            self.console.print(
                "[bold red]Error:[/] Docker not found. Please install Docker and try again."
            )
            return False

    def list_volumes(self) -> List[Dict[str, str]]:
        """List all Artifactory volumes.

        Returns:
            List[Dict[str, str]]: List of volumes
        """
        if not self.is_docker_available():
            return []

        try:
            result = self._run_command(
                [
                    "docker",
                    "volume",
                    "ls",
                    "--filter",
                    f"name={self.volume_prefix}",
                    "--format",
                    "{{.Name}},{{.Driver}},{{.Mountpoint}}",
                ]
            )

            volumes = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split(",")
                if len(parts) >= 3:
                    name, driver, mountpoint = parts
                    volumes.append(
                        {"name": name, "driver": driver, "mountpoint": mountpoint}
                    )
            return volumes
        except Exception as e:
            self.console.print(f"[red]Error listing volumes: {e}[/]")
            return []

    def create_volume(
        self,
        volume_type: VolumeType,
        name_suffix: Optional[str] = None,
        driver: Optional[str] = None,
        driver_opts: Optional[Dict[str, str]] = None,
        labels: Optional[Dict[str, str]] = None,
        host_path: Optional[Path] = None,
        display_name: Optional[str] = None,
    ) -> str:
        """Create a new volume for Artifactory.

        Args:
            volume_type: Type of volume to create
            name_suffix: Optional suffix for volume name
            driver: Docker volume driver
            driver_opts: Driver options
            labels: Custom labels for the volume
            host_path: Optional explicit host path to bind to
            display_name: Optional human-readable name for the volume

        Returns:
            str: Name of created volume
        """
        if not self.is_docker_available():
            raise RuntimeError("Docker is not available")

        # Generate volume name with timestamp if suffix not provided
        if not name_suffix:
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            name_suffix = timestamp

        volume_name = f"{self.volume_prefix}_{volume_type.value}_{name_suffix}"

        cmd = ["docker", "volume", "create", volume_name]

        # Add driver if specified
        if driver:
            cmd.extend(["--driver", driver])

        # Handle explicit host path binding
        if host_path:
            # Make sure the path exists
            os.makedirs(host_path, exist_ok=True)

            # Create driver options if not provided
            if not driver_opts:
                driver_opts = {}

            # Set up bind mount options
            driver_opts.update(
                {"type": "none", "o": "bind", "device": str(host_path.absolute())}
            )

            # Make sure we're using local driver with host path
            if not driver:
                cmd.extend(["--driver", "local"])
            elif driver != "local":
                self.console.print(
                    "[yellow]Warning: Using non-local driver with host path may not work as expected"
                )

        # Add driver options if specified
        if driver_opts:
            for key, value in driver_opts.items():
                cmd.extend(["--opt", f"{key}={value}"])

        # Prepare labels
        all_labels = self.default_labels.copy()

        # Add volume type and purpose
        all_labels["com.jfrog.artifactory.volume-type"] = volume_type.value
        all_labels["com.jfrog.artifactory.purpose"] = self._get_purpose_for_type(
            volume_type
        )

        # Add display name if provided
        if display_name:
            all_labels["com.jfrog.artifactory.display-name"] = display_name

        # Add custom labels
        if labels:
            all_labels.update(labels)

        # Add labels to command
        for key, value in all_labels.items():
            cmd.extend(["--label", f"{key}={value}"])

        try:
            self._run_command(cmd)
            self.console.print(f"[green]Created volume:[/] {volume_name}")
            return volume_name
        except Exception as e:
            self.console.print(f"[bold red]Failed to create volume:[/] {e}")
            raise

    def _get_purpose_for_type(self, volume_type: VolumeType) -> str:
        """Get a human-readable purpose for a volume type.

        Args:
            volume_type: Volume type

        Returns:
            str: Human-readable purpose
        """
        purposes = {
            VolumeType.DATA: "Artifactory data storage",
            VolumeType.LOGS: "Artifactory logs",
            VolumeType.BACKUP: "Artifactory backup storage",
            VolumeType.POSTGRESQL: "PostgreSQL database storage",
            VolumeType.ETC: "Artifactory configuration",
            VolumeType.ALL: "All Artifactory data",
        }
        return purposes.get(volume_type, "Unknown purpose")

    def delete_volume(self, volume_name: str, force: bool = False) -> bool:
        """Delete a volume.

        Args:
            volume_name: Name of volume to delete
            force: Whether to force deletion

        Returns:
            bool: True if deletion was successful
        """
        if not self.is_docker_available():
            return False

        cmd = ["docker", "volume", "rm"]
        if force:
            cmd.append("--force")
        cmd.append(volume_name)

        try:
            self._run_command(cmd)
            self.console.print(f"[green]Deleted volume:[/] {volume_name}")
            return True
        except Exception as e:
            self.console.print(f"[bold red]Failed to delete volume:[/] {e}")
            return False

    def backup_volume(
        self, volume_name: str, backup_path: Path, compress: bool = False
    ) -> Tuple[OperationStatus, Optional[Path]]:
        """Backup a volume to a tar file.

        Args:
            volume_name: Name of volume to backup
            backup_path: Directory to save backup
            compress: Whether to compress the backup with gzip

        Returns:
            Tuple[OperationStatus, Optional[Path]]: Status and path to backup file
        """
        if not self.is_docker_available():
            return OperationStatus.ERROR, None

        backup_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

        # Use .tar.gz extension if compressing
        if compress:
            backup_file = backup_path / f"{volume_name}_{timestamp}.tar.gz"
        else:
            backup_file = backup_path / f"{volume_name}_{timestamp}.tar"

        self.console.print(
            f"[bold]Backing up volume {volume_name} to {backup_file}...[/]"
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task(f"Backing up {volume_name}...", total=None)

            try:
                # Create a temporary container that mounts the volume and tar its contents
                tar_command = "tar"
                if compress:
                    tar_command += " -czf"  # Compress with gzip
                else:
                    tar_command += " -cf"

                self._run_command(
                    [
                        "docker",
                        "run",
                        "--rm",
                        "-v",
                        f"{volume_name}:/source",
                        "-v",
                        f"{backup_file.parent}:/backup",
                        "alpine",
                        "sh",
                        "-c",
                        f"{tar_command} /backup/{backup_file.name} -C /source .",
                    ]
                )

                # Also include volume metadata
                volume_info = self.get_volume_info(volume_name)
                if volume_info:
                    metadata_file = (
                        backup_path / f"{volume_name}_{timestamp}_metadata.json"
                    )
                    with open(metadata_file, "w") as f:
                        json.dump(volume_info, f, indent=2)

                    self.console.print(
                        f"[green]Volume metadata saved to:[/] {metadata_file}"
                    )

                progress.update(
                    task, completed=100, description=f"Backup completed: {backup_file}"
                )
                self.console.print(f"[green]Volume backup completed:[/] {backup_file}")
                return OperationStatus.SUCCESS, backup_file

            except Exception as e:
                progress.update(task, description=f"Backup failed: {e}")
                self.console.print(f"[bold red]Failed to backup volume:[/] {e}")
                return OperationStatus.ERROR, None

    def restore_volume(
        self,
        backup_file: Path,
        volume_name: Optional[str] = None,
        volume_type: Optional[VolumeType] = None,
        host_path: Optional[Path] = None,
    ) -> Tuple[OperationStatus, Optional[str]]:
        """Restore a volume from a backup file.

        Args:
            backup_file: Path to backup file
            volume_name: Name of volume to restore to (will create new if None)
            volume_type: Type of volume (required if volume_name is None)
            host_path: Optional host path to bind the new volume to

        Returns:
            Tuple[OperationStatus, Optional[str]]: Status and name of volume
        """
        if not self.is_docker_available():
            return OperationStatus.ERROR, None

        if not backup_file.exists():
            self.console.print(
                f"[bold red]Error:[/] Backup file not found: {backup_file}"
            )
            return OperationStatus.ERROR, None

        # Check if the backup is compressed
        is_compressed = backup_file.name.endswith(".gz") or backup_file.name.endswith(
            ".tgz"
        )

        # Create new volume if name not provided
        if not volume_name:
            if not volume_type:
                self.console.print(
                    "[bold red]Error:[/] Either volume_name or volume_type must be provided"
                )
                return OperationStatus.ERROR, None

            try:
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                display_name = f"Restored {volume_type.value} ({timestamp})"

                # Extract original volume name from backup filename for labels
                original_name = backup_file.name.split("_")[0]

                # Add metadata about restore operation
                labels = {
                    "com.jfrog.artifactory.restored-from": original_name,
                    "com.jfrog.artifactory.restored-at": datetime.datetime.now().isoformat(),
                    "com.jfrog.artifactory.backup-file": backup_file.name,
                }

                # Create the volume with host path if specified
                volume_name = self.create_volume(
                    volume_type,
                    f"restored_{timestamp}",
                    host_path=host_path,
                    labels=labels,
                    display_name=display_name,
                )
            except Exception as e:
                self.console.print(
                    f"[bold red]Failed to create new volume for restore:[/] {e}"
                )
                return OperationStatus.ERROR, None

        self.console.print(
            f"[bold]Restoring {backup_file} to volume {volume_name}...[/]"
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task(f"Restoring to {volume_name}...", total=None)

            try:
                # Use correct tar command based on compression
                tar_command = "tar -xf"
                if is_compressed:
                    tar_command = "tar -xzf"  # Extract gzipped tar

                # Create a temporary container that mounts the volume and extracts the tar
                self._run_command(
                    [
                        "docker",
                        "run",
                        "--rm",
                        "-v",
                        f"{volume_name}:/target",
                        "-v",
                        f"{backup_file.parent}:/backup",
                        "alpine",
                        "sh",
                        "-c",
                        f"rm -rf /target/* /target/.[!.]* && {tar_command} /backup/{backup_file.name} -C /target",
                    ]
                )

                progress.update(
                    task,
                    completed=100,
                    description=f"Restore completed to {volume_name}",
                )
                self.console.print(
                    f"[green]Volume restore completed to:[/] {volume_name}"
                )
                return OperationStatus.SUCCESS, volume_name

            except Exception as e:
                progress.update(task, description=f"Restore failed: {e}")
                self.console.print(f"[bold red]Failed to restore volume:[/] {e}")
                return OperationStatus.ERROR, None

    def get_volume_info(self, volume_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a volume.

        Args:
            volume_name: Name of volume

        Returns:
            Optional[Dict[str, Any]]: Volume information or None if not found
        """
        if not self.is_docker_available():
            return None

        try:
            result = self._run_command(["docker", "volume", "inspect", volume_name])

            import json

            volumes = json.loads(result.stdout)
            if volumes and len(volumes) > 0:
                return volumes[0]
            return None
        except Exception:
            return None

    def get_volume_size(self, volume_name: str) -> Optional[Tuple[float, str]]:
        """Get the size of a volume in human-readable format.

        Args:
            volume_name: Name of volume

        Returns:
            Optional[Tuple[float, str]]: Size in bytes and human-readable format
        """
        if not self.is_docker_available():
            return None

        try:
            volume_info = self.get_volume_info(volume_name)
            if not volume_info or "Mountpoint" not in volume_info:
                return None

            # Run du command in container to get size
            result = self._run_command(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{volume_name}:/volume",
                    "alpine",
                    "du",
                    "-sb",
                    "/volume",
                ]
            )

            # Parse output like "12345 /volume"
            size_str = result.stdout.strip().split()[0]
            size_bytes = int(size_str)

            # Convert to human-readable format
            units = ["B", "KB", "MB", "GB", "TB"]
            size_human = size_bytes
            unit_index = 0

            while size_human > 1024 and unit_index < len(units) - 1:
                size_human /= 1024
                unit_index += 1

            return (size_bytes, f"{size_human:.2f} {units[unit_index]}")
        except Exception as e:
            self.console.print(f"[yellow]Could not determine volume size: {e}[/]")
            return None

    def display_volumes(self) -> None:
        """Display information about all Artifactory volumes."""
        volumes = self.list_volumes()

        if not volumes:
            self.console.print("[yellow]No Artifactory volumes found.[/]")
            return

        table = Table(title="Artifactory Docker Volumes")
        table.add_column("Name", style="cyan")
        table.add_column("Driver", style="green")
        table.add_column("Size", style="magenta")
        table.add_column("Type", style="yellow")
        table.add_column("Mountpoint", style="blue")

        for volume in volumes:
            name = volume["name"]
            driver = volume["driver"]
            mountpoint = volume["mountpoint"]

            # Get volume size
            size_info = self.get_volume_size(name)
            size = size_info[1] if size_info else "Unknown"

            # Get volume info to determine type
            volume_info = self.get_volume_info(name)
            volume_type = "Unknown"
            if volume_info and "Labels" in volume_info:
                labels = volume_info["Labels"]
                if "com.jfrog.artifactory.volume-type" in labels:
                    volume_type = labels["com.jfrog.artifactory.volume-type"]

            table.add_row(name, driver, size, volume_type, mountpoint)

        self.console.print(table)

    def create_volume_set(
        self,
        name_suffix: Optional[str] = None,
        driver: Optional[str] = None,
        size_opts: Optional[Dict[Union[VolumeType, str], Dict[str, str]]] = None,
        host_paths: Optional[Dict[Union[VolumeType, str], Path]] = None,
        labels: Optional[Dict[str, str]] = None,
        artifactory_version: Optional[str] = None,
    ) -> Dict[VolumeType, str]:
        """Create a complete set of volumes for Artifactory.

        Args:
            name_suffix: Optional suffix for volume names
            driver: Docker volume driver
            size_opts: Size options for volumes (e.g. {"size": "10G"})
            host_paths: Optional map of volume types to host paths
            labels: Additional labels to apply to all volumes
            artifactory_version: Optional Artifactory version for labeling

        Returns:
            Dict[VolumeType, str]: Map of volume types to volume names
        """
        if not name_suffix:
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            name_suffix = timestamp

        volumes = {}

        # Create base labels
        all_labels = {}
        if labels:
            all_labels.update(labels)

        # Add Artifactory version label if provided
        if artifactory_version:
            all_labels["com.jfrog.artifactory.version"] = artifactory_version

        # Add installation timestamp
        all_labels["com.jfrog.artifactory.install-timestamp"] = (
            datetime.datetime.now().isoformat()
        )

        # Create default size options if not provided
        if not size_opts:
            size_opts = {
                VolumeType.DATA: {"size": "50G"},
                VolumeType.LOGS: {"size": "10G"},
                VolumeType.BACKUP: {"size": "20G"},
                VolumeType.POSTGRESQL: {"size": "20G"},
                VolumeType.ETC: {"size": "1G"},
            }

        # Normalize host_paths if provided (to handle string keys)
        normalized_host_paths = {}
        if host_paths:
            for key, path in host_paths.items():
                if isinstance(key, str):
                    try:
                        normalized_host_paths[VolumeType(key)] = path
                    except ValueError:
                        self.console.print(
                            f"[yellow]Warning: Unknown volume type '{key}', skipping host path[/]"
                        )
                else:
                    normalized_host_paths[key] = path

        # Create each volume type
        for volume_type in [
            VolumeType.DATA,
            VolumeType.LOGS,
            VolumeType.BACKUP,
            VolumeType.POSTGRESQL,
            VolumeType.ETC,
        ]:
            try:
                # Prepare display name
                display_name = f"Artifactory {volume_type.value}"
                if artifactory_version:
                    display_name += f" ({artifactory_version})"

                # Get host path if specified
                host_path = None
                if normalized_host_paths and volume_type in normalized_host_paths:
                    host_path = normalized_host_paths[volume_type]

                # Get driver options for this volume type
                driver_opts = None
                if driver and driver != "local" and size_opts:
                    if isinstance(size_opts, dict):
                        # Handle both string and enum keys
                        if volume_type in size_opts:
                            driver_opts = size_opts[volume_type]
                        elif volume_type.value in size_opts:
                            driver_opts = size_opts[volume_type.value]
                        elif "size" in size_opts:
                            driver_opts = {"size": size_opts["size"]}

                # Create the volume
                volume_name = self.create_volume(
                    volume_type,
                    name_suffix,
                    driver=driver,
                    driver_opts=driver_opts,
                    labels=all_labels,
                    host_path=host_path,
                    display_name=display_name,
                )
                volumes[volume_type] = volume_name

            except Exception as e:
                self.console.print(
                    f"[bold red]Failed to create volume for {volume_type.value}:[/] {e}"
                )

                # Clean up created volumes on failure
                for created_type, created_name in volumes.items():
                    self.console.print(
                        f"[yellow]Cleaning up volume {created_name}...[/]"
                    )
                    self.delete_volume(created_name, force=True)

                raise RuntimeError(f"Failed to create volume set: {e}")

        return volumes

    def generate_compose_volumes(
        self, volumes: Dict[VolumeType, str]
    ) -> Dict[str, Dict[str, str]]:
        """Generate volume configuration for docker-compose.yml.

        Args:
            volumes: Map of volume types to volume names

        Returns:
            Dict[str, Dict[str, str]]: Volume configuration for docker-compose
        """
        compose_volumes = {}

        for volume_type, volume_name in volumes.items():
            compose_volumes[volume_name] = {"external": True}

        return compose_volumes

    async def migrate_data(
        self, source_volume: str, target_volume: str, temp_dir: Path
    ) -> bool:
        """Migrate data from one volume to another.

        Args:
            source_volume: Source volume name
            target_volume: Target volume name
            temp_dir: Temporary directory for backup

        Returns:
            bool: True if migration was successful
        """
        self.console.print(
            f"[bold]Migrating data from {source_volume} to {target_volume}...[/]"
        )

        # Create temporary directory
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Backup source volume
        status, backup_file = self.backup_volume(source_volume, temp_dir, compress=True)
        if status != OperationStatus.SUCCESS or not backup_file:
            self.console.print("[bold red]Failed to backup source volume.[/]")
            return False

        # Restore to target volume
        status, _ = self.restore_volume(backup_file, target_volume)
        if status != OperationStatus.SUCCESS:
            self.console.print("[bold red]Failed to restore to target volume.[/]")
            return False

        self.console.print(
            f"[green]Successfully migrated data from {source_volume} to {target_volume}[/]"
        )

        # Clean up backup file
        try:
            backup_file.unlink()
            self.console.print(
                f"[green]Removed temporary backup file: {backup_file}[/]"
            )
        except Exception as e:
            self.console.print(
                f"[yellow]Could not remove temporary backup file: {e}[/]"
            )

        return True

    async def migrate_from_bind_mount(
        self, source_path: Path, target_volume: str, volume_type: VolumeType
    ) -> bool:
        """Migrate data from a bind mount to a Docker volume.

        Args:
            source_path: Path to the bind mount
            target_volume: Target volume name
            volume_type: Type of volume

        Returns:
            bool: True if migration was successful
        """
        if not self.is_docker_available():
            return False

        if not source_path.exists():
            self.console.print(
                f"[bold red]Error:[/] Source path does not exist: {source_path}"
            )
            return False

        self.console.print(
            f"[bold]Migrating from {source_path} to volume {target_volume}...[/]"
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task(f"Migrating to {target_volume}...", total=None)

            try:
                # Create a temporary container to copy data from host to volume
                self._run_command(
                    [
                        "docker",
                        "run",
                        "--rm",
                        "-v",
                        f"{target_volume}:/target",
                        "-v",
                        f"{source_path.absolute()}:/source",
                        "alpine",
                        "sh",
                        "-c",
                        "cp -a /source/. /target/",
                    ]
                )

                # Update volume labels to indicate migration source
                labels = {
                    "com.jfrog.artifactory.migrated-from": str(source_path),
                    "com.jfrog.artifactory.migrated-at": datetime.datetime.now().isoformat(),
                }

                # Apply labels to volume
                for key, value in labels.items():
                    try:
                        self._run_command(
                            [
                                "docker",
                                "volume",
                                "label",
                                "add",
                                target_volume,
                                f"{key}={value}",
                            ],
                            check=False,
                        )
                    except Exception:
                        # Docker volume label is not supported in older Docker versions, so ignore errors
                        pass

                progress.update(
                    task,
                    completed=100,
                    description=f"Migration completed to {target_volume}",
                )
                self.console.print(
                    f"[green]Successfully migrated data to volume {target_volume}[/]"
                )
                return True

            except Exception as e:
                progress.update(task, description=f"Migration failed: {e}")
                self.console.print(f"[bold red]Failed to migrate data:[/] {e}")
                return False

    def analyze_data_usage(self, volume_name: str) -> Dict[str, Any]:
        """Analyze the data usage within a volume.

        Args:
            volume_name: Name of volume to analyze

        Returns:
            Dict[str, Any]: Analysis results
        """
        if not self.is_docker_available():
            return {"error": "Docker not available"}

        self.console.print(f"[bold]Analyzing data usage in volume {volume_name}...[/]")

        try:
            # Run du command in container to get directory sizes
            result = self._run_command(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{volume_name}:/volume",
                    "alpine",
                    "sh",
                    "-c",
                    "du -sh /volume/* /volume/.[!.]* 2>/dev/null || true",
                ]
            )

            # Parse the results
            usage_data = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.strip().split()
                if len(parts) >= 2:
                    size, path = parts[0], parts[1]
                    path_name = Path(path).name
                    usage_data.append({"path": path_name, "size": size})

            # Get total size
            total_size_info = self.get_volume_size(volume_name)
            total_size = total_size_info[1] if total_size_info else "Unknown"

            # Display results
            table = Table(title=f"Data Usage Analysis for {volume_name}")
            table.add_column("Directory/File", style="cyan")
            table.add_column("Size", style="magenta")

            for item in usage_data:
                table.add_row(item["path"], item["size"])

            self.console.print(table)
            self.console.print(f"[bold]Total volume size:[/] {total_size}")

            # Return analysis data
            return {
                "volume": volume_name,
                "total_size": total_size,
                "usage_data": usage_data,
            }

        except Exception as e:
            self.console.print(f"[bold red]Failed to analyze data usage:[/] {e}")
            return {"error": str(e)}

    def create_bind_mount_spec(
        self, host_path: Path, container_path: str
    ) -> Dict[str, Any]:
        """Create a bind mount specification for docker-compose.

        Args:
            host_path: Path on host to mount
            container_path: Path in container to mount to

        Returns:
            Dict[str, Any]: Mount specification
        """
        # Ensure the host path exists
        host_path.mkdir(parents=True, exist_ok=True)

        return {
            "type": "bind",
            "source": str(host_path.absolute()),
            "target": container_path,
        }

    def get_volume_labels(self, volume_name: str) -> Dict[str, str]:
        """Get the labels of a volume.

        Args:
            volume_name: Name of volume

        Returns:
            Dict[str, str]: Volume labels
        """
        info = self.get_volume_info(volume_name)
        if not info or "Labels" not in info:
            return {}

        return info["Labels"]
