"""File generation and management for Docker installation."""

import platform
import shutil
from enum import Enum
from pathlib import Path

from rich.console import Console

from ..common import OperationStatus
from ..common.directory_utils import create_artifactory_structure
from ..common.file_utils import FileOperationResult, safe_write_file
from ..common.system_utils import set_directory_permissions
from ..templates import render_template_from_file
from .config import DockerConfig


class FileType(str, Enum):
    """Types of files generated for Docker installation."""

    ENV = "env"
    DOCKER_COMPOSE = "docker_compose"
    SYSTEM_YAML = "system_yaml"


class DockerFileManager:
    """Manages Docker installation files."""

    def __init__(
        self,
        config: DockerConfig,
        console: Console | None = None,
        use_named_volumes: bool = False,
        volume_names: dict[str, str] | None = None,
    ):
        self.config = config
        self.console = console or Console()
        self.use_named_volumes = use_named_volumes
        self.volume_names = volume_names or {}

    def generate_all_files(
        self, non_interactive: bool = False
    ) -> dict[FileType, FileOperationResult]:
        """Generate all files needed for Docker installation.

        Args:
            non_interactive: Whether to skip confirmation prompts

        Returns:
            Dict[FileType, FileOperationResult]: Results for each file type
        """
        # Create directories (not needed if using named volumes, but create for config files)
        self.create_directories()

        # Generate files
        self.console.print(f"[bold]Generating files in {self.config.output_dir}...[/]")

        results = {}
        results[FileType.ENV] = self._generate_env_file(non_interactive)
        results[FileType.DOCKER_COMPOSE] = self._generate_docker_compose(
            non_interactive
        )
        results[FileType.SYSTEM_YAML] = self._generate_system_yaml(non_interactive)

        # Set permissions if not using named volumes
        if not self.use_named_volumes:
            self._set_permissions(non_interactive)

        return results

    def create_directories(self) -> dict[str, Path]:
        """Create all necessary directories.

        Returns:
            Dict[str, Path]: Map of directory names to paths
        """
        # Create output directory
        if self.config.output_dir is not None:
            self.config.output_dir.mkdir(parents=True, exist_ok=True)

        # If using named volumes, we only need to ensure the etc directory exists for system.yaml
        if self.use_named_volumes:
            etc_path = self.config.data_dir / "etc"
            etc_path.mkdir(parents=True, exist_ok=True)
            return {"etc": etc_path}

        # Create Artifactory directories for bind mounts
        directories = create_artifactory_structure(self.config.data_dir)

        # Create PostgreSQL directory structure if needed
        if self.config.use_postgres:
            pg_dir = self.config.data_dir / "postgresql"
            pg_dir.mkdir(exist_ok=True)
            pg_data_dir = pg_dir / "data"
            pg_data_dir.mkdir(exist_ok=True)
            directories["postgresql"] = pg_dir
            directories["postgresql_data"] = pg_data_dir

            # Set permissions (PostgreSQL requires proper owner)
            self.console.print(
                "[yellow]Setting directory permissions for PostgreSQL...[/]"
            )
            try:
                # Make PostgreSQL data directory writable for all users (needed for Docker)
                pg_data_dir.chmod(0o777)
                self.console.print(
                    "[green]Successfully set PostgreSQL directory permissions[/]"
                )
            except Exception as e:
                self.console.print(
                    f"[yellow]Warning: Could not set PostgreSQL directory permissions: {e}[/]"
                )

        return directories

    def _generate_env_file(self, non_interactive: bool = False) -> FileOperationResult:
        """Generate .env file.

        Args:
            non_interactive: Whether to skip confirmation prompts

        Returns:
            FileOperationResult: Result of the operation
        """
        if self.config.output_dir is None:
            raise ValueError("output_dir must be set before generating files")
        env_content = render_template_from_file(
            "docker",
            "env.j2",
            {
                "artifactory_version": self.config.version,
                "data_dir": str(self.config.data_dir.absolute()),
                "external_port": self.config.port,
                "postgres_user": self.config.postgres_user,
                "postgres_password": self.config.generate_password("postgres"),
                "postgres_db": self.config.postgres_db,
                "use_postgres": self.config.use_postgres,
                "joinkey": self.config.generate_joinkey(),
            },
        )

        result = safe_write_file(
            self.config.output_dir / ".env", env_content, non_interactive
        )

        if not result.success:
            self.console.print("[bold red]Failed to create .env file[/]")

        return result

    def _generate_docker_compose(
        self, non_interactive: bool = False
    ) -> FileOperationResult:
        """Generate docker-compose.yml file.

        Args:
            non_interactive: Whether to skip confirmation prompts

        Returns:
            FileOperationResult: Result of the operation
        """
        if self.config.output_dir is None:
            raise ValueError("output_dir must be set before generating files")
        # System YAML check
        system_yaml_exists = (self.config.data_dir / "etc" / "system.yaml").exists()

        # Setup template context
        template_context = {
            "docker_registry": "releases-docker.jfrog.io",
            "artifactory_version": self.config.version,
            "external_port": self.config.port,
            "data_dir": str(self.config.data_dir.absolute()),
            "postgres_user": self.config.postgres_user,
            "postgres_password": self.config.get_password("postgres"),
            "postgres_db": self.config.postgres_db,
            "db_type": "postgresql" if self.config.use_postgres else "derby",
            "use_postgres": self.config.use_postgres,
            "joinkey": self.config.joinkey,
            "use_named_volumes": self.use_named_volumes,
            "system_yaml_exists": system_yaml_exists,
        }

        # Add volume names if using named volumes
        if self.use_named_volumes:
            template_context.update(
                {
                    "data_volume_name": self.volume_names.get(
                        "data", "artifactory_data"
                    ),
                    "logs_volume_name": self.volume_names.get(
                        "logs", "artifactory_logs"
                    ),
                    "etc_volume_name": self.volume_names.get("etc", "artifactory_etc"),
                    "postgres_volume_name": self.volume_names.get(
                        "postgresql", "artifactory_postgresql"
                    ),
                }
            )

            # Only include backup volume name if it actually exists
            if "backup" in self.volume_names:
                template_context["backup_volume_name"] = self.volume_names["backup"]

        docker_compose_content = render_template_from_file(
            "docker", "docker-compose.yml.j2", template_context
        )

        result = safe_write_file(
            self.config.output_dir / "docker-compose.yml",
            docker_compose_content,
            non_interactive,
        )

        if not result.success:
            self.console.print("[bold red]Failed to create docker-compose.yml file[/]")

        return result

    def _generate_system_yaml(
        self, non_interactive: bool = False
    ) -> FileOperationResult:
        """Generate system.yaml file.

        Args:
            non_interactive: Whether to skip confirmation prompts

        Returns:
            FileOperationResult: Result of the operation
        """
        if self.config.output_dir is None:
            raise ValueError("output_dir must be set before generating files")
        system_yaml_content = render_template_from_file(
            "docker",
            "system.yaml.j2",
            {
                "use_postgres": self.config.use_postgres,
                "postgres_user": self.config.postgres_user,
                "postgres_password": self.config.get_password("postgres"),
                "postgres_db": self.config.postgres_db,
                "joinkey": self.config.generate_joinkey(),
                "platform": platform.system(),
            },
        )

        # Make sure the etc directory exists
        etc_dir = self.config.data_dir / "etc"
        etc_dir.mkdir(parents=True, exist_ok=True)

        # If system.yaml is somehow a directory, remove it (common issue causing failures)
        system_yaml_path = etc_dir / "system.yaml"
        if system_yaml_path.exists() and system_yaml_path.is_dir():
            try:
                shutil.rmtree(system_yaml_path)
                self.console.print(
                    "[yellow]Removed system.yaml directory to create file[/]"
                )
            except Exception as e:
                self.console.print(
                    f"[bold red]Error: Could not remove system.yaml directory: {e}[/]"
                )
                return FileOperationResult(
                    status=OperationStatus.ERROR,
                    path=system_yaml_path,
                    message=f"Failed to remove directory: {str(e)}",
                )

        # Write to etc directory first (main location)
        main_result = safe_write_file(
            system_yaml_path, system_yaml_content, non_interactive
        )

        if not main_result.success:
            self.console.print(
                "[bold red]Failed to create system.yaml file in etc directory[/]"
            )
            return main_result

        # Also write to output dir for reference
        ref_result = safe_write_file(
            self.config.output_dir / "system.yaml", system_yaml_content, non_interactive
        )

        if not ref_result.success:
            self.console.print(
                "[yellow]Note: Failed to create reference copy of system.yaml[/]"
            )

        return main_result

    def _set_permissions(self, non_interactive: bool = False) -> None:
        """Set appropriate permissions on directories.

        Args:
            non_interactive: Whether to skip confirmation prompts
        """
        # Skip permission setting for named volumes (managed by Docker)
        if self.use_named_volumes:
            self.console.print(
                "[yellow]Using named Docker volumes - skipping host permission setup[/]"
            )
            return

        self.console.print(
            "[yellow]Setting appropriate permissions for Artifactory directories...[/]"
        )

        status, message = set_directory_permissions(
            self.config.data_dir,
            "1030:1030",  # Artifactory user in container
            non_interactive,
        )

        if status == OperationStatus.SUCCESS:
            self.console.print(
                "[green]Successfully set permissions on Artifactory directories[/]"
            )
        elif status == OperationStatus.WARNING:
            self.console.print(f"[yellow]Warning: {message}[/]")
        elif status == OperationStatus.ERROR:
            self.console.print(f"[bold red]Error setting permissions: {message}[/]")
            self.console.print("[yellow]You may need to manually set permissions:[/]")
            self.console.print(
                f"[yellow]sudo chown -R 1030:1030 {self.config.data_dir}[/]"
            )
            if platform.system() == "Darwin":  # macOS
                self.console.print(
                    f"[yellow]sudo chmod -R 777 {self.config.data_dir}[/]"
                )
        else:
            self.console.print(
                "[yellow]Permissions must be set manually as described above[/]"
            )
