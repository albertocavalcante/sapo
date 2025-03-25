"""JFrog Artifactory OSS installer module."""

from pathlib import Path
from typing import Optional

import requests
from pydantic import BaseModel, ConfigDict
from rich.console import Console
import typer
import semver

from .archive import extract_archive
from .checksum import verify_checksum
from .cleanup import register_temp_file, setup_signal_handlers
from .download import download_file
from .platform import Platform, get_current_platform

console = Console()


class ArtifactoryPackage(BaseModel):
    """Model representing an Artifactory package."""

    model_config = ConfigDict(frozen=True)

    version: str
    platform: Platform
    size: Optional[str] = None

    @property
    def filename(self) -> str:
        """Get the filename for the package."""
        extension = "zip" if self.platform == Platform.WINDOWS else "tar.gz"
        return f"jfrog-artifactory-oss-{self.version}-{self.platform.value}.{extension}"


def get_default_dest_dir(platform: Platform) -> Path:
    """
    Get the default destination directory based on the platform.

    Args:
        platform: The target platform

    Returns:
        Path: The default destination directory
    """
    home = Path.home()
    if platform == Platform.WINDOWS:
        return home / "AppData" / "Local" / "Programs" / "Artifactory"
    return home / "dev" / "tools"


class ArtifactoryConfig:
    """Configuration for Artifactory installation."""

    def __init__(
        self,
        version: str,
        platform: Optional[Platform] = None,
        dest_dir: Optional[Path] = None,
        keep_archive: bool = False,
        verify_checksum: bool = True,
    ):
        """
        Initialize Artifactory configuration.

        Args:
            version: Artifactory version to install
            platform: Platform to download for
            dest_dir: Destination directory
            keep_archive: Whether to keep the downloaded archive
            verify_checksum: Whether to verify the downloaded file's checksum

        Raises:
            ValueError: If version is invalid or empty
        """
        if not version or not isinstance(version, str):
            raise ValueError("Version must be a non-empty string")

        try:
            # Parse version to validate format
            semver.Version.parse(version)
        except ValueError:
            raise ValueError(
                "Version must be in format X.Y.Z where X, Y, and Z are numbers"
            )

        self.version = version
        self.platform = platform or get_current_platform()
        self.dest_dir = dest_dir or get_default_dest_dir(self.platform)
        self.keep_archive = keep_archive
        self.verify_checksum = verify_checksum
        self.base_url = "https://releases.jfrog.io/artifactory/bintray-artifactory/org/artifactory/oss"

    @property
    def package(self) -> ArtifactoryPackage:
        """Get the package configuration."""
        return ArtifactoryPackage(version=self.version, platform=self.platform)

    @property
    def download_url(self) -> str:
        """Get the download URL for the package."""
        return f"{self.base_url}/jfrog-artifactory-oss/{self.version}/{self.package.filename}"

    @property
    def extract_path(self) -> Path:
        """Get the path where the package will be extracted."""
        return self.dest_dir / f"artifactory-oss-{self.version}"

    @property
    def download_path(self) -> Path:
        """Get the path where the package will be downloaded."""
        return self.dest_dir / self.package.filename


def install_artifactory(
    version: str,
    platform: Optional[Platform] = None,
    destination: Optional[Path] = None,
    keep_archive: bool = False,
    verify_checksum_enabled: bool = True,
) -> None:
    """Install Artifactory OSS.

    Args:
        version: Package version
        platform: Target platform
        destination: Installation directory
        keep_archive: Whether to keep downloaded archive
        verify_checksum_enabled: Whether to verify package checksum
    """
    # Setup signal handlers
    setup_signal_handlers()

    # Create config
    config = ArtifactoryConfig(
        version=version,
        platform=platform,
        dest_dir=destination,
        keep_archive=keep_archive,
        verify_checksum=verify_checksum_enabled,
    )

    # Show installation info
    show_info(config)

    # Confirm installation
    if not typer.confirm("Do you want to proceed with the installation?"):
        raise typer.Exit()

    # Download package
    console.print("\nDownloading package...")
    if not download_file(config.download_url, config.download_path):
        console.print("[red]Failed to download package[/red]")
        raise typer.Exit(1)

    # Register download path for cleanup
    register_temp_file(config.download_path)

    # Verify checksum if enabled
    if config.verify_checksum:
        console.print("\nVerifying checksum...")
        if not verify_checksum(config.download_path, f"{config.download_url}.sha256"):
            console.print("[red]Checksum verification failed[/red]")
            raise typer.Exit(1)

    # Extract archive
    console.print("\nExtracting archive...")
    if not extract_archive(config.download_path, config.extract_path):
        console.print("[red]Failed to extract archive[/red]")
        raise typer.Exit(1)

    # Clean up if requested
    if not config.keep_archive:
        try:
            config.download_path.unlink()
        except Exception as e:
            console.print(f"[yellow]Warning: Could not remove archive: {e}[/yellow]")

    console.print("\n[green]Installation completed successfully![/green]")


def list_versions(limit: int = 10) -> None:
    """List available Artifactory versions with size and timestamp information."""
    try:
        # Get current platform and config
        current_platform = get_current_platform()
        config = ArtifactoryConfig(version="7.98.17", platform=current_platform)

        # Get available versions
        from .version import get_available_versions, display_versions_table

        versions = get_available_versions(config.base_url)

        # Display versions table
        package_pattern = (
            "jfrog-artifactory-oss-{version}-"
            + current_platform.value
            + (".zip" if current_platform == Platform.WINDOWS else ".tar.gz")
        )
        display_versions_table(
            config.base_url, versions, current_platform, package_pattern, limit
        )

    except Exception as e:
        console.print(f"[bold red]Error fetching versions: {str(e)}[/]")
        raise typer.Exit(code=1)


def show_info(config: ArtifactoryConfig) -> None:
    """Show information about the script and available URLs."""
    console.print("[bold]JFrog Artifactory OSS Installer[/]")
    console.print()

    # Check URL format
    console.print(f"Base URL: [cyan]{config.base_url}[/]")

    pkg = config.package
    download_url = config.download_url

    # Check if URL is valid
    try:
        response = requests.head(download_url, timeout=5)
        status = (
            f"[green]Available ({response.status_code})[/]"
            if response.status_code == 200
            else f"[red]Not Available ({response.status_code})[/]"
        )
    except Exception as e:
        status = f"[red]Error: {str(e)}[/]"

    console.print(f"Platform: [blue]{config.platform.value}[/]")
    console.print(f"  Filename: {pkg.filename}")
    console.print(f"  URL: {download_url}")
    console.print(f"  Status: {status}")
    console.print(f"  Destination: {config.dest_dir}")
    console.print(f"  Extract Path: {config.extract_path}")
    console.print(f"  Keep Archive: {'Yes' if config.keep_archive else 'No'}")
    console.print(f"  Verify Checksum: {'Yes' if config.verify_checksum else 'No'}")
