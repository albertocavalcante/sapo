"""Sapo CLI entry point."""

import typer
from pathlib import Path
from typing import Optional
from rich.console import Console

from .artifactory import (
    Platform,
    install_artifactory,
    list_versions,
    show_info,
    ArtifactoryConfig,
)

console = Console()

app = typer.Typer(
    help="Download and install JFrog Artifactory OSS",
    invoke_without_command=True,
    no_args_is_help=True,
)


@app.command()
def install(
    version: str = typer.Option(
        "7.98.17", "--version", "-v", help="Artifactory version to install"
    ),
    platform: Platform = typer.Option(
        Platform.DARWIN, "--platform", "-p", help="Platform to download"
    ),
    destination: Optional[Path] = typer.Option(
        None, "--dest", "-d", help="Destination directory (defaults to $HOME/dev/tools)"
    ),
    keep_archive: bool = typer.Option(
        False, "--keep", "-k", help="Keep the downloaded archive after extraction"
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Non-interactive mode, skip confirmation prompts"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", help="Show verbose extraction logs"
    ),
) -> None:
    """
    Download and install JFrog Artifactory OSS.
    """
    install_artifactory(
        version=version,
        platform=platform,
        destination=destination,
        keep_archive=keep_archive,
        non_interactive=yes,
        verbose=verbose,
    )


@app.command()
def versions(
    limit: int = typer.Option(
        10, "--limit", "-l", help="Number of versions to show (default: 10)"
    ),
) -> None:
    """
    List available Artifactory versions with size and timestamp information.
    """
    list_versions(limit=limit)


@app.command()
def info(
    version: str = typer.Option(
        "7.98.17", "--version", "-v", help="Artifactory version to check"
    ),
) -> None:
    """
    Show information about the script and available URLs.
    """
    config = ArtifactoryConfig(version=version)
    show_info(config)


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
